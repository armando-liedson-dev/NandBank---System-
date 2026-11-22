export function formatMoney(amount: string | number | null | undefined, currency: string): string {
  if (amount == null || amount === "") return "—";
  const numeric = typeof amount === "number" ? amount / 100 : Number(amount.replace(/\s/g, "").replace(",", "."));
  if (!Number.isFinite(numeric)) return `${String(amount)} ${currency}`;
  try {
    return new Intl.NumberFormat("pt-MZ", { style: "currency", currency }).format(numeric);
  } catch {
    return `${new Intl.NumberFormat("pt-MZ", { maximumFractionDigits: 2 }).format(numeric)} ${currency}`;
  }
}

export function formatDate(value: string | undefined): string {
  if (!value) return "Data não fornecida";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-MZ", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function roleLabel(role: string | undefined): string {
  if (role === "client") return "Cliente";
  if (role === "regional_manager") return "Gerente regional";
  if (role === "global_manager") return "Gerente global";
  if (role === "branch_manager") return "Gerente de filial";
  if (role === "teller") return "Operador de balcão";
  return "Perfil sem área atribuída";
}

export function regionLabel(region: string | undefined): string {
  const names: Record<string, string> = {
    AF: "África",
    EU: "Europa",
    AS: "Ásia",
    NA: "América do Norte",
    SA: "América do Sul",
    OC: "Oceânia",
  };
  return region ? (names[region.toUpperCase()] ?? region) : "Região não indicada";
}