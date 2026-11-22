import { createFileRoute } from "@tanstack/react-router";

import { LoginPage } from "@/components/nandbank/auth-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/entrar")({
  head: () => ({ meta: pageMeta("NandBank | Entrar", "Aceda à sua área do NandBank através do Gateway académico.") }),
  component: LoginPage,
});