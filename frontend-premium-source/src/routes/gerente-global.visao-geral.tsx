import { createFileRoute } from "@tanstack/react-router";

import { ManagerOverviewPage } from "@/components/nandbank/manager-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente-global/visao-geral")({
  head: () => ({ meta: pageMeta("NandBank | Painel global", "Visão global de indicadores e estados regionais devolvidos pelo Gateway.") }),
  component: () => <ManagerOverviewPage global />,
});