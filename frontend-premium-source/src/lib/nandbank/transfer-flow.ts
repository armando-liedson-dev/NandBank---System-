/** Ciclo de vida da transferência 2PC. Nunca deduzir sucesso a partir de HTTP 200. */
export const TERMINAL_TRANSFER_STATUSES = new Set(["COMMITTED", "ABORTED"]);
export const SUCCESS_TRANSFER_STATUS = "COMMITTED";
export const PENDING_TRANSFER_STATUSES = new Set([
  "NEW", "PREPARING", "PENDING", "DECISION_COMMIT", "DECISION_ABORT", "COMMITTING", "ABORTING",
]);
export function isTransferTerminal(status: string | undefined): boolean {
  return Boolean(status && TERMINAL_TRANSFER_STATUSES.has(status.toUpperCase()));
}
export function transferStateMessage(status: string): string {
  switch (status.toUpperCase()) {
    case "COMMITTED": return "Transferência concluída e confirmada pelo servidor.";
    case "ABORTED": return "Transferência cancelada pelo servidor. Confirme os saldos antes de tentar de novo.";
    default: return `Transferência em processamento (${status}). Aguarde a confirmação definitiva.`;
  }
}
export const PENDING_TRANSFER_STORAGE_KEY = "nandbank.pending-transfer.v1";
export interface PendingTransfer { id: string; fingerprint: string; status: string; }
export function readPendingTransfer(): PendingTransfer | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(PENDING_TRANSFER_STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && "id" in parsed && "fingerprint" in parsed &&
        typeof parsed.id === "string" && typeof parsed.fingerprint === "string" && parsed.id.length > 0) {
      return { id: parsed.id, fingerprint: parsed.fingerprint, status: "PENDING" };
    }
  } catch { /* dados não válidos devem ser ignorados */ }
  return null;
}
export function writePendingTransfer(pending: PendingTransfer | null): void {
  if (typeof window === "undefined") return;
  try {
    if (pending) window.sessionStorage.setItem(PENDING_TRANSFER_STORAGE_KEY, JSON.stringify(pending));
    else window.sessionStorage.removeItem(PENDING_TRANSFER_STORAGE_KEY);
  } catch { /* armazenamento indisponível não interrompe a confirmação */ }
}
