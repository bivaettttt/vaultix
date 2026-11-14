import { ErrorNotice, Page } from "./ui";
import { Lab } from "./lab";
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/instrument-sans/700.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles.css";
import { StrictMode, useState, type FormEvent, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useNavigate,
  useOutletContext,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Activity,
  ArrowDownLeft,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChevronRight,
  CircleHelp,
  LayoutGrid,
  List,
  LockKeyhole,
  LogOut,
  Settings2,
  ShieldCheck,
  FlaskConical,
  Wallet,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  date,
  minor,
  money,
  short,
  type Account,
  type Audit,
  type Entry,
  type Journal,
  type Limits,
  type Role,
  type User,
} from "./api";

const client = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: 10000 } },
});
const roleLabels: Record<Role, string> = {
  CUSTOMER: "Клиент",
  OPERATOR: "Оператор",
  ADMIN: "Администратор",
};
const useUser = () => useOutletContext<User>();
const useAccounts = () =>
  useQuery({
    queryKey: ["accounts"],
    queryFn: () => api<Account[]>("/accounts"),
  });

function Brand() {
  return (
    <div className="brand">
      <span>
        <Wallet size={19} />
      </span>
      Vaultix
    </div>
  );
}

function Login() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api("/login", "POST", { username, password }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  return (
    <div className="login">
      <aside className="login-art">
        <Brand />
        <div>
          <p className="eyebrow">ТРАНЗАКЦИОННАЯ ПЛАТФОРМА</p>
          <h1>
            У каждого перевода
            <br />
            две стороны.
          </h1>
          <p>
            Счета, переводы и журнал двойной записи в одном рабочем
            пространстве.
          </p>
        </div>
        <div className="login-diagram">
          <span>
            <ArrowUpRight size={20} /> Дебет
          </span>
          <i />
          <span>
            <ArrowDownLeft size={20} /> Кредит
          </span>
        </div>
        <footer>
          <ShieldCheck size={16} /> Синтетические данные · RUB
        </footer>
      </aside>
      <section className="login-form">
        <div>
          <span className="form-icon">
            <LockKeyhole size={23} />
          </span>
          <h2>Вход в Vaultix</h2>
          <p className="muted">Войдите в свой демонстрационный аккаунт.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              login.mutate();
            }}
          >
            <label>
              Логин
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Пароль
              <input
                autoComplete="current-password"
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <ErrorNotice error={login.error} />
            <button className="primary" disabled={login.isPending}>
              Войти <ArrowRight size={17} />
            </button>
          </form>
          <p className="login-help">
            <CircleHelp size={16} /> Учебные логины указаны в инструкции
            запуска.
          </p>
        </div>
      </section>
    </div>
  );
}

function Shell() {
  const session = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/me"),
  });
  const queryClient = useQueryClient();
  const logout = useMutation({
    mutationFn: () => api("/logout", "POST"),
    onSuccess: async () => {
      await queryClient.cancelQueries();
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== "me",
      });
      queryClient.setQueryData(["me"], null);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
  if (session.isPending) return <div className="center">Проверяем сессию…</div>;
  if (session.error instanceof ApiError && session.error.status === 401)
    return <Login />;
  if (!session.data)
    return (
      <div className="center">
        <ErrorNotice error={session.error} />
        <button onClick={() => session.refetch()}>Повторить</button>
      </div>
    );
  const user = session.data;
  const staff = user.role !== "CUSTOMER";
  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />
        <p className="side-label">РАБОЧЕЕ ПРОСТРАНСТВО</p>
        <nav aria-label="Основная навигация">
          <NavLink to="/" end>
            <LayoutGrid size={18} /> Обзор
          </NavLink>
          <NavLink to="/transfer">
            <ArrowUpRight size={18} /> Новый перевод
          </NavLink>
          <NavLink to="/history">
            <List size={18} /> История операций
          </NavLink>
        </nav>
        {staff && (
          <>
            <p className="side-label">УПРАВЛЕНИЕ</p>
            <nav aria-label="Управление">
              <NavLink to="/operations">
                <Settings2 size={18} /> Операционная панель
              </NavLink>
              <NavLink to="/audit">
                <ShieldCheck size={18} /> Аудит
              </NavLink>
              {user.role === "ADMIN" && (
                <NavLink to="/lab">
                  <FlaskConical size={18} /> Лаборатория
                </NavLink>
              )}
            </nav>
          </>
        )}
        <div className="sidebar-bottom">
          <a href="/api/docs" target="_blank" rel="noreferrer">
            <BookOpen size={17} /> Документация API <ArrowUpRight size={13} />
          </a>
          <span>
            <i /> Учебная среда
          </span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            <Activity size={16} /> Vaultix <ChevronRight size={13} />{" "}
            {staff ? "Операции" : "Клиентский кабинет"}
          </span>
          <div>
            <span className="avatar">
              {user.name
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")}
            </span>
            <p>
              <strong>{user.name}</strong>
              <small>{roleLabels[user.role]}</small>
            </p>
            <button
              className="icon"
              title="Выйти"
              aria-label="Выйти"
              disabled={logout.isPending}
              onClick={() => logout.mutate()}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main>
          <ErrorNotice error={logout.error} />
          <Outlet context={user} />
        </main>
      </div>
    </div>
  );
}

const activeLabel = (status: Account["status"]) =>
  status === "ACTIVE" ? "Активен" : "Заблокирован";
function Status({ status }: { status: Account["status"] }) {
  return (
    <span className={"tag " + (status === "ACTIVE" ? "good" : "bad")}>
      <i />
      {activeLabel(status)}
    </span>
  );
}

function AccountTable({ accounts }: { accounts: Account[] }) {
  if (!accounts.length) return <p className="empty">Счетов пока нет.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Счёт</th>
            <th>Статус</th>
            <th className="numeric">Остаток</th>
            <th aria-label="Открыть" />
          </tr>
        </thead>
        <tbody>
          {accounts.map((a) => (
            <tr key={a.id}>
              <td>
                <Link className="record" to={"/accounts/" + a.id}>
                  <span className="record-icon">
                    <Wallet size={17} />
                  </span>
                  <span>
                    {a.name}
                    <small className="mono">{short(a.id)} · RUB</small>
                  </span>
                </Link>
              </td>
              <td>
                <Status status={a.status} />
              </td>
              <td className="numeric strong">{money(a.balance_minor)}</td>
              <td>
                <Link
                  className="icon"
                  aria-label={"Открыть " + a.name}
                  to={"/accounts/" + a.id}
                >
                  <ChevronRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Overview() {
  const user = useUser();
  const accounts = useAccounts();
  const entries = accounts.data ?? [];
  return (
    <>
      <Page
        title={user.role === "CUSTOMER" ? "Обзор счетов" : "Обзор операций"}
        subtitle={
          user.role === "CUSTOMER"
            ? "Остатки, счета и последние операции"
            : "Синтетические счета и проведённые операции"
        }
      >
        <Link className="primary" to="/transfer">
          Новый перевод <ArrowUpRight size={17} />
        </Link>
      </Page>
      <ErrorNotice error={accounts.error} />
      {accounts.isPending && <p>Загружаем счета…</p>}
      {accounts.data && (
        <>
          <section className="summary">
            <div>
              <span>ОБЩИЙ ОСТАТОК</span>
              <strong>
                {money(
                  entries.reduce((total, a) => total + a.balance_minor, 0),
                )}
              </strong>
              <small>Текущий остаток по всем доступным счетам</small>
            </div>
            <div>
              <span>АКТИВНЫЕ СЧЕТА</span>
              <strong>
                {entries.filter((a) => a.status === "ACTIVE").length}
              </strong>
              <small>из {entries.length} открытых</small>
            </div>
            <div>
              <span>ВАЛЮТА УЧЁТА</span>
              <strong>RUB</strong>
              <small>Российский рубль</small>
            </div>
          </section>
          <section className="panel">
            <div className="panel-title">
              <h2>
                {user.role === "CUSTOMER" ? "Мои счета" : "Счета клиентов"}
              </h2>
              <span className="count">{entries.length}</span>
            </div>
            <AccountTable accounts={entries} />
          </section>
        </>
      )}
      <section className="panel">
        <div className="panel-title">
          <h2>Последние операции</h2>
          <Link to="/history">
            Вся история <ArrowRight size={15} />
          </Link>
        </div>
        <HistoryTable pageSize={5} />
      </section>
    </>
  );
}
function HistoryTable({
  account,
  pageSize = 20,
}: {
  account?: string;
  pageSize?: number;
}) {
  const [page, setPage] = useState(0);
  const accounts = useAccounts();
  const data = useQuery({
    queryKey: ["history", account, pageSize, page],
    queryFn: () =>
      api<Journal[]>(
        "/transfers?" +
          new URLSearchParams({
            ...(account ? { account_id: account } : {}),
            limit: String(pageSize),
            offset: String(page * pageSize),
          }),
      ),
  });
  const names = new Map(accounts.data?.map((a) => [a.id, a.name]));
  if (data.isPending) return <p className="empty">Загружаем операции…</p>;
  if (data.error) return <ErrorNotice error={data.error} />;
  return (
    <>
      {data.data.length === 0 ? (
        <p className="empty">Операций на этой странице нет.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Операция</th>
                <th>Получатель</th>
                <th>Дата и время</th>
                <th className="numeric">Сумма</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((j) => {
                const outgoing = account
                  ? j.source_id === account
                  : names.has(j.source_id);
                return (
                  <tr key={j.id}>
                    <td>
                      <Link className="record" to={"/history/" + j.id}>
                        <span className="record-icon">
                          {outgoing ? (
                            <ArrowUpRight size={17} />
                          ) : (
                            <ArrowDownLeft size={17} />
                          )}
                        </span>
                        <span>
                          {j.kind === "FUNDING"
                            ? "Открытие счёта"
                            : "Внутренний перевод"}
                          <small className="mono">{short(j.id)}</small>
                        </span>
                      </Link>
                    </td>
                    <td>
                      {names.get(j.destination_id) ?? short(j.destination_id)}
                    </td>
                    <td className="muted">{date(j.created_at)}</td>
                    <td className="numeric strong">
                      {account ? (outgoing ? "−" : "+") : ""}
                      {money(j.amount)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {pageSize > 5 && (
        <div className="pagination">
          <button disabled={!page} onClick={() => setPage(page - 1)}>
            Назад
          </button>
          <span>Страница {page + 1}</span>
          <button
            disabled={data.data.length < pageSize}
            onClick={() => setPage(page + 1)}
          >
            Далее
          </button>
        </div>
      )}
    </>
  );
}
function AccountPage() {
  const { id } = useParams();
  const account = useQuery({
    queryKey: ["accounts", id],
    queryFn: () => api<Account>("/accounts/" + id),
  });
  if (account.isPending) return <p>Загружаем счёт…</p>;
  if (account.error) return <ErrorNotice error={account.error} />;
  const a = account.data;
  return (
    <>
      <Link className="back" to="/">
        <ArrowLeft size={16} /> Обзор
      </Link>
      <Page title={a.name}>
        <Status status={a.status} />
      </Page>
      <section className="summary single">
        <div>
          <span>ТЕКУЩИЙ ОСТАТОК</span>
          <strong>{money(a.balance_minor)}</strong>
          <small className="mono full-id">{a.id}</small>
          <button onClick={() => navigator.clipboard.writeText(a.id)}>
            Копировать ID
          </button>
        </div>
      </section>
      <section className="panel">
        <div className="panel-title">
          <h2>История счёта</h2>
          <Link to={"/transfer?source=" + a.id}>
            Новый перевод <ArrowUpRight size={15} />
          </Link>
        </div>
        <HistoryTable key={id} account={id} />
      </section>
    </>
  );
}
function JournalPage() {
  const { id } = useParams();
  const journal = useQuery({
    queryKey: ["journal", id],
    queryFn: () => api<Journal & { entries: Entry[] }>("/transfers/" + id),
  });
  if (journal.isPending) return <p>Загружаем операцию…</p>;
  if (journal.error) return <ErrorNotice error={journal.error} />;
  const j = journal.data;
  return (
    <>
      <Link className="back" to="/history">
        <ArrowLeft size={16} /> История
      </Link>
      <Page
        title={j.kind === "FUNDING" ? "Открытие счёта" : "Внутренний перевод"}
        subtitle={date(j.created_at)}
      >
        <span className="tag good">
          <i /> Проведено
        </span>
      </Page>
      <section className="panel form-panel">
        <h2>{money(j.amount)}</h2>
        <p>
          Операция <span className="mono full-id">{j.id}</span>
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Сторона</th>
                <th>Счёт</th>
                <th className="numeric">Сумма</th>
              </tr>
            </thead>
            <tbody>
              {j.entries.map((e) => (
                <tr key={e.side}>
                  <td>{e.side === "DEBIT" ? "Дебет" : "Кредит"}</td>
                  <td className="mono">{e.account_id}</td>
                  <td className="numeric">{money(e.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
function TransferPage() {
  const [params] = useSearchParams();
  const [source, setSource] = useState(params.get("source") ?? "");
  const [destination, setDestination] = useState("");
  const [amount, setAmount] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const accounts = useAccounts();
  const limits = useQuery({
    queryKey: ["limits"],
    queryFn: () => api<Limits>("/limits"),
  });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const transfer = useMutation({
    mutationFn: () =>
      api<{ id: string }>(
        "/transfers",
        "POST",
        {
          source_id: source,
          destination_id: destination.trim(),
          amount_minor: minor(amount),
          currency: "RUB",
        },
        { "Idempotency-Key": key },
      ),
    onSuccess: (result) => {
      void queryClient.invalidateQueries();
      navigate("/history/" + result.id);
    },
  });
  const changed = (setter: (value: string) => void, value: string) => {
    setter(value);
    setKey(crypto.randomUUID());
    transfer.reset();
  };
  return (
    <>
      <Page
        title="Новый перевод"
        subtitle="Внутренний перевод в российских рублях"
      />
      <section className="panel form-panel">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            transfer.mutate();
          }}
        >
          <ErrorNotice error={accounts.error} />
          <label>
            Счёт списания
            <select
              required
              value={source}
              onChange={(e) => changed(setSource, e.target.value)}
            >
              <option value="">
                {accounts.isPending ? "Загрузка…" : "Выберите счёт"}
              </option>
              {accounts.data?.map((a) => (
                <option
                  key={a.id}
                  disabled={a.status === "BLOCKED"}
                  value={a.id}
                >
                  {a.name} · {money(a.balance_minor)}
                </option>
              ))}
            </select>
          </label>
          <label>
            ID счёта получателя
            <input
              required
              placeholder="UUID счёта Vaultix"
              value={destination}
              onChange={(e) => changed(setDestination, e.target.value)}
            />
          </label>
          <label>
            Сумма, ₽
            <input
              required
              inputMode="decimal"
              placeholder="0,00"
              value={amount}
              onChange={(e) => changed(setAmount, e.target.value)}
            />
          </label>
          {limits.data && (
            <p className="muted">
              Лимит операции {money(limits.data.per_transfer)} · за UTC-день{" "}
              {money(limits.data.per_day)}
            </p>
          )}
          <ErrorNotice error={transfer.error} />
          <button
            className="primary"
            disabled={transfer.isPending || accounts.isPending}
          >
            {transfer.isPending ? "Проводим…" : "Выполнить перевод"}{" "}
            <ArrowUpRight size={17} />
          </button>
        </form>
      </section>
    </>
  );
}
function Operations() {
  const user = useUser();
  const accounts = useAccounts();
  const queryClient = useQueryClient();
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<User[]>("/users"),
  });
  const limits = useQuery({
    queryKey: ["limits"],
    queryFn: () => api<Limits>("/limits"),
  });
  const [notice, setNotice] = useState("");
  const action = useMutation({
    mutationFn: ({
      path,
      method,
      body,
    }: {
      path: string;
      method: string;
      body: unknown;
    }) => api(path, method, body),
    onMutate: () => setNotice(""),
    onSuccess: () => {
      setNotice("Изменения сохранены");
      void queryClient.invalidateQueries();
    },
  });
  function submit(
    event: FormEvent<HTMLFormElement>,
    handler: (data: FormData) => void,
  ) {
    event.preventDefault();
    handler(new FormData(event.currentTarget));
  }
  return (
    <>
      <Page
        title="Операционная панель"
        subtitle="Счета, контрагенты и правила проведения"
      />
      <ErrorNotice
        error={action.error ?? users.error ?? accounts.error ?? limits.error}
      />
      {notice && (
        <p className="tag good" role="status">
          {notice}{" "}
          <button
            className="icon"
            aria-label="Закрыть"
            onClick={() => setNotice("")}
          >
            <X size={14} />
          </button>
        </p>
      )}
      <section className="panel">
        <div className="panel-title">
          <h2>Статусы счетов</h2>
          <Link to="/history">
            Журнал операций <ArrowRight size={15} />
          </Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Счёт</th>
                <th>Остаток</th>
                <th>Статус</th>
                <th>Действие</th>
              </tr>
            </thead>
            <tbody>
              {accounts.data?.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={"/accounts/" + a.id}>{a.name}</Link>
                    <small className="mono">{a.id}</small>
                  </td>
                  <td>{money(a.balance_minor)}</td>
                  <td>
                    <Status status={a.status} />
                  </td>
                  <td>
                    <button
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: "/accounts/" + a.id,
                          method: "PATCH",
                          body: {
                            status:
                              a.status === "ACTIVE" ? "BLOCKED" : "ACTIVE",
                          },
                        })
                      }
                    >
                      {a.status === "ACTIVE"
                        ? "Заблокировать"
                        : "Разблокировать"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {accounts.isPending && <p className="empty">Загружаем счета…</p>}
        {accounts.data?.length === 0 && (
          <p className="empty">Счетов пока нет.</p>
        )}
      </section>
      <div className="form-grid">
        <section className="panel form-panel">
          <h2>Открыть счёт</h2>
          <form
            onSubmit={(e) =>
              submit(e, (d) =>
                action.mutate({
                  path: "/accounts",
                  method: "POST",
                  body: {
                    owner_id: d.get("owner"),
                    name: d.get("name"),
                    funding_minor: Number(d.get("funding")),
                  },
                }),
              )
            }
          >
            <label>
              Клиент
              <select name="owner" required>
                <option value="">Выберите клиента</option>
                {users.data
                  ?.filter((u) => u.active && u.role === "CUSTOMER")
                  .map((u) => (
                    <option value={u.id} key={u.id}>
                      {u.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Название
              <input name="name" required maxLength={100} />
            </label>
            <label>
              Стартовое финансирование, коп.
              <input
                name="funding"
                type="number"
                defaultValue={0}
                min={0}
                max={1e12}
                required
              />
            </label>
            <button className="primary" disabled={action.isPending}>
              Открыть счёт
            </button>
          </form>
        </section>
        {user.role === "ADMIN" && limits.data && (
          <section className="panel form-panel">
            <h2>Лимиты переводов</h2>
            <form
              key={limits.data.per_transfer + ":" + limits.data.per_day}
              onSubmit={(e) =>
                submit(e, (d) =>
                  action.mutate({
                    path: "/limits",
                    method: "PUT",
                    body: {
                      per_transfer: Number(d.get("operation")),
                      per_day: Number(d.get("day")),
                    },
                  }),
                )
              }
            >
              <label>
                На операцию, коп.
                <input
                  name="operation"
                  type="number"
                  min={1}
                  max={1e12}
                  defaultValue={limits.data.per_transfer}
                  required
                />
              </label>
              <label>
                За UTC-день, коп.
                <input
                  name="day"
                  type="number"
                  min={1}
                  max={1e12}
                  defaultValue={limits.data.per_day}
                  required
                />
              </label>
              <button className="primary" disabled={action.isPending}>
                Сохранить лимиты
              </button>
            </form>
          </section>
        )}
      </div>
      {user.role === "ADMIN" && (
        <>
          <section className="panel">
            <div className="panel-title">
              <h2>Пользователи</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Имя</th>
                    <th>Роль</th>
                    <th>Доступ</th>
                    <th>Действие</th>
                  </tr>
                </thead>
                <tbody>
                  {users.data?.map((u) => (
                    <tr key={u.id}>
                      <td>
                        {u.name}
                        <small>{u.username}</small>
                      </td>
                      <td>{roleLabels[u.role]}</td>
                      <td>{u.active ? "Активен" : "Отключён"}</td>
                      <td>
                        {u.role === "CUSTOMER" && (
                          <button
                            disabled={action.isPending}
                            onClick={() =>
                              action.mutate({
                                path: "/users/" + u.id,
                                method: "PATCH",
                                body: { active: !u.active },
                              })
                            }
                          >
                            {u.active ? "Отключить" : "Включить"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel form-panel">
            <h2>Создать пользователя</h2>
            <form
              onSubmit={(e) =>
                submit(e, (d) =>
                  action.mutate({
                    path: "/users",
                    method: "POST",
                    body: Object.fromEntries(d.entries()),
                  }),
                )
              }
            >
              <label>
                Логин
                <input
                  name="username"
                  required
                  pattern="[a-z][a-z0-9_.\x2d]{2,39}"
                />
              </label>
              <label>
                Имя
                <input name="name" required maxLength={100} />
              </label>
              <label>
                Пароль
                <input
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  maxLength={128}
                />
              </label>
              <label>
                Роль
                <select name="role">
                  {Object.entries(roleLabels).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <button className="primary" disabled={action.isPending}>
                Создать пользователя
              </button>
            </form>
          </section>
        </>
      )}
    </>
  );
}

function AuditPage() {
  const [page, setPage] = useState(0);
  const data = useQuery({
    queryKey: ["audit", page],
    queryFn: () => api<Audit[]>("/audit?limit=30&offset=" + page * 30),
  });
  return (
    <>
      <Page
        title="Журнал аудита"
        subtitle="История чувствительных действий и идентификаторы запросов"
      />
      <ErrorNotice error={data.error} />
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Действие</th>
                <th>Результат</th>
                <th>Субъект и объект</th>
                <th>Запрос</th>
                <th>Время</th>
              </tr>
            </thead>
            <tbody>
              {data.data?.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{a.action}</td>
                  <td className="mono">{a.result}</td>
                  <td>
                    <span title={a.actor_id ?? ""}>
                      {a.actor_id ? short(a.actor_id) : "—"}
                    </span>
                    <small title={a.object_id ?? ""}>
                      {a.object_id ? short(a.object_id) : "—"}
                    </small>
                  </td>
                  <td className="mono">{a.request_id}</td>
                  <td>{date(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data.isPending && <p className="empty">Загружаем события…</p>}
        {data.data?.length === 0 && <p className="empty">Событий пока нет.</p>}
        <div className="pagination">
          <button disabled={!page} onClick={() => setPage(page - 1)}>
            Назад
          </button>
          <span>Страница {page + 1}</span>
          <button
            disabled={(data.data?.length ?? 0) < 30}
            onClick={() => setPage(page + 1)}
          >
            Далее
          </button>
        </div>
      </section>
    </>
  );
}
function Protected({
  admin,
  children,
}: {
  admin?: boolean;
  children: ReactNode;
}) {
  const { role } = useUser();
  return role === "CUSTOMER" || (admin && role !== "ADMIN") ? (
    <Navigate replace to="/" />
  ) : (
    children
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Overview />} />
            <Route path="accounts/:id" element={<AccountPage />} />
            <Route path="transfer" element={<TransferPage />} />
            <Route
              path="history"
              element={
                <>
                  <Page
                    title="История операций"
                    subtitle="Проведённые переводы и финансирование счетов"
                  />
                  <section className="panel">
                    <HistoryTable />
                  </section>
                </>
              }
            />
            <Route path="history/:id" element={<JournalPage />} />
            <Route
              path="operations"
              element={
                <Protected>
                  <Operations />
                </Protected>
              }
            />
            <Route
              path="audit"
              element={
                <Protected>
                  <AuditPage />
                </Protected>
              }
            />
            <Route
              path="lab"
              element={
                <Protected admin>
                  <Lab />
                </Protected>
              }
            />
            <Route path="*" element={<Navigate replace to="/" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
