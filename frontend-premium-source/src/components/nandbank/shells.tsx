import { useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  ArrowLeftRight,
  Building2,
  CreditCard,
  FileClock,
  Gauge,
  Globe2,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  MoreHorizontal,
  Network,
  ReceiptText,
  Settings2,
  Wallet,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { BrandLogo } from "@/components/nandbank/brand";
import { clearAccessToken, DEMO_MODE, DEMO_NOTICE } from "@/services/api/client";

const customerLinks = [
  { title: "Visão geral", to: "/cliente/visao-geral", icon: LayoutDashboard },
  { title: "As minhas contas", to: "/cliente/contas", icon: Wallet },
  { title: "Transferir", to: "/cliente/transferir", icon: ArrowLeftRight },
  { title: "Movimentos", to: "/cliente/movimentos", icon: History },
  { title: "Cartões digitais", to: "/cliente/cartoes", icon: CreditCard },
  { title: "Serviços", to: "/cliente/servicos", icon: Settings2 },
  { title: "Sobre o sistema", to: "/cliente/sistema", icon: Globe2 },
] as const;

const regionalLinks = [
  { title: "Visão geral", to: "/gerente/visao-geral", icon: Gauge },
  { title: "Infraestrutura", to: "/gerente/infraestrutura", icon: Network },
  { title: "Operações", to: "/gerente/operacoes", icon: ReceiptText },
  { title: "Visão global", to: "/gerente-global/visao-geral", icon: Globe2 },
  { title: "Auditoria global", to: "/gerente-global/auditoria", icon: FileClock },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <a href="#conteudo" className="skip-link">
        Saltar para o conteúdo
      </a>
      <header className="site-header">
        <div className="site-header-inner">
          <BrandLogo />
          <nav aria-label="Navegação principal" className="hidden items-center gap-8 md:flex">
            <a href="#servicos" className="site-nav-link">Serviços</a>
            <a href="#funciona" className="site-nav-link">Como funciona</a>
            <a href="#seguranca" className="site-nav-link">Segurança</a>
            <a href="#sobre" className="site-nav-link">Sobre nós</a>
          </nav>
          <div className="hidden items-center gap-3 md:flex">
            <Button asChild variant="outline" className="site-signin-button min-h-11 border-primary-foreground/35 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground">
              <Link to="/entrar">Entrar</Link>
            </Button>
            <Button asChild className="min-h-11 px-5">
              <Link to="/criar-conta">Criar conta</Link>
            </Button>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={open ? "Fechar menu" : "Abrir menu"}
            aria-expanded={open}
            className="text-ivory hover:bg-ivory/10 hover:text-ivory md:hidden"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X /> : <Menu />}
          </Button>
        </div>
        {open && (
          <nav aria-label="Navegação móvel" className="site-mobile-nav md:hidden">
            <a href="#servicos" onClick={() => setOpen(false)}>Serviços</a>
            <a href="#funciona" onClick={() => setOpen(false)}>Como funciona</a>
            <a href="#seguranca" onClick={() => setOpen(false)}>Segurança</a>
            <a href="#sobre" onClick={() => setOpen(false)}>Sobre nós</a>
            <Link to="/entrar" onClick={() => setOpen(false)}>Entrar</Link>
            <Link to="/criar-conta" onClick={() => setOpen(false)}>Criar conta</Link>
          </nav>
        )}
      </header>
    </>
  );
}

export function SiteFooter() {
  return (
    <footer id="sobre" className="site-footer">
      <div className="site-footer-inner">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <BrandLogo compact />
          <p className="max-w-xl text-sm leading-6 text-primary-foreground/70">
            Protótipo académico · Operações fictícias · Sem ligação a bancos reais.
          </p>
          <nav aria-label="Links do rodapé" className="flex flex-wrap gap-x-6 gap-y-3 text-sm">
            <Link to="/entrar" className="footer-link">Entrar</Link>
            <Link to="/criar-conta" className="footer-link">Criar conta</Link>
            <a href="#seguranca" className="footer-link">Segurança</a>
          </nav>
        </div>
        <div className="mt-8 flex flex-col gap-2 border-t border-primary-foreground/15 pt-5 text-xs text-primary-foreground/55 sm:flex-row sm:items-center sm:justify-between">
          <span>© {new Date().getFullYear()} NandBank</span>
          <span>Projecto académico de banca digital distribuída</span>
        </div>
      </div>
    </footer>
  );
}

export function DemoBanner() {
  if (!DEMO_MODE) return null;
  return (
    <div role="status" className="demo-banner">
      <span className="demo-banner-dot" aria-hidden="true" />
      {DEMO_NOTICE}
    </div>
  );
}

export function DashboardShell({
  children,
  title,
  eyebrow,
  mode,
}: {
  children: ReactNode;
  title: string;
  eyebrow: string;
  mode: "customer" | "manager";
}) {
  const currentPath = useRouterState({ select: (router) => router.location.pathname });
  const [moreOpen, setMoreOpen] = useState(false);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const links = mode === "customer" ? customerLinks : regionalLinks;
  const mobileLinks = mode === "customer" ? customerLinks.slice(0, 4) : links.slice(0, 4);

  async function signOut() {
    await queryClient.cancelQueries();
    queryClient.clear();
    clearAccessToken();
    await navigate({ to: "/entrar", replace: true });
  }

  return (
    <div className={mode === "manager" ? "app-frame app-frame-dark" : "app-frame"}>
      <aside className="app-sidebar hidden lg:flex">
        <div className="sidebar-brand"><BrandLogo compact /></div>
        <div className="sidebar-divider" />
        <div className="sidebar-section-label">{mode === "customer" ? "Área pessoal" : "Gestão"}</div>
        <nav aria-label="Navegação da área" className="sidebar-nav">
          {links.map((item) => {
            const Icon = item.icon;
            const active = currentPath === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={active ? "sidebar-link sidebar-link-active" : "sidebar-link"}
                aria-current={active ? "page" : undefined}
              >
                <Icon aria-hidden="true" />
                <span>{item.title}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-divider" />
          <p className="sidebar-footnote">Protótipo académico</p>
          <Button variant="ghost" className="sidebar-logout" onClick={() => void signOut()}>
            <LogOut aria-hidden="true" /> Terminar sessão
          </Button>
        </div>
      </aside>

      <div className="app-main min-w-0">
        <header className="app-topbar">
          <div className="flex min-w-0 items-center gap-3">
            <div className="lg:hidden"><BrandLogo compact tone={mode === "customer" ? "light" : "dark"} /></div>
            <div className="hidden min-w-0 lg:block">
              <p className="app-eyebrow">{eyebrow}</p>
              <h1 className="truncate text-lg font-semibold">{title}</h1>
            </div>
            <div className="min-w-0 lg:hidden">
              <p className="app-eyebrow">{eyebrow}</p>
              <h1 className="truncate text-base font-semibold">{title}</h1>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="academic-tag hidden sm:inline-flex">Sistema académico</span>
            <Button asChild variant="ghost" size="icon" aria-label="Ir para a página inicial" className="hidden sm:inline-flex">
              <Link to="/"><Building2 /></Link>
            </Button>
          </div>
        </header>
        <main id="conteudo" className="app-content">
          <DemoBanner />
          {children}
        </main>
        <footer className="app-footer">
          <span>© {new Date().getFullYear()} NandBank · Protótipo académico</span>
          <span>Sem ligação a instituições financeiras reais</span>
        </footer>
      </div>

      <nav aria-label="Navegação móvel" className="mobile-bottom-nav lg:hidden">
        {mobileLinks.map((item) => {
          const Icon = item.icon;
          const active = currentPath === item.to;
          return (
            <Link key={item.to} to={item.to} className={active ? "mobile-nav-link mobile-nav-link-active" : "mobile-nav-link"}>
              <Icon aria-hidden="true" />
              <span>{item.title === "Visão geral" ? "Início" : item.title.split(" ")[0]}</span>
            </Link>
          );
        })}
        <Button variant="ghost" className="mobile-nav-link" aria-expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)}>
          {moreOpen ? <X aria-hidden="true" /> : <MoreHorizontal aria-hidden="true" />}
          <span>Mais</span>
        </Button>
      </nav>
      {moreOpen && (
        <div className="mobile-more-panel lg:hidden">
          {(mode === "customer" ? customerLinks.slice(4) : regionalLinks).map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.to} to={item.to} onClick={() => setMoreOpen(false)}>
                <Icon aria-hidden="true" />{item.title}
              </Link>
            );
          })}
          <Button variant="ghost" onClick={() => void signOut()}><LogOut aria-hidden="true" />Terminar sessão</Button>
        </div>
      )}
    </div>
  );
}