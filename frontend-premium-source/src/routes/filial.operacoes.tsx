import { createFileRoute } from "@tanstack/react-router";
import { TellerOperationsPage } from "@/components/nandbank/staff-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/filial/operacoes")({
  head: () => ({ meta: pageMeta("NandBank | Operacoes", "Área protegida de gestão bancária NandBank.") }),
  component: () => <TellerOperationsPage branch />,
});
