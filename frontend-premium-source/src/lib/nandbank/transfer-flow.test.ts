import { describe, expect, it } from "vitest";
import { isTransferTerminal, transferStateMessage } from "./transfer-flow";
describe("estado definitivo de transferência 2PC", () => {
  it("não confunde PENDING com COMMITTED", () => {
    expect(isTransferTerminal("PENDING")).toBe(false);
    expect(isTransferTerminal("DECISION_COMMIT")).toBe(false);
    expect(isTransferTerminal("COMMITTED")).toBe(true);
    expect(isTransferTerminal("ABORTED")).toBe(true);
  });
  it("não anuncia sucesso antes da confirmação final", () => {
    expect(transferStateMessage("PENDING")).toContain("processamento");
    expect(transferStateMessage("COMMITTED")).toContain("concluída");
  });
});
