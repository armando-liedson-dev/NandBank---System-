import { useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  FileClock,
  Globe2,
  Network,
  RefreshCw,
  Server,
  ShieldCheck,
  Users,
  XCircle,
} from "lucide-react";

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DashboardShell } from "@/components/nandbank/shells";
import { errorMessage, useNandQuery } from "@/lib/nandbank/query";
import { formatDate, regionLabel } from "@/lib/nandbank/presentation";
import { DEMO_MODE, gateway } from "@/services/api/client";
import { DEMO_NODES, DEMO_STATS, DEMO_TRANSFERS } from "@/services/api/demo";
import type { GatewayMe, GatewayNode, GatewayRole } from "@/services/api/types";

const demoRegionalManager: GatewayMe = {
  user: { id: "demo-regional-manager", name: "Gestor regional de demonstração", email: "regional.demo@example.invalid", role: "regional_manager", region: "AF", branch: "Maputo" },
  accounts: [],
};
const demoGlobalManager: GatewayMe = {
  user: { id: "demo-global-manager", name: "Gestor global de demonstração", email: "global.demo@example.invalid", role: "global_manager" },
  accounts: [],
};

function ManagerIntro({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="page-intro manager-page-intro">
      <div className="min-w-0"><p className="eyebrow eyebrow-gold">NandBank · Gestão</p><h2>{title}</h2><p>{description}</p></div>
      {action && <div className="page-intro-action">{action}</div>}
    </div>
  );
}

function ManagerNotice({ loading, error, retry }: { loading: boolean; error: unknown; retry: () => unknown }) {
  if (loading) return <div role="status" className="resource-message manager-resource"><span className="loading-mark" />A consultar o Gateway…</div>;
  if (!error) return null;
  return (
    <section role="alert" className="resource-message resource-message-error manager-resource-error">
      <CircleAlert aria-hidden="true" /><div><strong>Dados de gestão indisponíveis.</strong><p>{errorMessage(error)}</p></div>
      <Button variant="secondary" size="sm" className="min-h-11" onClick={() => void retry()}><RefreshCw aria-hidden="true" /> Tentar novamente</Button>
    </section>
  );
}

function hasManagerRole(role: GatewayRole | undefined): boolean {
  return role === "regional_manager" || role === "global_manager";
}

function ManagerAccess({ role, globalOnly = false }: { role: GatewayRole | undefined; globalOnly?: boolean }) {
  if (!role) return null;
  if (globalOnly ? role === "global_manager" : hasManagerRole(role)) return null;
  return (
    <section role="alert" className="access-denied-panel">
      <ShieldCheck aria-hidden="true" /><div><h3>Área não autorizada</h3><p>O seu perfil não tem permissões para consultar esta informação. A autorização é validada pelo Gateway.</p></div>
      <Button asChild variant="secondary"><Link to="/entrar">Voltar a entrar</Link></Button>
    </section>
  );
}

function StatValue({ label, value, icon: Icon, detail }: { label: string; value: number | string | undefined; icon: typeof Users; detail: string }) {
  return (
    <article className="manager-stat">
      <div className="manager-stat-top"><span>{label}</span><Icon aria-hidden="true" /></div>
      <strong>{value == null ? "—" : value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function regionNodeTitle(node: GatewayNode): string {
  return node.name ?? node.region_name ?? regionLabel(node.code ?? node.region);
}

function nodeHealth(value: boolean | string | null | undefined): { label: string; className: string } {
  if (value === true || value === "UP") return { label: "Disponível", className: "node-health node-health-good" };
  if (value === false || value === "DOWN") return { label: "Indisponível", className: "node-health node-health-bad" };
  if (value === "CHECKING") return { label: "A verificar", className: "node-health node-health-unknown" };
  if (value === "RECOVERING") return { label: "Em recuperação", className: "node-health node-health-unknown" };
  return { label: "Sem estado", className: "node-health node-health-unknown" };
}

function NodeStatusCard({ node }: { node: GatewayNode }) {
  const primary = nodeHealth(node.primary_up ?? node.primary_status);
  const standby = nodeHealth(node.standby_up ?? node.standby_status);
  return (
    <article className="node-card">
      <div className="node-card-heading"><span className="node-card-icon"><Network aria-hidden="true" /></span><div className="min-w-0"><h3>{regionNodeTitle(node)}</h3><p>{node.code ?? node.region ?? "Código não devolvido"}</p></div><span className={nodeHealth(node.service_available).className}>{node.service_available === true ? "Serviço disponível" : node.service_available === false ? "Serviço indisponível" : "Estado não indicado"}</span></div>
      <div className="node-pair">
        <div><span className="node-role"><Server aria-hidden="true" /> Nó principal</span><strong className={primary.className}>{primary.label}</strong></div>
        <div><span className="node-role"><Server aria-hidden="true" /> Nó secundário</span><strong className={standby.className}>{standby.label}</strong></div>
      </div>
      {node.last_event ? <div className="node-last-event"><Activity aria-hidden="true" /><span>{node.last_event}</span><time>{formatDate(node.event_at ?? undefined)}</time></div> : <p className="node-empty-event">Sem evento recente devolvido pelo Gateway.</p>}
    </article>
  );
}

function getRecordField(record: unknown, key: string): string | null {
  if (record == null || typeof record !== "object") return null;
  const value = (record as Record<string, unknown>)[key];
  if (typeof value === "string" || typeof value === "number") return String(value);
  return null;
}

function countValues(values: Record<string, number> | undefined): number | undefined {
  if (!values) return undefined;
  return Object.values(values).reduce((total, value) => total + value, 0);
}

export function ManagerOverviewPage({ global = false }: { global?: boolean }) {
  const profile = useNandQuery(["manager-profile", global ? "global" : "regional"], gateway.me, global ? demoGlobalManager : demoRegionalManager);
  const stats = useNandQuery(["manager-stats"], gateway.adminStats, DEMO_STATS);
  const nodes = useNandQuery(["manager-nodes"], gateway.nodes, DEMO_NODES);
  const role = profile.data?.user.role;
  const scopedNodes = global ? nodes.data : nodes.data?.filter((node) => node.code === profile.data?.user.region || node.region === profile.data?.user.region);
  const title = global ? "Visão global da rede" : `Operação ${profile.data?.user.region ? `da região ${regionLabel(profile.data.user.region)}` : "regional"}`;

  return (
    <DashboardShell mode="manager" title={global ? "Visão global" : "Visão geral"} eyebrow={global ? "Gerência global" : "Gerência regional"}>
      <div className="page-stack manager-stack">
        <ManagerIntro title={title} description={global ? "Indicadores e estado de regiões devolvidos pelo Gateway, sem estimativas." : "Acompanhe serviços, operações e nós dentro do âmbito autorizado pelo Gateway."} action={<Button variant="secondary" onClick={() => { void profile.refetch(); void stats.refetch(); void nodes.refetch(); }}><RefreshCw aria-hidden="true" /> Actualizar</Button>} />
        <ManagerAccess role={role} globalOnly={global} />
        {(!role || hasManagerRole(role)) && <>
          <ManagerNotice loading={stats.isPending} error={stats.error} retry={stats.refetch} />
          <div className="manager-stat-grid">
            <StatValue label="Clientes" value={stats.data?.clients} icon={Users} detail="Total devolvido pelo Gateway" />
            <StatValue label="Transferências" value={countValues(stats.data?.transfers)} icon={ArrowRight} detail="Estados agregados disponíveis" />
            <StatValue label="Operações de balcão" value={countValues(stats.data?.operations)} icon={Activity} detail="Depósitos e levantamentos registados" />
            <StatValue label="Regiões" value={stats.data?.regions} icon={Globe2} detail="Âmbito reportado pela API" />
          </div>
          <section className="manager-section">
            <div className="section-title-row manager-section-title"><div><p className="eyebrow eyebrow-gold">Infraestrutura</p><h3>Estado dos nós</h3></div><Button asChild variant="link"><Link to="/gerente/infraestrutura">Ver infraestrutura <ArrowRight aria-hidden="true" /></Link></Button></div>
            <ManagerNotice loading={nodes.isPending} error={nodes.error} retry={nodes.refetch} />
            {scopedNodes?.length ? <div className="node-grid">{scopedNodes.map((node, index) => <NodeStatusCard key={node.code ?? node.region ?? index} node={node} />)}</div> : !nodes.isPending && !nodes.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>O Gateway ainda não devolveu o estado dos nós para este perfil.</p></div> : null}
          </section>
          {global && <section className="manager-section manager-global-link"><div><p className="eyebrow eyebrow-gold">Acesso global</p><h3>Diário de auditoria</h3><p>Consulta reservada ao gerente global.</p></div><Button asChild variant="secondary"><Link to="/gerente-global/auditoria">Abrir auditoria <ArrowRight aria-hidden="true" /></Link></Button></section>}
        </>}
      </div>
    </DashboardShell>
  );
}

const reasonOptions = [
  ["MAINTENANCE", "Manutenção programada"],
  ["FAULT", "Avaria interna"],
  ["SECURITY", "Incidente de segurança"],
  ["UPGRADE", "Actualização"],
  ["FAILOVER_TEST", "Teste de tolerância a falhas"],
  ["OTHER", "Outro motivo"],
] as const;

type NodeActionChoice = { code: string; action: "STOP_PRIMARY" | "START_PRIMARY"; label: string };

export function ManagerInfrastructurePage() {
  const queryClient = useQueryClient();
  const profile = useNandQuery(["manager-profile", "regional"], gateway.me, demoRegionalManager);
  const nodes = useNandQuery(["manager-nodes"], gateway.nodes, DEMO_NODES);
  const actions = useNandQuery(["manager-node-actions"], gateway.nodeActions, { agent_online: false, jobs: [] });
  const [choice, setChoice] = useState<NodeActionChoice | null>(null);
  const [reason, setReason] = useState<(typeof reasonOptions)[number][0]>("MAINTENANCE");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const requestAction = useMutation({
    mutationFn: () => {
      if (!choice) throw new Error("Seleccione primeiro uma acção.");
      return gateway.requestNodeAction(choice.code, choice.action, reason, note.trim());
    },
    onSuccess: async (result) => {
      setMessage(result.message);
      setChoice(null);
      setNote("");
      await queryClient.invalidateQueries({ queryKey: ["manager-node-actions"] });
      await queryClient.invalidateQueries({ queryKey: ["manager-nodes"] });
    },
    onError: (error) => setMessage(errorMessage(error)),
  });
  const role = profile.data?.user.role;
  const canControl = role === "regional_manager" || role === "global_manager";
  const scopedNodes = role === "global_manager" ? nodes.data : nodes.data?.filter((node) => node.code === profile.data?.user.region || node.region === profile.data?.user.region);

  return (
    <DashboardShell mode="manager" title="Infraestrutura" eyebrow="Gestão de nós">
      <div className="page-stack manager-stack">
        <ManagerIntro title="Infraestrutura distribuída." description="O estado e os pedidos de intervenção são os que o Gateway devolve. A execução depende do agente Windows no servidor." action={<Button variant="secondary" onClick={() => { void nodes.refetch(); void actions.refetch(); }}><RefreshCw aria-hidden="true" /> Actualizar</Button>} />
        <ManagerAccess role={role} />
        {(!role || hasManagerRole(role)) && <>
          <div className="agent-status-line"><span className={actions.data?.agent_online ? "agent-dot agent-dot-online" : "agent-dot"} aria-hidden="true" /><strong>{actions.data?.agent_online ? "Agente Windows ligado" : "Estado do agente não confirmado"}</strong><span>{actions.data?.agent_online ? "O Gateway confirmou a ligação recente." : "Não é possível confirmar uma intervenção sem resposta do Gateway."}</span></div>
          <ManagerNotice loading={nodes.isPending} error={nodes.error} retry={nodes.refetch} />
          {scopedNodes?.length ? <div className="node-grid">{scopedNodes.map((node, index) => <NodeStatusCard key={node.code ?? node.region ?? index} node={node} />)}</div> : !nodes.isPending && !nodes.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>Não há estado de nó disponível para este perfil.</p></div> : null}
          <section className="manager-section">
            <div className="section-title-row manager-section-title"><div><p className="eyebrow eyebrow-gold">Intervenções</p><h3>Pedidos registados</h3></div></div>
            <ManagerNotice loading={actions.isPending} error={actions.error} retry={actions.refetch} />
            {actions.data?.jobs.length ? <div className="job-list">{actions.data.jobs.map((job) => <article className="job-row" key={job.id}><span className="job-icon"><Activity aria-hidden="true" /></span><div className="min-w-0"><strong>{job.action} · {regionLabel(job.region)}</strong><span>{job.reason} · {job.status}</span><small>{job.result ?? "A aguardar resultado do agente."}</small></div><time>{formatDate(job.updated_at ?? job.created_at)}</time></article>)}</div> : !actions.isPending && !actions.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>O Gateway não devolveu pedidos de intervenção.</p></div> : null}
          </section>
          {canControl && <section className="manager-action-section"><div><p className="eyebrow eyebrow-gold">Acções controladas</p><h3>Gestão do nó principal</h3><p>Cada pedido exige confirmação, motivo e validação do servidor.</p></div><div className="node-action-buttons">{scopedNodes?.map((node, index) => { const code = node.code ?? node.region; if (!code) return null; return <div className="node-action-row" key={code}><strong>{regionNodeTitle(node)}</strong><div><Button variant="secondary" disabled={DEMO_MODE || requestAction.isPending} onClick={() => { setChoice({ code, action: "STOP_PRIMARY", label: "Desligar nó principal" }); setReason("MAINTENANCE"); }}>Desligar principal</Button><Button disabled={DEMO_MODE || requestAction.isPending} onClick={() => { setChoice({ code, action: "START_PRIMARY", label: "Ligar nó principal" }); setReason("MAINTENANCE"); }}>Ligar principal</Button></div></div>; })}</div>{DEMO_MODE && <p className="field-note">Na demonstração, as acções que alteram nós estão desactivadas.</p>}{message && <p role={requestAction.isError ? "alert" : "status"} className={requestAction.isError ? "form-message form-message-error" : "form-message form-message-success"}>{message}</p>}</section>}
        </>}
      </div>
      <AlertDialog open={Boolean(choice)} onOpenChange={(open) => { if (!open) setChoice(null); }}>
        <AlertDialogContent className="confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar pedido de intervenção?</AlertDialogTitle>
            <AlertDialogDescription>{choice?.label} em {choice ? regionLabel(choice.code) : "região seleccionada"}. O pedido só será concluído se o Gateway e o agente Windows o confirmarem.</AlertDialogDescription>
          </AlertDialogHeader>
          <label className="form-field"><span>Motivo</span><Select value={reason} onValueChange={(value) => setReason(value as (typeof reasonOptions)[number][0])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{reasonOptions.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></label>
          <label className="form-field"><span>Nota <small className="inline-note">(opcional)</small></span><Input value={note} onChange={(event) => setNote(event.target.value)} maxLength={300} /></label>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction disabled={DEMO_MODE || requestAction.isPending} onClick={(event) => { event.preventDefault(); requestAction.mutate(); setChoice(null); }}>
              {requestAction.isPending ? "A enviar…" : "Enviar pedido"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardShell>
  );
}

export function ManagerOperationsPage() {
  const queryClient = useQueryClient();
  const profile = useNandQuery(["manager-profile", "regional"], gateway.me, demoRegionalManager);
  const operations = useNandQuery(["manager-operations"], gateway.operations, DEMO_TRANSFERS);
  const cards = useNandQuery(["manager-pending-cards"], gateway.pendingCards, []);
  const [message, setMessage] = useState<string | null>(null);
  const review = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) => gateway.reviewCard(id, approved),
    onSuccess: async (result) => {
      setMessage(`Pedido actualizado pelo Gateway: ${result.status}.`);
      await queryClient.invalidateQueries({ queryKey: ["manager-pending-cards"] });
    },
    onError: (error) => setMessage(errorMessage(error)),
  });
  const role = profile.data?.user.role;
  const canReview = hasManagerRole(role);

  return (
    <DashboardShell mode="manager" title="Operações" eyebrow="Gestão regional">
      <div className="page-stack manager-stack">
        <ManagerIntro title="Operações e pedidos." description="Consulte registos e pedidos de cartão dentro do âmbito que o Gateway autoriza." action={<Button variant="secondary" onClick={() => { void operations.refetch(); void cards.refetch(); }}><RefreshCw aria-hidden="true" /> Actualizar</Button>} />
        <ManagerAccess role={role} />
        {(!role || hasManagerRole(role)) && <>
          <div className="manager-columns">
            <section className="manager-section"><div className="section-title-row manager-section-title"><div><p className="eyebrow eyebrow-gold">Actividade</p><h3>Operações recentes</h3></div></div><ManagerNotice loading={operations.isPending} error={operations.error} retry={operations.refetch} />{operations.data?.length ? <div className="job-list">{operations.data.map((item, index) => <article className="job-row" key={getRecordField(item, "id") ?? index}><span className="job-icon"><Activity aria-hidden="true" /></span><div className="min-w-0"><strong>{getRecordField(item, "operation_type") ?? "Operação"}</strong><span>{getRecordField(item, "status") ?? "Estado não fornecido"}</span><small>{getRecordField(item, "account_id") ?? getRecordField(item, "id") ?? "Referência não fornecida"}</small></div><time>{formatDate(getRecordField(item, "created_at") ?? undefined)}</time></article>)}</div> : !operations.isPending && !operations.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>Não existem operações disponíveis para este perfil.</p></div> : null}</section>
            <section className="manager-section"><div className="section-title-row manager-section-title"><div><p className="eyebrow eyebrow-gold">Aprovação</p><h3>Pedidos de cartão</h3></div></div><ManagerNotice loading={cards.isPending} error={cards.error} retry={cards.refetch} />{cards.data?.length ? <div className="pending-card-list">{cards.data.map((card) => <article className="pending-card-row" key={card.id}><div><strong>{card.holder_name ?? "Titular não indicado"}</strong><span>{card.branch ?? "Filial não indicada"} · {card.currency ?? "Moeda não indicada"}</span><small>{card.status} · {card.id}</small></div><div className="pending-card-actions"><Button size="sm" disabled={!canReview || DEMO_MODE || review.isPending} onClick={() => review.mutate({ id: card.id, approved: true })}><CircleCheck aria-hidden="true" /> Aprovar</Button><Button size="sm" variant="secondary" disabled={!canReview || DEMO_MODE || review.isPending} onClick={() => review.mutate({ id: card.id, approved: false })}><XCircle aria-hidden="true" /> Rejeitar</Button></div></article>)}</div> : !cards.isPending && !cards.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>Não há pedidos de cartão por analisar.</p></div> : null}{message && <p role={review.isError ? "alert" : "status"} className={review.isError ? "form-message form-message-error" : "form-message form-message-success"}>{message}</p>}{DEMO_MODE && <p className="field-note">Na demonstração, as decisões de aprovação não alteram dados.</p>}</section>
          </div>
        </>}
      </div>
    </DashboardShell>
  );
}

export function GlobalAuditPage() {
  const audit = useNandQuery(["global-audit"], gateway.audit, []);
  const profile = useNandQuery(["manager-profile", "global"], gateway.me, demoGlobalManager);
  const role = profile.data?.user.role;

  return (
    <DashboardShell mode="manager" title="Auditoria global" eyebrow="Controlo e auditoria">
      <div className="page-stack manager-stack">
        <ManagerIntro title="Diário de auditoria." description="Eventos registados pelo Gateway, disponíveis apenas ao gerente global." action={<Button variant="secondary" onClick={() => void audit.refetch()}><RefreshCw aria-hidden="true" /> Actualizar</Button>} />
        <ManagerAccess role={role} globalOnly />
        {(!role || role === "global_manager") && <section className="manager-section"><div className="section-title-row manager-section-title"><div><p className="eyebrow eyebrow-gold">Registos recentes</p><h3>Eventos disponíveis</h3></div><FileClock aria-hidden="true" /></div><ManagerNotice loading={audit.isPending} error={audit.error} retry={audit.refetch} />{audit.data?.length ? <div className="audit-list">{audit.data.map((item, index) => <article className="audit-row" key={getRecordField(item, "id") ?? index}><span className="audit-index">{String(index + 1).padStart(2, "0")}</span><div className="min-w-0"><strong>{getRecordField(item, "kind") ?? getRecordField(item, "event_type") ?? "Evento"}</strong><p>{getRecordField(item, "details") ?? getRecordField(item, "event") ?? "Detalhes não fornecidos"}</p><small>{getRecordField(item, "actor_id") ?? "Actor não indicado"}</small></div><time>{formatDate(getRecordField(item, "created_at") ?? undefined)}</time></article>)}</div> : !audit.isPending && !audit.isError ? <div className="manager-empty"><CircleHelp aria-hidden="true" /><p>O Gateway não devolveu eventos de auditoria.</p></div> : null}</section>}
      </div>
    </DashboardShell>
  );
}