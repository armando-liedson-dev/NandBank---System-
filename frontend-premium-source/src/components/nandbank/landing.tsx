import { Link } from "@tanstack/react-router";
import { useEffect } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  CreditCard,
  Globe2,
  Landmark,
  Network,
  ShieldCheck,
  Wallet,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { SiteFooter, SiteHeader } from "@/components/nandbank/shells";
import { errorMessage, useNandQuery } from "@/lib/nandbank/query";
import heroPhoto from "@/assets/nandbank-hero-antonius-ferret.jpg.asset.json";
import { gateway } from "@/services/api/client";

const pillars = [
  {
    number: "01",
    icon: Wallet,
    title: "Contas em várias regiões",
    text: "Consulte contas e saldos por moeda, sem misturar divisas diferentes.",
  },
  {
    number: "02",
    icon: Globe2,
    title: "Transferências entre regiões",
    text: "Prepare operações entre contas através das rotas académicas suportadas.",
  },
  {
    number: "03",
    icon: CreditCard,
    title: "Cartões virtuais académicos",
    text: "Peça e acompanhe cartões de demonstração sujeitos a aprovação.",
  },
  {
    number: "04",
    icon: Network,
    title: "Continuidade distribuída",
    text: "Acompanhe o estado dos nós regionais quando o Gateway disponibiliza essa informação.",
  },
];

export function LandingPage() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const items = document.querySelectorAll<HTMLElement>(".benefit-item, .region-tile, .workflow-list li, .section-heading-row, .security-feature");
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("reveal-visible");
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: 0.08, rootMargin: "0px 0px -16px 0px" });
    items.forEach((item) => { item.classList.add("reveal-pending"); observer.observe(item); });
    return () => { observer.disconnect(); items.forEach((item) => item.classList.remove("reveal-pending", "reveal-visible")); };
  }, []);
  const heroImageUrl = import.meta.env["VITE_LOCAL_ASSETS"] === "true" ? "/static/images/nandbank-hero-antonius-ferret.jpg" : heroPhoto.url;
  const health = useNandQuery(
    ["gateway-health"],
    gateway.health,
    { status: "preview", app: "NandBank", timestamp: "" },
  );
  const connection = health.isPending
    ? "A verificar o Gateway"
    : health.isError
      ? errorMessage(health.error)
      : health.data?.status === "ok"
        ? "Gateway ligado"
        : "Pré-visualização activa";

  return (
    <div className="public-site">
      <SiteHeader />
      <main id="conteudo">
        <section className="hero-section">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="eyebrow eyebrow-gold">Banca digital distribuída · projecto académico</p>
              <h1>O seu dinheiro.<br /><span>Sem fronteiras.</span></h1>
              <p className="hero-description">
                Uma experiência digital para contas regionais, transferências entre moedas suportadas e gestão clara — ligada ao Gateway NandBank existente.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg" className="min-h-12 px-6">
                  <Link to="/criar-conta">Criar conta <ArrowRight aria-hidden="true" /></Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="hero-outline-button min-h-12 border-primary-foreground/40 bg-transparent px-6 text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground">
                  <Link to="/entrar">Entrar</Link>
                </Button>
              </div>
              <div className="hero-trust-row">
                <span><ShieldCheck aria-hidden="true" /> Permissões por perfil</span>
                <span><Globe2 aria-hidden="true" /> Seis regiões académicas</span>
                <span className="gateway-indicator"><i aria-hidden="true" />{connection}</span>
              </div>
            </div>
            <figure className="hero-visual">
              <img
                src={heroImageUrl}
                alt="Profissional africana a consultar o telemóvel e o computador"
                className="hero-photo"
                fetchPriority="high"
              />
              <figcaption className="hero-photo-caption">
                <span>Uma experiência para um mundo ligado</span>
                <span className="caption-index">Nº 01 / NandBank</span>
              </figcaption>
            </figure>
          </div>
          <div className="hero-bottom-rule" />
        </section>

        <section id="servicos" className="benefit-section">
          <div className="section-wrap">
            <div className="benefit-intro">
              <p className="eyebrow eyebrow-ink">Vantagens NandBank</p>
              <h2>Mais clareza para cada movimento.</h2>
              <p>Uma interface pensada para acompanhar operações distribuídas sem esconder o que ainda depende do servidor.</p>
            </div>
            <div className="benefit-list">
              {pillars.map((item) => {
                const Icon = item.icon;
                return (
                  <article key={item.number} className="benefit-item">
                    <div className="benefit-item-top"><span>{item.number}</span><Icon aria-hidden="true" /></div>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="network-section">
          <div className="section-wrap network-grid">
            <div>
              <p className="eyebrow eyebrow-gold">Uma rede académica</p>
              <h2>Seis regiões.<br /><span>Uma visão conectada.</span></h2>
              <p className="network-copy">
                A arquitectura separa a experiência do cliente da operação dos nós regionais. Os painéis mostram apenas os dados que o Gateway autoriza e devolve.
              </p>
              <Button asChild variant="outline" className="network-link-button mt-7 min-h-11 border-primary-foreground/35 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground">
                <Link to="/gerente/infraestrutura">Ver infraestrutura <ArrowUpRight aria-hidden="true" /></Link>
              </Button>
            </div>
            <div className="region-grid" aria-label="Regiões do projecto">
              {[
                ["AF", "África"], ["EU", "Europa"], ["AS", "Ásia"],
                ["NA", "América do Norte"], ["SA", "América do Sul"], ["OC", "Oceânia"],
              ].map(([code, name]) => (
                <div className="region-tile" key={code}>
                  <span className="region-code">{code}</span><span>{name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="funciona" className="workflow-section">
          <div className="section-wrap">
            <div className="section-heading-row">
              <div>
                <p className="eyebrow eyebrow-ink">Como funciona</p>
                <h2>Do acesso à operação, com contexto.</h2>
              </div>
              <p className="section-heading-note">Cada etapa depende da resposta real do Gateway. A interface não confirma operações por conta própria.</p>
            </div>
            <ol className="workflow-list">
              <li><span>01</span><Landmark aria-hidden="true" /><div><h3>Crie o seu acesso</h3><p>Registo validado pelo Gateway com filial suportada.</p></div></li>
              <li><span>02</span><Wallet aria-hidden="true" /><div><h3>Consulte as suas contas</h3><p>Veja cada saldo na moeda e região correspondentes.</p></div></li>
              <li><span>03</span><ArrowRight aria-hidden="true" /><div><h3>Confirme uma transferência</h3><p>Reveja a cotação devolvida e o resultado da operação distribuída.</p></div></li>
            </ol>
          </div>
        </section>

        <section id="seguranca" className="security-section">
          <div className="section-wrap security-grid">
            <div className="security-emblem"><ShieldCheck aria-hidden="true" /></div>
            <div>
              <p className="eyebrow eyebrow-gold">Segurança e transparência</p>
              <h2>Dados reais quando ligados.<br />Estados honestos quando não.</h2>
              <p>O NandBank é um projecto académico. As permissões, o estado da sessão e os resultados financeiros vêm do Gateway; a interface não guarda palavras-passe nem inventa disponibilidade.</p>
            </div>
            <div className="security-note">
              <span className="security-note-line" />
              <p>Operações fictícias.<br />Sem ligação a bancos reais.</p>
            </div>
          </div>
        </section>

        <section className="closing-section">
          <div className="section-wrap closing-inner">
            <div>
              <p className="eyebrow eyebrow-gold">NandBank · protótipo académico</p>
              <h2>Uma nova forma de acompanhar a banca distribuída.</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="min-h-12 px-6"><Link to="/criar-conta">Criar conta <ArrowRight aria-hidden="true" /></Link></Button>
              <Button asChild size="lg" variant="outline" className="hero-outline-button min-h-12 border-primary-foreground/40 bg-transparent px-6 text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"><Link to="/entrar">Entrar</Link></Button>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}