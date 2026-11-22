import { createFileRoute } from "@tanstack/react-router";

import { ManagerOperationsPage } from "@/components/nandbank/manager-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente/operacoes")({
  head: () => ({ meta: pageMeta("NandBank | Operações regionais", "Consulte operações e pedidos de cartão autorizados pelo Gateway NandBank.") }),
  component: ManagerOperationsPage,
});