import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "@/components/nandbank/landing";
import { pageMeta } from "@/lib/nandbank/meta";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: pageMeta(
      "NandBank | Banca digital distribuída",
      "Experiência académica de banca digital distribuída, preparada para o Gateway FastAPI NandBank.",
    ),
  }),
  component: LandingPage,
});
