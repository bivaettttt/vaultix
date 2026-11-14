import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Play, X } from "lucide-react";
import { api, money } from "./api";
import { ErrorNotice, Page } from "./main";

const scenarios = [
  [
    "success",
    "Обычный перевод",
    "Операция и две проводки фиксируются одной транзакцией.",
  ],
  [
    "insufficient",
    "Недостаточный баланс",
    "Сумма списания превышает остаток отправителя.",
  ],
  [
    "replay",
    "Повтор запроса",
    "Ключ и тело повторяются. API возвращает сохранённый результат.",
  ],
  [
    "conflict",
    "Изменение тела",
    "Повтор с тем же ключом и другой суммой даёт конфликт.",
  ],
  [
    "concurrent",
    "Два конкурентных списания",
    "Два HTTP-запроса списывают по 70 ₽ со счёта с остатком 100 ₽.",
  ],
  [
    "rollback",
    "Ошибка и откат",
    "Сбой возникает после записи журнала и проводок до фиксации.",
  ],
  [
    "blocked",
    "Заблокированный счёт",
    "Источник заблокирован до отправки запроса.",
  ],
  ["limit", "Превышение лимита", "Сумма выше лимита отдельной операции."],
] as const;
const labels: Record<string, string> = {
  http_outcomes: "Ожидаемые ответы API",
  expected_balances: "Ожидаемые остатки",
  journal_count: "Число проведённых операций",
  entries_balanced: "Равенство дебета и кредита",
  ledger_unchanged: "Журнал и остатки сохранились",
  same_receipt: "Повтор вернул тот же результат",
};

type Snapshot = {
  accounts: { id: string; status: string; balance_minor: number }[];
  journals: unknown[];
  entries: unknown[];
};
type LabResult = {
  passed: boolean;
  checks: Record<string, boolean>;
  requests: {
    key: string;
    body: { source_id: string; destination_id: string; amount_minor: number };
  }[];
  responses: {
    status: number;
    body: unknown;
    replayed: boolean;
    request_id: string;
  }[];
  before: Snapshot;
  after: Snapshot;
};

export function Lab() {
  const [selected, setSelected] = useState<(typeof scenarios)[number]>(
    scenarios[0],
  );
  const run = useMutation({
    mutationFn: () => api<LabResult>("/lab/" + selected[0], "POST"),
  });
  const result = run.data;
  return (
    <>
      <Page
        title="Лаборатория надёжности"
        subtitle="HTTP-запросы и проводки в отдельной демонстрационной базе PostgreSQL"
      />
      <div className="lab-grid">
        <section className="panel">
          <div className="panel-title">
            <h2>Сценарии</h2>
          </div>
          <div className="scenario-list">
            {scenarios.map((s) => (
              <button
                key={s[0]}
                aria-pressed={s[0] === selected[0]}
                disabled={run.isPending}
                onClick={() => {
                  setSelected(s);
                  run.reset();
                }}
              >
                {s[1]}
              </button>
            ))}
          </div>
        </section>
        <section className="panel form-panel">
          <h2>{selected[1]}</h2>
          <p className="muted">{selected[2]}</p>
          <p className="muted">
            Для каждого запуска создаются новые счета. Стартовые остатки 100 ₽ и
            0 ₽.
          </p>
          <button
            className="primary"
            disabled={run.isPending}
            onClick={() => run.mutate()}
          >
            <Play size={16} />
            {run.isPending ? "Выполняем…" : "Запустить проверку"}
          </button>
          <ErrorNotice error={run.error} />
        </section>
      </div>
      {result && (
        <div aria-live="polite">
          <section className="panel">
            <div className="panel-title">
              <h2>Инварианты</h2>
              <span className={"tag " + (result.passed ? "good" : "bad")}>
                <i />
                {result.passed ? "Проверка пройдена" : "Обнаружено расхождение"}
              </span>
            </div>
            <ul className="checks">
              {Object.entries(result.checks).map(([code, ok]) => (
                <li key={code}>
                  {ok ? <Check size={17} /> : <X size={17} />}
                  {labels[code]} <span>{ok ? "Подтверждено" : "Ошибка"}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="panel">
            <div className="panel-title">
              <h2>Состояние PostgreSQL</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Показатель</th>
                    <th>До</th>
                    <th>После</th>
                  </tr>
                </thead>
                <tbody>
                  {(["source_id", "destination_id"] as const).map((side, i) => {
                    const id = result.requests[0].body[side];
                    const before = result.before.accounts.find(
                      (a) => a.id === id,
                    )!;
                    const after = result.after.accounts.find(
                      (a) => a.id === id,
                    )!;
                    return (
                      <tr key={side}>
                        <td>
                          {i ? "Получатель" : "Отправитель"}
                          <small className="mono">{id}</small>
                        </td>
                        <td>
                          {money(before.balance_minor)}
                          <small>{before.status}</small>
                        </td>
                        <td>
                          {money(after.balance_minor)}
                          <small>{after.status}</small>
                        </td>
                      </tr>
                    );
                  })}
                  <tr>
                    <td>Операции</td>
                    <td>{result.before.journals.length}</td>
                    <td>{result.after.journals.length}</td>
                  </tr>
                  <tr>
                    <td>Проводки</td>
                    <td>{result.before.entries.length}</td>
                    <td>{result.after.entries.length}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <details>
              <summary>Полные снимки</summary>
              <pre>
                {JSON.stringify(
                  { before: result.before, after: result.after },
                  null,
                  2,
                )}
              </pre>
            </details>
          </section>
          <section className="panel">
            <div className="panel-title">
              <h2>Запросы и ответы API</h2>
            </div>
            {result.responses.map((r, index) => (
              <details key={r.request_id} open={index === 0}>
                <summary>
                  POST /api/transfers · HTTP {r.status}
                  {r.replayed ? " · повтор" : ""}
                </summary>
                <pre>
                  {JSON.stringify(
                    { request: result.requests[index], response: r },
                    null,
                    2,
                  )}
                </pre>
              </details>
            ))}
          </section>
        </div>
      )}
    </>
  );
}
