export type Role = "CUSTOMER" | "OPERATOR" | "ADMIN";
export type Account = {
  id: string;
  owner_id: string;
  name: string;
  status: "ACTIVE" | "BLOCKED";
  balance_minor: number;
};
export type User = {
  id: string;
  username: string;
  name: string;
  role: Role;
  active: boolean;
};
export type Journal = {
  id: string;
  kind: "TRANSFER" | "FUNDING";
  source_id: string;
  destination_id: string;
  amount: number;
  created_at: string;
};
export type Entry = {
  account_id: string;
  amount: number;
  side: "DEBIT" | "CREDIT";
};
export type Limits = { per_transfer: number; per_day: number };
export type Audit = {
  id: string;
  actor_id: string | null;
  action: string;
  result: string;
  object_id: string | null;
  request_id: string;
  created_at: string;
};

const messages: Record<string, string> = {
  INVALID_CREDENTIALS: "Проверьте логин и пароль.",
  INSUFFICIENT_FUNDS: "На счёте недостаточно средств.",
  INVALID_INPUT: "Проверьте формат и значения полей.",
  ACCOUNT_BLOCKED: "Один из счетов заблокирован.",
  ACCOUNT_NOT_FOUND: "Счёт недоступен. Проверьте идентификатор.",
  TRANSFER_NOT_FOUND: "Операция недоступна.",
  CUSTOMER_NOT_FOUND: "Активный клиент с таким ID недоступен.",
  SAME_ACCOUNT: "Выберите разные счета.",
  OPERATION_LIMIT: "Превышен лимит на один перевод.",
  DAILY_LIMIT: "Превышен дневной лимит.",
  AUTH_REQUIRED: "Войдите в систему заново.",
  ROLE_FORBIDDEN: "Для действия требуется другая роль.",
  IDEMPOTENCY_CONFLICT: "Ключ уже связан с другими реквизитами.",
  USERNAME_EXISTS: "Этот логин уже занят.",
  INTERNAL_ERROR:
    "Ошибка сервера. Проверьте историю или повторите тот же запрос.",
  LAB_DISABLED: "Лаборатория выключена в этом окружении.",
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public requestId?: string,
  ) {
    super(messages[code] ?? "Запрос не выполнен.");
  }
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  headers?: HeadersInit,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      error.code ?? "HTTP_ERROR",
      response.headers.get("X-Request-ID") ?? undefined,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const rub = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
});
export const money = (amount: number) => rub.format(amount / 100);
export const short = (id: string) => id.slice(0, 8);
export const date = (value: string) =>
  new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
export function minor(raw: string) {
  const input = raw.trim().replace(",", ".");
  if (!/^\d{1,11}(\.\d{1,2})?$/.test(input))
    throw new Error("Введите сумму в рублях, до двух знаков после запятой.");
  const [rubles, kopecks = ""] = input.split(".");
  return Number(rubles) * 100 + Number(kopecks.padEnd(2, "0"));
}
