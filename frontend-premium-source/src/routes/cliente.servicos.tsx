import { createFileRoute } from "@tanstack/react-router";

import { ClientServicesPage } from "@/components/nandbank/client-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/cliente/servicos")({
  head: () => ({ meta: pageMeta("NandBank | Serviços", "Aceda apenas às operações académicas suportadas pelo Gateway NandBank.") }),
  component: ClientServicesPage,
});