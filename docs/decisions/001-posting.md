# ADR-001 · PostgreSQL ledger and locking

Status: accepted.

A modular monolith can commit entries, replay receipts and success audit in one transaction. Use derived balances for this bounded educational dataset. A mutable balance projection would speed up reads at the cost of synchronization and reconciliation logic.

Use READ COMMITTED with deterministic account locking and per-key transaction advisory locks. Serializable transactions would require handling serialization retries across otherwise independent operations. An advisory hash collision only serializes unrelated requests. The database primary key remains the authority for replay receipts.

Store successful and rejected business outcomes. Roll back unexpected failures so a retry can execute again. Scope keys to the authenticated user. Each deliberate change to transfer input requires a fresh key.
