import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CircleAlert, RefreshCw, Search, ShieldCheck, Trash2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DashboardShell } from "@/components/nandbank/shells";
import { errorMessage, useNandQuery } from "@/lib/nandbank/query";
import { DEMO_MODE, gateway } from "@/services/api/client";
import type { CustomerState, GatewayCustomer } from "@/services/api/types";

type Mode = "global" | "regional" | "branch";
const stateLabels: Record<CustomerState, string> = {
  ACTIVE: "Activa", SUSPENDED: "Conta suspensa", SUSPECT: "Conta suspeita", EXPIRED: "Conta expirada",
};

function valueDate(date?: string | null) { return date ? new Date(date).toLocaleString("pt-MZ") : "—"; }

export function CustomerManagementPage({ mode }: { mode: Mode }) {
  const profile = useNandQuery(["customer-management-profile"], gateway.me);
  const list = useNandQuery(["manager-customers"], gateway.customers);
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");
  const [region, setRegion] = useState("all");
  const [selectedId, setSelectedId] = useState("");
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [newState, setNewState] = useState<CustomerState>("ACTIVE");
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const allowed = profile.data && (mode === "global" ? profile.data.user.role === "global_manager" : mode === "regional" ? profile.data.user.role === "regional_manager" : profile.data.user.role === "branch_manager");
  const customers = list.data ?? [];
  const visible = useMemo(() => customers.filter((x) => (region === "all" || x.region === region || x.regions?.includes(region)) && [x.name, x.email, x.branch, x.id].some((v) => String(v ?? "").toLowerCase().includes(filter.toLowerCase()))), [customers, filter, region]);
  const regions = [...new Set(customers.map((x) => x.region).filter(Boolean))] as string[];
  const selected = customers.find((x) => x.id === selectedId);
  const details = useQuery({
    queryKey: ["manager-customer-detail", selectedId],
    queryFn: () => gateway.customerActivity(selectedId),
    enabled: !!selectedId && !!allowed && !DEMO_MODE,
    staleTime: 5_000,
    retry: false,
  });
  const statusMutation = useMutation({
    mutationFn: () => gateway.setCustomerStatus(selectedId, newState, reason.trim()),
    onSuccess: () => { setFeedback("Estado actualizado com auditoria. O histórico financeiro foi preservado."); setReason(""); void queryClient.invalidateQueries({ queryKey: ["manager-customers"] }); void queryClient.invalidateQueries({ queryKey: ["manager-customer-detail", selectedId] }); },
  });
  const editMutation = useMutation({
    mutationFn: () => gateway.updateCustomer(selectedId, editName, editEmail),
    onSuccess: () => { setFeedback("Dados do cliente actualizados."); void queryClient.invalidateQueries({ queryKey: ["manager-customers"] }); void queryClient.invalidateQueries({ queryKey: ["manager-customer-detail", selectedId] }); },
  });
  const deleteMutation = useMutation({
    mutationFn: () => gateway.permanentlyDeleteEmptyCustomer(selectedId, deleteConfirmation.trim()),
    onSuccess: () => {
      setSelectedId(""); setDeleteConfirmation("");
      void queryClient.invalidateQueries({ queryKey: ["manager-customers"] });
      void queryClient.invalidateQueries({ queryKey: ["staff-accounts"] });
      void queryClient.invalidateQueries({ queryKey: ["branch-stats"] });
    },
  });
  const open = (item: GatewayCustomer) => {
    setSelectedId(item.id);setDeleteConfirmation("");deleteMutation.reset();setEditName(item.name);setEditEmail(item.email);setNewState(item.status);setFeedback("");setReason("");
    statusMutation.reset();editMutation.reset();
  };
  const isRestricted = !allowed;
  return <DashboardShell mode={mode === "global" ? "global" : mode === "regional" ? "manager" : "branch"} eyebrow={mode === "global" ? "Administração global" : "Gestão autorizada"} title="Base de dados de clientes">
    <div className="page-stack manager-stack">
      <div className="page-intro manager-page-intro"><div><p className="eyebrow eyebrow-gold">NandBank · Clientes</p><h2>Registos e actividade dos clientes.</h2><p>{mode === "global" ? "Todas as regiões — gestão central" : mode === "regional" ? "Apenas clientes com contas nesta região" : "Apenas clientes com contas nesta filial"}. Consultar, actualizar e suspender sem apagar o histórico.</p></div><Button variant="secondary" onClick={() => void list.refetch()}><RefreshCw /> Actualizar</Button></div>
      {profile.isError && <p className="staff-alert">{errorMessage(profile.error)}</p>}
      {profile.data && isRestricted && <p role="alert" className="staff-alert"><ShieldCheck /> Sem permissão para gerir clientes neste âmbito.</p>}
      {allowed && <>
        {list.isError && <p role="alert" className="staff-alert">{errorMessage(list.error)}</p>}
        <section className="staff-panel">
          <div className="staff-panel-heading"><h3><Users className="inline-block" /> Clientes registados</h3><span>{customers.length} cliente(s) no âmbito autorizado</span></div>
          <div className="staff-filters"><label className="staff-field"><span>Pesquisar cliente</span><div className="staff-search"><Search /><Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Nome, email, filial ou ID" /></div></label>
          {mode === "global" && <label className="staff-field"><span>Região</span><select className="staff-native-select" value={region} onChange={(e) => setRegion(e.target.value)}><option value="all">Todas as regiões</option>{regions.map((x) => <option key={x} value={x}>{x.toUpperCase()}</option>)}</select></label>}</div>
          <div className="staff-customers-list">{visible.map((x) => <button type="button" key={x.id} className={selectedId === x.id ? "staff-customer active" : "staff-customer"} onClick={() => open(x)}><span><strong>{x.name}</strong><small>{x.email}</small><small>{(x.regions?.length ? x.regions.join(", ") : x.region)?.toUpperCase()} · {x.branch} · {x.account_count} conta(s)</small></span><span className={x.status === "ACTIVE" ? "staff-status active" : "staff-status"}>{stateLabels[x.status]}</span></button>)}{!list.isPending && !visible.length && <p>Nenhum cliente encontrado.</p>}</div>
        </section>
        {selected && <section className="staff-panel">
          <div className="staff-panel-heading"><h3>Ficha do cliente — {selected.name}</h3><span>Registado: {valueDate(selected.created_at)}</span></div>
          <p className="staff-note">Registo: <code>{selected.id}</code> · Estado: <strong>{stateLabels[selected.status]}</strong>{selected.status_reason ? ` · Motivo: ${selected.status_reason}` : ""}</p>
          {feedback && <p role="status" className="staff-success">{feedback}</p>}
          {details.isError && <p className="staff-alert">{errorMessage(details.error)}</p>}
          <form className="staff-form" onSubmit={(e) => {e.preventDefault();setFeedback("");editMutation.mutate();}}>
            <label className="staff-field"><span>Nome completo</span><Input value={editName} minLength={3} required onChange={(e) => setEditName(e.target.value)} /></label>
            <label className="staff-field"><span>Email</span><Input type="email" value={editEmail} required onChange={(e) => setEditEmail(e.target.value)} /></label>
            <Button type="submit" disabled={editMutation.isPending || DEMO_MODE} variant="outline">Guardar dados</Button>
          </form>
          {editMutation.isError && <p className="staff-alert">{errorMessage(editMutation.error)}</p>}
          <div className="staff-separator" />
          <h3 className="staff-subtitle">Suspender, sinalizar, expirar ou reactivar</h3>
          <p className="staff-note"><AlertTriangle className="inline-block" /> O estado EXPIRED funciona como exclusão lógica. Os movimentos e comprovativos permanecem guardados. Todas as alterações exigem justificação.</p>
          <form className="staff-form" onSubmit={(e) => {
            e.preventDefault();setFeedback("");
            if (!window.confirm(`Confirma a mudança do estado de ${selected.name} para ${stateLabels[newState]}?`)) return;
            statusMutation.mutate();
          }}>
            <label className="staff-field"><span>Novo estado</span><select className="staff-native-select" value={newState} onChange={(e) => setNewState(e.target.value as CustomerState)}><option value="ACTIVE">Activa / reactivar</option><option value="SUSPENDED">Conta suspensa</option><option value="SUSPECT">Conta suspeita</option><option value="EXPIRED">Conta expirada</option></select></label>
            <label className="staff-field staff-full"><span>Justificação obrigatória (mínimo 5 caracteres)</span><Input value={reason} minLength={5} maxLength={300} required onChange={(e) => setReason(e.target.value)} placeholder="Indique o motivo e a referência da intervenção" /></label>
            <Button type="submit" disabled={statusMutation.isPending || reason.trim().length < 5 || DEMO_MODE} variant={newState === "ACTIVE" ? "secondary" : "destructive"}>Aplicar alteração</Button>
          </form>
          {statusMutation.isError && <p role="alert" className="staff-alert">{errorMessage(statusMutation.error)}</p>}
          {mode !== "branch" && <div className="staff-delete-section">
            <h3 className="staff-subtitle"><Trash2 className="inline-block" /> Eliminar cliente definitivamente</h3>
            <p className="staff-note">Por segurança, esta opção apenas elimina registos com uma única conta, saldo zero, sem transferências, depósitos, movimentos ou cartões. Contas com histórico devem ser marcadas como expiradas.</p>
            <label className="staff-field"><span>Para confirmar escreva exactamente o email: {selected.email}</span>
              <Input type="email" autoComplete="off" value={deleteConfirmation} onChange={(e) => setDeleteConfirmation(e.target.value)} placeholder="Confirmar email do cliente" />
            </label>
            <Button type="button" className="staff-delete-button" disabled={DEMO_MODE || deleteMutation.isPending || deleteConfirmation.trim().toLowerCase() !== selected.email.toLowerCase()}
              onClick={() => {if (window.confirm(`Eliminar definitivamente ${selected.name}? Esta acção não pode ser revertida.`)) deleteMutation.mutate();}}>
              {deleteMutation.isPending ? "A verificar e eliminar..." : "Eliminar definitivamente"}
            </Button>
            {deleteMutation.isError && <p className="staff-alert" role="alert">{errorMessage(deleteMutation.error)}</p>}
          </div>}
          <div className="staff-separator" />
          <h3 className="staff-subtitle">Actividade bancária visível no âmbito autorizado</h3>
          {!details.data && <p>{details.isPending ? "A carregar movimentos..." : "Sem detalhes disponíveis."}</p>}
          {details.data && <>
            <h4 className="staff-small-heading">Contas ({details.data.accounts.length})</h4>
            <div className="staff-list">{details.data.accounts.map((x) => <article key={x.id}><div><strong>{x.branch} · {x.currency}</strong><small>{x.id}</small></div><span>{x.region.toUpperCase()}</span></article>)}</div>
            <h4 className="staff-small-heading">Depósitos / levantamentos ({details.data.operations.length})</h4>
            <div className="staff-list">{details.data.operations.map((x) => <article key={x.id}><div><strong>{x.operation_type}</strong><small>{x.account_id}</small></div><div><strong>{(x.amount_minor/100).toFixed(2)}</strong><small>{x.status}</small></div></article>)}{!details.data.operations.length && <p>Nenhuma operação registada.</p>}</div>
            <h4 className="staff-small-heading">Transferências ({details.data.transfers.length})</h4>
            <div className="staff-list">{details.data.transfers.map((x) => <article key={x.id}><div><strong>{x.source_currency} {(x.amount_minor/100).toFixed(2)}</strong><small>{x.id}</small></div><span>{x.status}</span></article>)}{!details.data.transfers.length && <p>Nenhuma transferência registada.</p>}</div>
            <h4 className="staff-small-heading">Cartões ({details.data.cards.length})</h4>
            <div className="staff-list">{details.data.cards.map((x) => <article key={x.id}><div><strong>•••• {x.last4}</strong><small>{x.account_id}</small></div><span>{x.status}</span></article>)}{!details.data.cards.length && <p>Sem cartões registados.</p>}</div>
          </>}
        </section>}
      </>}
    </div>
  </DashboardShell>;
}
