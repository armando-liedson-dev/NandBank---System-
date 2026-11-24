import { createFileRoute } from "@tanstack/react-router";
import { BranchOverviewPage } from "@/components/nandbank/staff-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/filial/visao-geral")({
  head: () => ({ meta: pageMeta("NandBank | Visao-Geral", "Área protegida de gestão bancária NandBank.") }),
  component: () => <BranchOverviewPage />,
});
