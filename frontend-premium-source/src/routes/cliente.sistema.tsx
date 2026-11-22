import { createFileRoute } from "@tanstack/react-router";

import { ClientSystemPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/sistema")({
  head: () => ({ meta: pageMeta("NandBank | Sobre o sistema", "Informação sobre a arquitectura académica distribuída do NandBank.") }),
  component: ClientSystemPage,
});