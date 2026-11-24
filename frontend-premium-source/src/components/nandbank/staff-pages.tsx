import { useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Activity, ArrowRight, Building2, CircleAlert, Landmark, RefreshCw, Search, Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DashboardShell } from "@/components/nandbank/shells";
import { errorMessage, useNandQuery } from "@/lib/nandbank/query";
import { createIdempotencyKey, DEMO_MODE, gateway } from "@/services/api/client";
import type { GatewayRole } from "@/services/api/types";

type RawAccount = { id: string; name: string; email: string; branch: string; region: string; currency: string };
type RawOperation = { id: string; account_id: string; operation_type: string; amount_minor: number; status: string; created_at: string };

function Roles({ role, allowed }: { role: GatewayRole | undefined; allowed: GatewayRole[] }) {
  if (!role || allowed.includes(role)) return null;
  return <section role="alert" className="staff-alert"><CircleAlert />Este perfil não está autorizado a usar esta área.</section>;
}

export function BranchOverviewPage() {
  const profile = useNandQuery(["staff-profile"], gateway.me);
  const stats = useNandQuery(["branch-stats"], gateway.adminStats);
  const accounts = useNandQuery(["branch-accounts"], gateway.adminAccounts);
  const role = profile.data?.user.role;
  const valid = role === "branch_manager";
  return <DashboardShell mode="branch" eyebrow="Gestão de filial" title="Visão geral">
    <div className="page-stack manager-stack">
      <div className="page-intro manager-page-intro"><div><p className="eyebrow eyebrow-gold">NandBank · Filial</p><h2>Gestão de {profile.data?.user.branch ?? "filial"}</h2><p>Informações limitadas à filial autorizada pelo Gateway.</p></div><Button variant="secondary" onClick={() => { void stats.refetch(); void accounts.refetch(); }}><RefreshCw /> Actualizar</Button></div>
      {profile.isError && <p role="alert" className="staff-alert">{errorMessage(profile.error)}</p>}
      <Roles role={role} allowed={["branch_manager"]} />
      {valid && <>
        {stats.isError && <p role="alert" className="staff-alert">{errorMessage(stats.error)}</p>}
        <div className="staff-stats">
          <article className="staff-stat"><Building2 /><strong>{profile.data?.user.branch}</strong><span>Filial autorizada</span></article>
          <article className="staff-stat"><Wallet /><strong>{stats.data?.clients ?? "—"}</strong><span>Clientes registados</span></article>
          <article className="staff-stat"><Activity /><strong>{Object.values(stats.data?.operations ?? {}).reduce((a, b) => a + b, 0)}</strong><span>Operações de balcão</span></article>
          <article className="staff-stat"><Landmark /><strong>{Array.isArray(accounts.data) ? accounts.data.length : "—"}</strong><span>Contas da filial</span></article>
        </div>
        <div className="staff-actions">
          <Link to="/filial/operacoes" className="staff-action"><Landmark /><strong>Depósitos e levantamentos</strong><span>Executar operações autorizadas</span><ArrowRight /></Link>
          <Link to="/filial/clientes" className="staff-action"><Wallet /><strong>Registos de clientes</strong><span>Consultar e gerir contas da filial</span><ArrowRight /></Link>
        </div>
      </>}
    </div>
  </DashboardShell>;
}

export function TellerOperationsPage({ branch = false }: { branch?: boolean }) {
  const profile = useNandQuery(["staff-profile"], gateway.me);
  const accountsQuery = useNandQuery(["staff-accounts"], gateway.adminAccounts);
  const operations = useNandQuery(["staff-operations"], gateway.operations);
  const currencies = useNandQuery(["staff-config"], gateway.config);
  const queryClient = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [operation, setOperation] = useState<"deposit" | "withdraw">("deposit");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("");
  const [search, setSearch] = useState("");
  const [confirmed, setConfirmed] = useState<null | { operation_id: string; balance_minor: number }>(null);
  const operationKey = useRef(createIdempotencyKey());
  const rawAccounts = Array.isArray(accountsQuery.data) ? accountsQuery.data as RawAccount[] : [];
  const role = profile.data?.user.role;
  const valid = branch ? role === "branch_manager" : role === "teller";
  const selectedAccount = rawAccounts.find((a) => a.id === accountId);
  const accounts = useMemo(() => rawAccounts.filter((a) => [a.name, a.email, a.branch, a.id].some((v) => String(v ?? "").toLowerCase().includes(search.toLowerCase()))).slice(0, 50), [rawAccounts, search]);
  const actions = Array.isArray(operations.data) ? operations.data as RawOperation[] : [];
  const mutation = useMutation({
    mutationFn: async () => {
      const id = accountId.trim();
      if (!id || !amount || Number(amount) <= 0) throw new Error("Seleccione uma conta e um montante positivo.");
      if (!selectedAccount) throw new Error("A conta escolhida não pertence às contas disponibilizadas para esta filial.");
      if (!currency) throw new Error("Seleccione a moeda da operação.");
      if (operation === "withdraw" && currency !== selectedAccount.currency) throw new Error("O levantamento deve usar a moeda da conta.");
      return operation === "deposit"
        ? gateway.tellerDeposit(id, amount, currency, operationKey.current)
        : gateway.tellerWithdraw(id, amount, currency, operationKey.current);
    },
    onSuccess: (result) => {
      setConfirmed({ operation_id: result.operation_id, balance_minor: result.balance_minor });
      operationKey.current = createIdempotencyKey();
      setAmount("");
      void queryClient.invalidateQueries({ queryKey: ["staff-operations"] });
      void queryClient.invalidateQueries({ queryKey: ["branch-stats"] });
    },
  });
  const changeAccount = (id: string) => {
    setAccountId(id); setCurrency(rawAccounts.find((a) => a.id === id)?.currency ?? "");
    setConfirmed(null); mutation.reset(); operationKey.current = createIdempotencyKey();
  };
  const changeOperation = (op: "deposit" | "withdraw") => {setOperation(op);setConfirmed(null);mutation.reset();operationKey.current=createIdempotencyKey();};
  return <DashboardShell mode={branch ? "branch" : "teller"} title="Operações de balcão" eyebrow={branch ? "Gestão de filial" : "Operador de balcão"}>
    <div className="page-stack manager-stack">
      <div className="page-intro manager-page-intro"><div><p className="eyebrow eyebrow-gold">NandBank · Balcão</p><h2>Depósitos e levantamentos.</h2><p>Operações reais do protótipo para a filial {profile.data?.user.branch ?? "autorizada"}.</p></div></div>
      {profile.isError && <p role="alert" className="staff-alert">{errorMessage(profile.error)}</p>}
      <Roles role={role} allowed={branch ? ["branch_manager"] : ["teller"]} />
      {valid && <>
        <section className="staff-panel">
          <div className="staff-panel-heading"><h3>Seleccionar conta do cliente</h3><span>{rawAccounts.length} contas no âmbito autorizado</span></div>
          {accountsQuery.isError && <p role="alert" className="staff-alert">{errorMessage(accountsQuery.error)}</p>}
          <label className="staff-field"><span>Pesquisar por nome, email ou ID</span><div className="staff-search"><Search /><Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Pesquisar conta de cliente" /></div></label>
          <label className="staff-field"><span>Conta bancária</span><select className="staff-native-select" value={accountId} onChange={(e) => changeAccount(e.target.value)} disabled={mutation.isPending}><option value="">Seleccione uma conta...</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name} · {a.branch} · {a.currency} · {a.id.slice(0, 8)}</option>)}</select></label>
          {selectedAccount && <p className="staff-account-info"><strong>{selectedAccount.name}</strong> · {selectedAccount.email} · {selectedAccount.branch} · {selectedAccount.currency}</p>}
        </section>
        <section className="staff-panel">
          <div className="staff-panel-heading"><h3>Nova operação</h3><span>Moedas de demonstração</span></div>
          <div className="staff-tabs"><button type="button" aria-pressed={operation === "deposit"} className={operation === "deposit" ? "active" : ""} onClick={() => changeOperation("deposit")}>Depósito</button><button type="button" aria-pressed={operation === "withdraw"} className={operation === "withdraw" ? "active" : ""} onClick={() => changeOperation("withdraw")}>Levantamento</button></div>
          <form className="staff-form" onSubmit={(e) => {e.preventDefault();setConfirmed(null);mutation.mutate();}}>
            <label className="staff-field"><span>Montante</span><Input type="number" min="0.01" step="0.01" required value={amount} onChange={(e) => {setAmount(e.target.value);operationKey.current=createIdempotencyKey();}} placeholder="0.00" /></label>
            <label className="staff-field"><span>Moeda</span><select className="staff-native-select" value={currency} required onChange={(e) => {setCurrency(e.target.value);operationKey.current=createIdempotencyKey();}}>{!currency && <option value="">Seleccione moeda</option>}{(currencies.data?.currencies ?? ["MZN", "EUR", "USD", "CNY", "ZAR", "GHS"]).map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
            <Button className="staff-submit" type="submit" disabled={mutation.isPending || !selectedAccount || !currency || !amount || Number(amount) <= 0 || DEMO_MODE}>{mutation.isPending ? "A processar..." : operation === "deposit" ? "Confirmar depósito" : "Confirmar levantamento"}</Button>
          </form>
          <p className="staff-note">Em caso de falha de rede, mantenha os mesmos dados e tente novamente com o mesmo identificador. Não duplique a transacção.</p>
          {mutation.isError && <p role="alert" className="staff-alert">{errorMessage(mutation.error)}<br />A mesma chave de idempotência será usada se repetir sem alterar o formulário.</p>}
          {confirmed && <p role="status" className="staff-success">Operação confirmada! Referência: <code>{confirmed.operation_id}</code> · Novo saldo: {(confirmed.balance_minor/100).toFixed(2)} {selectedAccount?.currency}</p>}
        </section>
        <section className="staff-panel"><div className="staff-panel-heading"><h3>Movimentos da filial</h3><Button variant="outline" onClick={() => void operations.refetch()}><RefreshCw /> Actualizar</Button></div>
          {operations.isError && <p className="staff-alert">{errorMessage(operations.error)}</p>}
          <div className="staff-list">{actions.slice(0, 25).map((o) => <article key={o.id}><div><strong>{o.operation_type}</strong><small>{o.account_id}</small></div><div><strong>{(o.amount_minor/100).toFixed(2)}</strong><small>{o.status}</small></div></article>)}{actions.length === 0 && !operations.isPending && <p>Ainda não há movimentos nesta filial.</p>}</div>
        </section>
      </>}
    </div>
  </DashboardShell>;
}
