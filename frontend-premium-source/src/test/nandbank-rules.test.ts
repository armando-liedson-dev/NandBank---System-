import { describe, expect, it, vi } from "vitest";

import { resolveNandQuery } from "@/lib/nandbank/query";
import { isValidRegistrationPassword } from "@/lib/nandbank/validation";
import { getIdempotencyKey } from "@/services/api/client";

describe("NandBank input safeguards", () => {
  it("requires a 12-character registration password with upper, lower, and numeric characters", () => {
    expect(isValidRegistrationPassword("BankPass2026")).toBe(true);
    expect(isValidRegistrationPassword("Bankpass202")).toBe(false);
    expect(isValidRegistrationPassword("bankpass2026")).toBe(false);
  });

  it("reuses one idempotency key for retries and creates a new key for changed transfer details", () => {
    const first = getIdempotencyKey(null, "source-A|destination-B|25.00");
    const retry = getIdempotencyKey(first, "source-A|destination-B|25.00");
    const changed = getIdempotencyKey(retry, "source-A|destination-B|26.00");

    expect(first.key.length).toBeGreaterThanOrEqual(8);
    expect(retry.key).toBe(first.key);
    expect(changed.key).not.toBe(first.key);
  });

  it("uses demo records only when demo mode is explicitly enabled", async () => {
    const demoData = { balance: 250, currency: "MZN" };
    const gatewayData = { balance: 0, currency: "MZN" };
    const gatewayQuery = vi.fn().mockResolvedValue(gatewayData);

    await expect(resolveNandQuery(false, demoData, gatewayQuery)).resolves.toBe(gatewayData);
    expect(gatewayQuery).toHaveBeenCalledOnce();
    await expect(resolveNandQuery(true, demoData, gatewayQuery)).resolves.toBe(demoData);
  });
});