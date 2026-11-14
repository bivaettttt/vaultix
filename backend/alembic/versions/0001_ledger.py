from alembic import op

revision = "0001"
down_revision = None

TABLES = (
    "users",
    "sessions",
    "accounts",
    "limits",
    "journals",
    "entries",
    "idempotency",
    "audit",
)


def upgrade():
    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            username varchar(40) NOT NULL UNIQUE,
            name varchar(100) NOT NULL,
            password_hash text NOT NULL,
            role text NOT NULL CHECK (role IN ('CUSTOMER', 'OPERATOR', 'ADMIN')),
            active boolean NOT NULL DEFAULT true
        );
        CREATE TABLE sessions (
            token_hash text PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users,
            expires_at timestamptz NOT NULL
        );
        CREATE INDEX sessions_user ON sessions(user_id);
        CREATE TABLE accounts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id uuid REFERENCES users,
            name varchar(100) NOT NULL,
            status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'BLOCKED')),
            currency text NOT NULL DEFAULT 'RUB' CHECK (currency = 'RUB')
        );
        CREATE INDEX accounts_owner ON accounts(owner_id);
        CREATE UNIQUE INDEX one_clearing ON accounts ((owner_id IS NULL)) WHERE owner_id IS NULL;
        INSERT INTO accounts(id, name) VALUES ('00000000-0000-0000-0000-000000000001', 'Demo clearing');
        CREATE TABLE limits (
            id integer PRIMARY KEY CHECK (id = 1),
            per_transfer bigint NOT NULL CHECK (per_transfer BETWEEN 1 AND 1000000000000),
            per_day bigint NOT NULL CHECK (per_day BETWEEN per_transfer AND 1000000000000)
        );
        INSERT INTO limits VALUES (1, 5000000, 10000000);
        CREATE TABLE journals (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            kind text NOT NULL CHECK (kind IN ('TRANSFER', 'FUNDING')),
            actor_id uuid REFERENCES users,
            source_id uuid NOT NULL REFERENCES accounts,
            destination_id uuid NOT NULL REFERENCES accounts,
            amount bigint NOT NULL CHECK (amount BETWEEN 1 AND 1000000000000),
            created_at timestamptz NOT NULL,
            CHECK (source_id <> destination_id),
            CHECK (destination_id <> '00000000-0000-0000-0000-000000000001'),
            CHECK ((kind = 'FUNDING') = (source_id = '00000000-0000-0000-0000-000000000001'))
        );
        CREATE INDEX journals_source_date ON journals(source_id, created_at);
        CREATE INDEX journals_destination_date ON journals(destination_id, created_at);
        CREATE TABLE entries (
            journal_id uuid NOT NULL REFERENCES journals,
            side text NOT NULL CHECK (side IN ('DEBIT', 'CREDIT')),
            account_id uuid NOT NULL REFERENCES accounts,
            amount bigint NOT NULL CHECK (amount BETWEEN 1 AND 1000000000000),
            PRIMARY KEY (journal_id, side)
        );
        CREATE INDEX entries_account ON entries(account_id);
        CREATE TABLE idempotency (
            actor_id uuid NOT NULL REFERENCES users,
            key varchar(128) NOT NULL,
            digest text NOT NULL,
            status integer NOT NULL CHECK (status IN (201, 404, 409)),
            body jsonb NOT NULL,
            PRIMARY KEY (actor_id, key)
        );
        CREATE TABLE audit (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_id uuid REFERENCES users,
            action text NOT NULL,
            result text NOT NULL,
            object_id uuid,
            request_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );
        CREATE INDEX audit_date ON audit(created_at DESC);
        CREATE FUNCTION prevent_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable rows in %', TG_TABLE_NAME USING ERRCODE = '23514';
        END;
        $$;
        CREATE TRIGGER immutable_journals BEFORE UPDATE OR DELETE ON journals
          FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
        CREATE TRIGGER immutable_entries BEFORE UPDATE OR DELETE ON entries
          FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
        CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON audit
          FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
        CREATE FUNCTION validate_journal() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM entries d JOIN entries c ON c.journal_id = d.journal_id
                WHERE d.journal_id = NEW.id AND d.side = 'DEBIT' AND c.side = 'CREDIT'
                  AND d.account_id = NEW.source_id AND c.account_id = NEW.destination_id
                  AND d.amount = NEW.amount AND c.amount = NEW.amount
            ) THEN
                RAISE EXCEPTION 'invalid posting %', NEW.id USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END;
        $$;
        CREATE CONSTRAINT TRIGGER balanced_journal AFTER INSERT ON journals
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_journal();
        CREATE VIEW account_balances AS
          SELECT a.*, COALESCE(b.balance_minor, 0)::bigint AS balance_minor
          FROM accounts a LEFT JOIN (
            SELECT account_id, sum(CASE side WHEN 'CREDIT' THEN amount ELSE -amount END) AS balance_minor
            FROM entries GROUP BY account_id
          ) b ON b.account_id = a.id;
    """)


def downgrade():
    op.execute("DROP VIEW account_balances")
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION validate_journal(), prevent_mutation()")
