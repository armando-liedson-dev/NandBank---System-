import { createFileRoute } from "@tanstack/react-router";

import { ClientOverviewPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/visao-geral")({
  head: () => ({ meta: pageMeta("NandBank | Visão geral do cliente", "Consulte contas, saldos por moeda e operações devolvidas pelo Gateway NandBank.") }),
  component: ClientOverviewPage,
});