import { createFileRoute } from "@tanstack/react-router";

import { ManagerInfrastructurePage } from "@/components/nandbank/manager-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente/infraestrutura")({
  head: () => ({ meta: pageMeta("NandBank | Infraestrutura", "Consulte o estado dos nós e os pedidos de intervenção enviados ao Gateway.") }),
  component: ManagerInfrastructurePage,
});