import { createFileRoute } from "@tanstack/react-router";

import { ManagerOverviewPage } from "@/components/nandbank/manager-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente/visao-geral")({
  head: () => ({ meta: pageMeta("NandBank | Painel regional", "Indicadores e estado regional devolvidos pelo Gateway NandBank.") }),
  component: () => <ManagerOverviewPage />,
});