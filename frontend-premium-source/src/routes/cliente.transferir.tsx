import { createFileRoute } from "@tanstack/react-router";

import { ClientTransferPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/transferir")({
  head: () => ({ meta: pageMeta("NandBank | Transferências", "Prepare transferências entre contas com cotação e confirmação do Gateway.") }),
  component: ClientTransferPage,
});