import type {
  GatewayCard,
  GatewayConfig,
  GatewayErrorPayload,
  GatewayMe,
  GatewayNode,
  GatewayNodeActions,
  GatewayQuote,
  GatewayRole,
  GatewayStats,
  GatewayTransfer,
  LoginResult,
} from "./types";

const SESSION_KEY = "nandbank.access-token";
const API_BASE_URL = (import.meta.env["VITE_API_BASE_URL"] ?? "").trim().replace(/\/$/, "");

function clearExpiredSession(): void {
  clearAccessToken();
  if (typeof window !== "undefined") window.dispatchEvent(new Event("nandbank:session-expired"));
}

export const DEMO_MODE = import.meta.env["VITE_DEMO_MODE"] === "true";
export const DEMO_NOTICE = "Pré-visualização de interface — dados fictícios";

export class GatewayError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "GatewayError";
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

export function saveAccessToken(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SESSION_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // A blocked browser storage must not prevent the sign-out view from opening.
  }
}

function endpoint(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function messageFromPayload(payload: unknown): string | null {
  if (payload == null || typeof payload !== "object") return null;
  const error = payload as GatewayErrorPayload;
  if (typeof error.detail === "string") return error.detail;
  if (error.detail && typeof error.detail.message === "string") return error.detail.message;
  return typeof error.message === "string" ? error.message : null;
}

function statusMessage(status: number, detail: string | null): string {
  if (status === 406) return "Servidor indisponível. Esta pré-visualização não está ligada ao Gateway FastAPI.";
  if (status === 401) return "A sessão terminou. Entre novamente para continuar.";
  if (status === 403) return "O seu perfil não tem autorização para esta operação.";
  if (status === 404) return detail ?? "A informação pedida não foi encontrada.";
  if (status === 409) return detail ?? "Esta operação já existe ou precisa de ser revista.";
  if (status === 422 || status === 400) return detail ?? "Verifique os dados preenchidos.";
  if (status === 503) return "O servidor bancário ou um serviço regional está indisponível.";
  if (status >= 500) return "O servidor não conseguiu concluir o pedido.";
  return detail ?? "Não foi possível concluir o pedido.";
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 12_000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  try {
    const response = await fetch(endpoint(path), {
      ...init,
      headers,
      signal: controller.signal,
      cache: "no-store",
    });

    let payload: unknown = null;
    if (response.status !== 204) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    }
    if (!response.ok) {
      if (response.status === 401) clearExpiredSession();
      throw new GatewayError(response.status, statusMessage(response.status, messageFromPayload(payload)));
    }
    return payload as T;
  } catch (error) {
    if (error instanceof GatewayError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new GatewayError(0, "O servidor demorou demasiado a responder. Tente novamente.");
    }
    throw new GatewayError(0, "Servidor indisponível. Confirme a ligação ao Gateway FastAPI.");
  } finally {
    clearTimeout(timeout);
  }
}

async function requestBlob(path: string): Promise<Blob> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
  const headers = new Headers({ Accept: "application/pdf" });
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    const response = await fetch(endpoint(path), { headers, signal: controller.signal, cache: "no-store" });
    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (response.status === 401) clearExpiredSession();
      throw new GatewayError(response.status, statusMessage(response.status, messageFromPayload(payload)));
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof GatewayError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new GatewayError(0, "O servidor demorou demasiado a responder. Tente novamente.");
    }
    throw new GatewayError(0, "Servidor indisponível. Confirme a ligação ao Gateway FastAPI.");
  } finally {
    clearTimeout(timeout);
  }
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export const gateway = {
  health: () => get<{ status: string; app: string; timestamp: string }>("/api/health"),
  config: () => get<GatewayConfig>("/api/config"),
  login: (email: string, password: string) =>
    post<LoginResult>("/api/auth/login", { email, password }),
  register: (input: { name: string; email: string; password: string; branch: string }) =>
    post<{ ok: boolean; account_id: string; user_id: string; message: string }>(
      "/api/auth/register",
      input,
    ),
  me: () => get<GatewayMe>("/api/me"),
  createAccount: (branch: string) =>
    post<{ ok: boolean; account_id: string; balance_minor: number }>("/api/accounts", { branch }),
  lookupAccount: (id: string) =>
    get<{ account_id: string; beneficiary: string; region: string; branch: string; currency: string }>(
      `/api/accounts/lookup/${encodeURIComponent(id)}`,
    ),
  account: (id: string) => get<Record<string, unknown>>(`/api/accounts/${encodeURIComponent(id)}`),
  accountDetails: (id: string) =>
    get<Record<string, unknown>>(`/api/accounts/${encodeURIComponent(id)}/details`),
  ledger: (id: string) => get<unknown[]>(`/api/accounts/${encodeURIComponent(id)}/ledger`),
  transfers: () => get<GatewayTransfer[]>("/api/transfers"),
  transferStatus: (id: string) => get<GatewayTransfer>(`/api/transfers/${encodeURIComponent(id)}`),
  transfer: (input: {
    source_id: string;
    destination_id: string;
    amount: string;
    idempotency_key: string;
    note?: string;
  }) => request<GatewayTransfer & { quote?: GatewayQuote }>("/api/transfers", { method: "POST", body: JSON.stringify(input) }, 45_000),
  quote: (source: string, destination: string, amount: string) => {
    const query = new URLSearchParams({ source, destination, amount });
    return get<GatewayQuote>(`/api/fx/quote?${query.toString()}`);
  },
  fxRates: () => get<Array<{ currency: string; units_per_eur: string; source: string; updated_at: string }>>("/api/fx/rates"),
  cards: () => get<GatewayCard[]>("/api/cards"),
  requestCard: (account_id: string) =>
    post<{ id: string; status: string; message: string }>("/api/cards/request", { account_id }),
  setCardState: (id: string, action: "freeze" | "unfreeze") =>
    request<{ ok: boolean; status: string }>(`/api/cards/${encodeURIComponent(id)}/${action}`, { method: "POST" }),
  adminStats: () => get<GatewayStats>("/api/admin/stats"),
  nodes: () => get<GatewayNode[]>("/api/admin/nodes"),
  failover: () => get<GatewayNode[]>("/api/failover/status"),
  operations: () => get<unknown[]>("/api/admin/operations"),
  adminAccounts: () => get<unknown[]>("/api/admin/accounts"),
  pendingCards: () => get<GatewayCard[]>("/api/admin/cards"),
  reviewCard: (id: string, approved: boolean) =>
    post<{ ok: boolean; status: string }>(`/api/admin/cards/${encodeURIComponent(id)}/review`, {
      approved,
    }),
  nodeActions: () => get<GatewayNodeActions>("/api/admin/node-actions"),
  requestNodeAction: (
    code: string,
    action: "STOP_PRIMARY" | "START_PRIMARY",
    reason: "MAINTENANCE" | "FAULT" | "SECURITY" | "UPGRADE" | "FAILOVER_TEST" | "OTHER",
    note = "",
  ) =>
    post<{ id: string; status: string; message: string }>(
      `/api/admin/nodes/${encodeURIComponent(code)}/action`,
      { action, reason, note },
    ),
  audit: () => get<unknown[]>("/api/admin/audit"),
  receipt: (id: string) => requestBlob(`/api/transactions/${encodeURIComponent(id)}/receipt.pdf`),
};

export type RoleHome = "/cliente/visao-geral" | "/gerente/visao-geral" | "/gerente-global/visao-geral";

export function roleHome(role: GatewayRole): RoleHome | null {
  if (role === "client") return "/cliente/visao-geral";
  if (role === "global_manager") return "/gerente-global/visao-geral";
  if (role === "regional_manager") return "/gerente/visao-geral";
  return null;
}

export function createIdempotencyKey(): string {
  const uuid = globalThis.crypto?.randomUUID?.();
  return uuid ?? `nb-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export function getIdempotencyKey(
  previous: { fingerprint: string; key: string } | null,
  fingerprint: string,
): { fingerprint: string; key: string } {
  if (previous?.fingerprint === fingerprint) return previous;
  return { fingerprint, key: createIdempotencyKey() };
}
/** Preserva a chave após timeout ou refresh na MESMA aba, evitando dupla submissão. */
export const TRANSFER_KEY_STORAGE = "nandbank.transfer-key.v1";
export function readTransferKey(): { fingerprint: string; key: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(TRANSFER_KEY_STORAGE);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (value && typeof value === "object" && "fingerprint" in value && "key" in value &&
        typeof value.fingerprint === "string" && typeof value.key === "string" && value.key.length >= 8) {
      return { fingerprint: value.fingerprint, key: value.key };
    }
  } catch { /* sessão sem armazenamento */ }
  return null;
}
export function writeTransferKey(value: { fingerprint: string; key: string } | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value) window.sessionStorage.setItem(TRANSFER_KEY_STORAGE, JSON.stringify(value));
    else window.sessionStorage.removeItem(TRANSFER_KEY_STORAGE);
  } catch { /* sessão sem armazenamento */ }
}
