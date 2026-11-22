import { createFileRoute } from "@tanstack/react-router";

import { ClientMovementsPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/movimentos")({
  head: () => ({ meta: pageMeta("NandBank | Movimentos", "Histórico de transferências devolvido pelo Gateway NandBank.") }),
  component: ClientMovementsPage,
});