import { createFileRoute } from "@tanstack/react-router";
import { CustomerManagementPage } from "@/components/nandbank/customer-management";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente-global/clientes")({
  head: () => ({ meta: pageMeta("NandBank | Clientes", "Área protegida de gestão bancária NandBank.") }),
  component: () => <CustomerManagementPage mode="global" />,
});
