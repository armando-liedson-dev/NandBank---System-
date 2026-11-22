import { createFileRoute } from "@tanstack/react-router";

import { RegisterPage } from "@/components/nandbank/auth-pages";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/criar-conta")({
  head: () => ({ meta: pageMeta("NandBank | Criar conta", "Crie um acesso académico NandBank validado pelo Gateway FastAPI existente.") }),
  component: RegisterPage,
});