import { createFileRoute } from "@tanstack/react-router";

import { ClientCardsPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/cartoes")({
  head: () => ({ meta: pageMeta("NandBank | Cartões académicos", "Consulte pedidos e estados dos cartões virtuais académicos devolvidos pelo Gateway.") }),
  component: ClientCardsPage,
});