import { createFileRoute } from "@tanstack/react-router";

import { GlobalAuditPage } from "@/components/nandbank/manager-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/gerente-global/auditoria")({
  head: () => ({ meta: pageMeta("NandBank | Auditoria global", "Diário de auditoria do Gateway reservado ao gerente global.") }),
  component: GlobalAuditPage,
});