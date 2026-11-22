import { createFileRoute } from "@tanstack/react-router";

import { ClientAccountsPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/contas")({
  head: () => ({ meta: pageMeta("NandBank | As minhas contas", "Consulte contas regionais e dados bancários autorizados pelo Gateway NandBank.") }),
  component: ClientAccountsPage,
});