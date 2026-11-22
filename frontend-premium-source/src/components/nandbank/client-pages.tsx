import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  ArrowLeftRight,
  ArrowRight,
  BadgeCheck,
  Building2,
  CircleAlert,
  CircleHelp,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  Globe2,
  History,
  Landmark,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Wallet,
  RotateCcw,
  Wifi,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DashboardShell } from "@/components/nandbank/shells";
import { BrandMark } from "@/components/nandbank/brand";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { isTransferTerminal, readPendingTransfer, transferStateMessage, writePendingTransfer, type PendingTransfer } from "@/lib/nandbank/transfer-flow";
import { errorMessage, useNandQuery } from "@/lib/nandbank/query";
import { formatDate, formatMoney, regionLabel } from "@/lib/nandbank/presentation";
import { DEMO_CARDS, DEMO_CUSTOMER, DEMO_TRANSFERS } from "@/services/api/demo";
import {
  DEMO_MODE,
  DEMO_NOTICE,
  gateway,
  getIdempotencyKey,
  readTransferKey,
  writeTransferKey,
  GatewayError,
} from "@/services/api/client";
import type { GatewayAccount, GatewayCard, GatewayTransfer } from "@/services/api/types";

function PageIntro({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="page-intro">
      <div className="min-w-0">
        <p className="eyebrow eyebrow-ink">NandBank · Área do cliente</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action && <div className="page-intro-action">{action}</div>}
    </div>
  );
}

function NetworkMessage({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: unknown;
  retry: () => unknown;
}) {
  if (loading) {
    return <div role="status" className="resource-message"><span className="loading-mark" />A carregar dados do Gateway…</div>;
  }
  if (error) {
    return (
      <section role="alert" className="resource-message resource-message-error">
        <CircleAlert aria-hidden="true" />
        <div><strong>Não foi possível actualizar os dados.</strong><p>{errorMessage(error)}</p></div>
        <Button variant="outline" size="sm" className="min-h-11" onClick={() => void retry()}><RefreshCw aria-hidden="true" /> Tentar novamente</Button>
      </section>
    );
  }
  return null;
}

function EmptyMessage({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-message">
      <span className="empty-message-icon"><CircleHelp aria-hidden="true" /></span>
      <div><h3>{title}</h3><p>{description}</p></div>
    </div>
  );
}

function QuickLink({ to, icon: Icon, label }: { to: "/cliente/transferir" | "/cliente/contas" | "/cliente/cartoes" | "/cliente/movimentos"; icon: typeof Wallet; label: string }) {
  return (
    <Link to={to} className="quick-action">
      <span><Icon aria-hidden="true" /></span><strong>{label}</strong><ArrowRight aria-hidden="true" className="quick-action-arrow" />
    </Link>
  );
}

function transferValue(transfer: GatewayTransfer): string {
  return transfer.amount ?? (transfer.amount_minor != null ? formatMoney(transfer.amount_minor, transfer.source_currency) : "Valor não fornecido");
}

function transferStatus(status: string): string {
  const labels: Record<string, string> = {
    COMMITTED: "Concluída",
    PREPARING: "Em processamento",
    DECISION_COMMIT: "A confirmar",
    DECISION_ABORT: "A cancelar",
    PENDING: "Pendente de confirmação",
    COMMITTING: "A concluir",
    ABORTING: "A reverter",
    ABORTED: "Cancelada",
    NEW: "Recebida",
  };
  return labels[status] ?? status;
}

function TransferRows({ items }: { items: GatewayTransfer[] }) {
  if (items.length === 0) {
    return <EmptyMessage title="Ainda sem movimentos" description="As operações devolvidas pelo Gateway aparecerão aqui." />;
  }
  return (
    <div className="transaction-list">
      {items.slice(0, 5).map((item) => (
        <article key={item.id} className="transaction-row">
          <span className="transaction-icon"><ArrowLeftRight aria-hidden="true" /></span>
          <div className="transaction-main min-w-0"><strong>Transferência entre contas</strong><span>{item.source_region && item.dest_region ? `${regionLabel(item.source_region)} → ${regionLabel(item.dest_region)}` : item.id}</span><small>{formatDate(item.created_at)}</small></div>
          <div className="transaction-value"><strong>{transferValue(item)} {item.source_currency}</strong><span className={item.status === "COMMITTED" ? "status-tag status-tag-good" : "status-tag"}>{transferStatus(item.status)}</span></div>
        </article>
      ))}
    </div>
  );
}

function BalanceTile({ account, hidden }: { account: GatewayAccount; hidden: boolean }) {
  return (
    <article className="balance-tile">
      <div className="flex items-start justify-between gap-3">
        <span className="balance-currency">{account.currency}</span>
        <span className="balance-region">{regionLabel(account.region)}</span>
      </div>
      <h3>{account.branch}</h3>
      <p className="balance-amount">{hidden ? "••••••" : account.balance != null ? formatMoney(account.balance, account.currency) : "Saldo não disponível"}</p>
      <div className="balance-tile-bottom"><span>{account.status ?? "Estado não indicado"}</span><span className="truncate">{account.id}</span></div>
    </article>
  );
}

export function ClientOverviewPage() {
  const profile = useNandQuery(["client-profile"], gateway.me, DEMO_CUSTOMER);
  const transfers = useNandQuery(["client-transfers"], gateway.transfers, DEMO_TRANSFERS);
  const [hidden, setHidden] = useState(false);
  const accounts = profile.data?.accounts ?? [];

  return (
    <DashboardShell mode="customer" title="Visão geral" eyebrow="Área pessoal">
      <div className="page-stack">
        <PageIntro
          title={profile.data ? `Olá, ${profile.data.user.name.split(" ")[0]}.` : "Acompanhe as suas contas."}
          description="Consulte saldos por moeda e acompanhe operações confirmadas pelo Gateway."
          action={<Button variant="outline" onClick={() => { void profile.refetch(); void transfers.refetch(); }}><RefreshCw aria-hidden="true" /> Actualizar</Button>}
        />
        <NetworkMessage loading={profile.isPending} error={profile.error} retry={profile.refetch} />
        <div className="summary-grid">
          <section className="summary-panel summary-panel-dark">
            <div className="summary-panel-top"><span className="eyebrow eyebrow-gold">Contas associadas</span><Button variant="ghost" size="icon" aria-label={hidden ? "Mostrar saldos" : "Ocultar saldos"} onClick={() => setHidden((value) => !value)}>{hidden ? <Eye aria-hidden="true" /> : <EyeOff aria-hidden="true" />}</Button></div>
            {profile.isError ? <p className="summary-unavailable">Entre para consultar dados da sua conta.</p> : accounts.length > 0 ? (
              <div className="summary-total-list">
                {accounts.map((account) => <div key={account.id}><span>{account.currency} · {account.branch}</span><strong>{hidden ? "••••••" : account.balance != null ? formatMoney(account.balance, account.currency) : "Saldo não disponível"}</strong></div>)}
              </div>
            ) : <p className="summary-unavailable">Os saldos serão mostrados depois de o Gateway confirmar as contas.</p>}
          </section>
          <section className="quick-actions-panel">
            <div className="section-title-row"><div><p className="eyebrow eyebrow-ink">Acesso rápido</p><h3>O que precisa de fazer?</h3></div><span className="touch-note">Sempre disponível nesta área</span></div>
            <div className="quick-actions-grid">
              <QuickLink to="/cliente/transferir" icon={ArrowLeftRight} label="Transferir" />
              <QuickLink to="/cliente/contas" icon={Wallet} label="Contas" />
              <QuickLink to="/cliente/cartoes" icon={CreditCard} label="Cartões" />
              <QuickLink to="/cliente/movimentos" icon={History} label="Movimentos" />
            </div>
          </section>
        </div>
        <section className="content-section">
          <div className="section-title-row"><div><p className="eyebrow eyebrow-ink">As minhas contas</p><h3>Por região e moeda</h3><p className="section-subtitle">Os saldos não são somados entre moedas diferentes.</p></div><Button asChild variant="link"><Link to="/cliente/contas">Ver todas <ArrowRight aria-hidden="true" /></Link></Button></div>
          {accounts.length > 0 ? <div className="account-grid">{accounts.map((account) => <BalanceTile key={account.id} account={account} hidden={hidden} />)}</div> : !profile.isPending && !profile.isError ? <EmptyMessage title="Não existem contas disponíveis" description="Quando o Gateway associar contas a este perfil, elas aparecerão aqui." /> : null}
        </section>
        <section className="content-section">
          <div className="section-title-row"><div><p className="eyebrow eyebrow-ink">Actividade recente</p><h3>Movimentos</h3></div><Button asChild variant="link"><Link to="/cliente/movimentos">Ver movimentos <ArrowRight aria-hidden="true" /></Link></Button></div>
          <NetworkMessage loading={transfers.isPending} error={transfers.error} retry={transfers.refetch} />
          {transfers.data && <TransferRows items={transfers.data} />}
        </section>
      </div>
    </DashboardShell>
  );
}

function AccountDetails({ data }: { data: Record<string, unknown> }) {
  const rows = [
    ["Titular", data["owner_name"]],
    ["País", data["country"]],
    ["Região", data["region"]],
    ["Filial", data["branch_name"] ?? data["branch"]],
    ["Moeda", data["currency"]],
    ["Número", data["account_number"]],
    ["NIB", data["nib"]],
    ["IBAN", data["iban"]],
    ["SWIFT/BIC", data["swift_bic"]],
  ].filter((row): row is [string, string] => typeof row[1] === "string" && row[1].length > 0);
  return (
    <div className="details-grid">
      {rows.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      {typeof data["notice"] === "string" && <p className="details-notice">{data["notice"]}</p>}
    </div>
  );
}

export function ClientAccountsPage() {
  const queryClient = useQueryClient();
  const profile = useNandQuery(["client-profile"], gateway.me, DEMO_CUSTOMER);
  const [branch, setBranch] = useState("");
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const details = useMutation({ mutationFn: (id: string) => gateway.accountDetails(id) });
  const create = useMutation({
    mutationFn: () => gateway.createAccount(branch.trim()),
    onSuccess: async (result) => {
      setFormMessage(`Pedido concluído. Referência da conta: ${result.account_id}`);
      setBranch("");
      await queryClient.invalidateQueries({ queryKey: ["client-profile"] });
    },
    onError: (error) => setFormMessage(errorMessage(error)),
  });

  return (
    <DashboardShell mode="customer" title="As minhas contas" eyebrow="Área pessoal">
      <div className="page-stack">
        <PageIntro title="Contas por região." description="Cada conta mantém o seu próprio saldo, moeda e informação devolvida pelo Gateway." />
        <NetworkMessage loading={profile.isPending} error={profile.error} retry={profile.refetch} />
        {profile.data?.accounts.length ? (
          <div className="account-list">
            {profile.data.accounts.map((account) => (
              <article className="account-list-item" key={account.id}>
                <div className="account-list-heading"><span className="account-icon"><Wallet aria-hidden="true" /></span><div className="min-w-0"><h3>{account.branch}</h3><p>{regionLabel(account.region)} · {account.currency}</p></div><span className="status-tag">{account.status ?? "Estado não indicado"}</span></div>
                <div className="account-list-balance"><span>Saldo</span><strong>{account.balance != null ? formatMoney(account.balance, account.currency) : "Não disponível"}</strong></div>
                <div className="account-list-foot"><span className="truncate">{account.id}</span><Button variant="outline" size="sm" onClick={() => { setSelectedAccount(selectedAccount === account.id ? null : account.id); if (selectedAccount !== account.id) details.mutate(account.id); }}><CircleHelp aria-hidden="true" /> Detalhes</Button></div>
                {selectedAccount === account.id && details.data && <AccountDetails data={details.data} />}
                {selectedAccount === account.id && details.error && <p role="alert" className="form-message form-message-error">{errorMessage(details.error)}</p>}
              </article>
            ))}
          </div>
        ) : !profile.isPending && !profile.isError ? <EmptyMessage title="Não existem contas associadas" description="A lista será actualizada quando o Gateway devolver contas para o seu perfil." /> : null}
        <section className="form-section">
          <div className="form-section-heading"><span className="form-section-icon"><Building2 aria-hidden="true" /></span><div><p className="eyebrow eyebrow-ink">Nova conta</p><h3>Pedir uma conta adicional</h3><p>O Gateway valida a filial e atribui a moeda configurada.</p></div></div>
          <form className="inline-form" onSubmit={(event) => { event.preventDefault(); setFormMessage(null); create.mutate(); }}>
            <label className="form-field"><span>Filial</span><Input value={branch} onChange={(event) => setBranch(event.target.value)} required placeholder="Código de filial aceite pelo Gateway" /></label>
            <Button type="submit" disabled={create.isPending || !branch.trim() || DEMO_MODE}>{create.isPending ? "A enviar…" : "Pedir conta"}<ArrowRight aria-hidden="true" /></Button>
          </form>
          {formMessage && <p role={create.isError ? "alert" : "status"} className={create.isError ? "form-message form-message-error" : "form-message form-message-success"}>{formMessage}</p>}
          {DEMO_MODE && <p className="field-note">Na demonstração, os pedidos que alterariam dados reais ficam desactivados.</p>}
        </section>
      </div>
    </DashboardShell>
  );
}

function DemoLookup(accountId: string) {
  if (accountId === "NB-DEMO-EU-002") {
    return { account_id: accountId, beneficiary: "Utilizador de demonstração", region: "EU", branch: "Lisboa", currency: "EUR" };
  }
  if (accountId === "NB-DEMO-AF-001") {
    return { account_id: accountId, beneficiary: "Utilizador de demonstração", region: "AF", branch: "Maputo", currency: "MZN" };
  }
  throw new GatewayError(404, "Conta de demonstração não encontrada.");
}

export function ClientTransferPage() {
  const queryClient = useQueryClient();
  const profile = useNandQuery(["client-profile"], gateway.me, DEMO_CUSTOMER);
  const [sourceId, setSourceId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [pendingTransfer, setPendingTransfer] = useState<PendingTransfer | null>(null);
  const [lastTransferStatus, setLastTransferStatus] = useState<string | null>(null);
  useEffect(() => { setPendingTransfer(readPendingTransfer()); }, []);
  useEffect(() => {
    if (!pendingTransfer || !profile.data?.user.id) return;
    if (!pendingTransfer.fingerprint.startsWith(`${profile.data.user.id}|`)) {
      writePendingTransfer(null);
      writeTransferKey(null);
      setPendingTransfer(null);
    }
  }, [pendingTransfer, profile.data?.user.id]);
  const statusCheck = useQuery({
    queryKey: ["transfer-final-status", pendingTransfer?.id],
    queryFn: () => gateway.transferStatus(pendingTransfer!.id),
    enabled: Boolean(pendingTransfer?.id) && !DEMO_MODE,
    refetchInterval: 3_000,
    retry: false,
  });
  useEffect(() => {
    const state = statusCheck.data?.status;
    if (!state) return;
    setLastTransferStatus(state);
    setResultMessage(transferStateMessage(state));
    if (isTransferTerminal(state)) {
      setPendingTransfer(null);
      writePendingTransfer(null);
      idempotency.current = null;
      writeTransferKey(null);
      void queryClient.invalidateQueries({ queryKey: ["client-profile"] });
      void queryClient.invalidateQueries({ queryKey: ["client-transfers"] });
    }
  }, [statusCheck.data?.status, queryClient]);
  const source = profile.data?.accounts.find((account) => account.id === sourceId);
  const normalAmount = amount.trim().replace(/\s/g, "").replace(",", ".");
  const parsedAmount = Number(normalAmount);
  const lookup = useQuery({
    queryKey: ["account-lookup", destinationId, DEMO_MODE ? "demo" : "live"],
    queryFn: () => DEMO_MODE ? Promise.resolve(DemoLookup(destinationId)) : gateway.lookupAccount(destinationId),
    enabled: typeof window !== "undefined" && Boolean(destinationId.trim()),
    retry: false,
  });
  const quote = useQuery({
    queryKey: ["transfer-quote", source?.currency, lookup.data?.currency, normalAmount, DEMO_MODE ? "demo" : "live"],
    queryFn: () => DEMO_MODE
      ? Promise.resolve({ source_currency: "MZN", destination_currency: "EUR", amount_minor: Math.round(parsedAmount * 100), fee_minor: 250, total_debit_minor: Math.round(parsedAmount * 100) + 250, credit_minor: Math.max(0, Math.round(parsedAmount * 0.006 * 100)), rate: "0.00600000", source_amount: parsedAmount.toFixed(2), fee: "2.50", total_debit: (parsedAmount + 2.5).toFixed(2), recipient_amount: (parsedAmount * 0.006).toFixed(2), fx_source: "DEMO", updated_at: "2026-11-20T10:30:00Z", notice: DEMO_NOTICE })
      : gateway.quote(source?.currency ?? "", lookup.data?.currency ?? "", normalAmount),
    enabled: typeof window !== "undefined" && Boolean(source && lookup.data && Number.isFinite(parsedAmount) && parsedAmount > 0),
    retry: false,
  });
  const fingerprint = `${profile.data?.user.id ?? "NO_PROFILE"}|${sourceId}|${destinationId.trim()}|${normalAmount}|${note.trim()}`;
  const idempotency = useRef<{ fingerprint: string; key: string } | null>(null);
  const transfer = useMutation({
    mutationFn: () => {
      if (!sourceId || !destinationId || !normalAmount || !quote.data) throw new Error("Preencha os dados e confirme a cotação antes de continuar.");
      if (DEMO_MODE) return Promise.resolve({ id: "DEMO-TX-NEW", status: "PREPARING" });
      idempotency.current = getIdempotencyKey(idempotency.current ?? readTransferKey(), fingerprint);
      writeTransferKey(idempotency.current);
      const idempotencyKey = idempotency.current.key;
      return gateway.transfer({ source_id: sourceId, destination_id: destinationId.trim(), amount: normalAmount, idempotency_key: idempotencyKey, note: note.trim() });
    },
    onSuccess: async (result) => {
      const status = result.status ?? "PENDING";
      setLastTransferStatus(status);
      setResultMessage(DEMO_MODE ? "Simulação concluída — nenhuma transferência foi enviada ao Gateway." : transferStateMessage(status));
      if (DEMO_MODE || isTransferTerminal(status)) {
        idempotency.current = null;
        writeTransferKey(null);
        writePendingTransfer(null);
        setPendingTransfer(null);
      } else if (result.id) {
        const next = { id: result.id, fingerprint, status };
        setPendingTransfer(next);
        writePendingTransfer(next);
      } else {
        setResultMessage("O servidor aceitou o pedido sem referência. NÃO repita com outra chave. Consulte os movimentos ou contacte o gestor.");
      }
      await queryClient.invalidateQueries({ queryKey: ["client-transfers"] });
      if (isTransferTerminal(status)) await queryClient.invalidateQueries({ queryKey: ["client-profile"] });
    },
    onError: (error) => setResultMessage(`${errorMessage(error)} Se o pedido já tiver chegado ao Gateway, volte a enviá-lo somente com os mesmos dados: a chave de idempotência será reutilizada.`),
  });

  const quoteRows = useMemo(() => {
    if (!quote.data || !source || !lookup.data) return [];
    return [
      ["A debitar", `${quote.data.total_debit} ${source.currency}`],
      ["Comissão", `${quote.data.fee} ${source.currency}`],
      ["A receber", `${quote.data.recipient_amount} ${lookup.data.currency}`],
      ["Taxa de câmbio", quote.data.rate],
    ];
  }, [lookup.data, quote.data, source]);

  return (
    <DashboardShell mode="customer" title="Transferir" eyebrow="Operações">
      <div className="page-stack">
        <PageIntro title="Transferir entre contas." description="Confirme os dados do destinatário e a cotação actual antes de enviar o pedido." />
        <NetworkMessage loading={profile.isPending} error={profile.error} retry={profile.refetch} />
        <div className="transfer-layout">
          <form className="form-section transfer-form" onSubmit={(event) => { event.preventDefault(); if (!pendingTransfer) setConfirmationOpen(true); }}>
            <div className="form-section-heading"><span className="form-section-icon"><ArrowLeftRight aria-hidden="true" /></span><div><p className="eyebrow eyebrow-ink">Nova operação</p><h3>Dados da transferência</h3></div></div>
            <label className="form-field"><span>Conta de origem</span>
              <Select value={sourceId} onValueChange={setSourceId} disabled={Boolean(pendingTransfer) || transfer.isPending}>
                <SelectTrigger aria-label="Seleccionar conta de origem"><SelectValue placeholder="Escolha uma conta" /></SelectTrigger>
                <SelectContent>{(profile.data?.accounts ?? []).map((account) => <SelectItem value={account.id} key={account.id}>{account.branch} · {account.currency} · {account.id}</SelectItem>)}</SelectContent>
              </Select>
            </label>
            <label className="form-field"><span>Conta de destino</span><Input value={destinationId} onChange={(event) => setDestinationId(event.target.value)} disabled={Boolean(pendingTransfer) || transfer.isPending} required autoComplete="off" placeholder="Introduza o identificador da conta" /></label>
            {lookup.data && <div className="beneficiary-confirmation"><BadgeCheck aria-hidden="true" /><div><strong>{lookup.data.beneficiary}</strong><span>{lookup.data.branch} · {regionLabel(lookup.data.region)} · {lookup.data.currency}</span></div></div>}
            {lookup.isError && destinationId.trim() && <p role="alert" className="form-message form-message-error">{errorMessage(lookup.error)}</p>}
            <label className="form-field"><span>Montante</span><div className="amount-input-wrap"><Input inputMode="decimal" type="text" value={amount} onChange={(event) => setAmount(event.target.value)} disabled={Boolean(pendingTransfer) || transfer.isPending} required placeholder="0,00" /><span>{source?.currency ?? "Moeda da conta"}</span></div></label>
            <label className="form-field"><span>Nota <small className="inline-note">(opcional)</small></span><Input value={note} onChange={(event) => setNote(event.target.value)} disabled={Boolean(pendingTransfer) || transfer.isPending} maxLength={400} placeholder="Referência para esta operação" /></label>
            <Button type="submit" size="lg" className="min-h-12 w-full" disabled={transfer.isPending || Boolean(pendingTransfer) || !source || !lookup.data || !quote.data || !Number.isFinite(parsedAmount) || parsedAmount <= 0}>
              {pendingTransfer ? "A aguardar confirmação 2PC…" : transfer.isPending ? "A enviar pedido…" : DEMO_MODE ? "Simular transferência" : "Rever e confirmar"}<ArrowRight aria-hidden="true" />
            </Button>
            {pendingTransfer && <section role="status" className="transfer-pending-notice"><span className="loading-mark"/><div><strong>Operação #{pendingTransfer.id.slice(0, 8)} a ser concluída</strong><p>Aguardamos o estado definitivo do servidor. Não envie outro pedido enquanto estiver pendente.</p>{statusCheck.isError && <p role="alert">{errorMessage(statusCheck.error)} <Button type="button" variant="outline" size="sm" onClick={() => void statusCheck.refetch()}>Consultar novamente</Button></p>}</div></section>}
            {resultMessage && <p role={transfer.isError || lastTransferStatus === "ABORTED" ? "alert" : "status"} className={transfer.isError || lastTransferStatus === "ABORTED" ? "form-message form-message-error" : "form-message form-message-success"}>{resultMessage}</p>}
            <AlertDialog open={confirmationOpen} onOpenChange={setConfirmationOpen}>
              <AlertDialogContent>
                <AlertDialogHeader><AlertDialogTitle>Confirmar transferência</AlertDialogTitle><AlertDialogDescription>Verifique os dados bancários e a cotação antes de autorizar a operação. O resultado final poderá ficar pendente de confirmação 2PC.</AlertDialogDescription></AlertDialogHeader>
                <dl className="transfer-confirmation-list"><div><dt>Origem</dt><dd>{source?.branch} · {source?.currency}</dd></div><div><dt>Destinatário</dt><dd>{lookup.data?.beneficiary ?? "A validar"}</dd></div><div><dt>Conta de destino</dt><dd>{destinationId}</dd></div>{quoteRows.map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
                <AlertDialogFooter><AlertDialogCancel>Rever dados</AlertDialogCancel><AlertDialogAction onClick={() => { setResultMessage(null); setLastTransferStatus(null); transfer.mutate(); }}>Autorizar pedido</AlertDialogAction></AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            {DEMO_MODE && <p className="field-note">{DEMO_NOTICE}. Nenhuma operação é enviada ao Gateway.</p>}
          </form>
          <aside className="quote-panel">
            <p className="eyebrow eyebrow-gold">Antes de confirmar</p><h3>Resumo da operação</h3>
            {quote.isPending && source && lookup.data && <div role="status" className="resource-message"><span className="loading-mark" />A obter cotação…</div>}
            {quote.isError && <p role="alert" className="form-message form-message-error">{errorMessage(quote.error)}</p>}
            {quoteRows.length ? <dl className="quote-list">{quoteRows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <div className="quote-empty"><Globe2 aria-hidden="true" /><p>A cotação só aparece depois de o Gateway validar a origem, o destino e o montante.</p></div>}
            <div className="quote-footnote"><LockKeyhole aria-hidden="true" /><span>A confirmação final depende da resposta do servidor.</span></div>
          </aside>
        </div>
      </div>
    </DashboardShell>
  );
}

export function ClientMovementsPage() {
  const transfers = useNandQuery(["client-transfers"], gateway.transfers, DEMO_TRANSFERS);
  const [statusFilter, setStatusFilter] = useState("all");
  const [receiptId, setReceiptId] = useState<string | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const filtered = (transfers.data ?? []).filter((item) => statusFilter === "all" || item.status === statusFilter);
  const statuses = Array.from(new Set((transfers.data ?? []).map((item) => item.status)));

  async function downloadReceipt(id: string) {
    setReceiptId(id);
    setReceiptError(null);
    try {
      const file = await gateway.receipt(id);
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "nandbank-comprovativo-academico.pdf";
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (error) {
      setReceiptError(errorMessage(error));
    } finally {
      setReceiptId(null);
    }
  }

  return (
    <DashboardShell mode="customer" title="Movimentos" eyebrow="Histórico">
      <div className="page-stack">
        <PageIntro title="Movimentos da conta." description="Histórico devolvido pelo Gateway, sem dados de exemplo no modo normal." action={<Button variant="outline" onClick={() => void transfers.refetch()}><RefreshCw aria-hidden="true" /> Actualizar</Button>} />
        <NetworkMessage loading={transfers.isPending} error={transfers.error} retry={transfers.refetch} />
        <section className="content-section">
          <div className="filter-row"><div><p className="eyebrow eyebrow-ink">Transferências</p><h3>Registos disponíveis</h3></div><label className="filter-control"><span>Estado</span><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger aria-label="Filtrar por estado"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Todos</SelectItem>{statuses.map((status) => <SelectItem key={status} value={status}>{transferStatus(status)}</SelectItem>)}</SelectContent></Select></label></div>
          {receiptError && <p role="alert" className="form-message form-message-error">{receiptError}</p>}
          {filtered.length ? <div className="movement-table-wrap"><table className="movement-table"><thead><tr><th scope="col">Operação</th><th scope="col">Referência</th><th scope="col">Data</th><th scope="col">Montante</th><th scope="col">Estado</th><th scope="col">Comprovativo</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td>Transferência</td><td className="table-id">{item.id}</td><td>{formatDate(item.created_at)}</td><td>{transferValue(item)} {item.source_currency}</td><td><span className={item.status === "COMMITTED" ? "status-tag status-tag-good" : "status-tag"}>{transferStatus(item.status)}</span></td><td>{!DEMO_MODE && item.status === "COMMITTED" ? <Button variant="outline" size="sm" disabled={receiptId === item.id} onClick={() => void downloadReceipt(item.id)}><Download aria-hidden="true" />{receiptId === item.id ? "A preparar…" : "PDF"}</Button> : "—"}</td></tr>)}</tbody></table></div> : !transfers.isPending && !transfers.isError ? <EmptyMessage title="Nenhum movimento encontrado" description="Os registos e filtros dependem do histórico devolvido pelo Gateway." /> : null}
        </section>
      </div>
    </DashboardShell>
  );
}

function VirtualCardVisual({ card }: { card?: GatewayCard }) {
  const [flipped, setFlipped] = useState(false);
  const frozen = card?.status === "FROZEN";
  return (
    <div className="virtual-card-shell">
      <button type="button" className="virtual-card-flip-trigger" aria-label={flipped ? "Mostrar frente do cartão académico" : "Virar cartão académico para consultar informações"} aria-pressed={flipped} onClick={() => setFlipped(v => !v)}>
        <span className={`virtual-card-rotator${flipped ? " is-flipped" : ""}${frozen ? " is-frozen" : ""}`}>
          <span className="academic-card-visual virtual-card-face virtual-card-front" aria-hidden={flipped}>
            <span className="card-sheen" aria-hidden="true" />
            <span className="academic-card-top"><span className="card-brand-lockup"><BrandMark compact /><strong>NandBank</strong></span><span className="academic-card-type">CARTÃO DIGITAL<br/>ACADÉMICO</span></span>
            <span className="virtual-card-chip-row"><svg className="virtual-card-chip" viewBox="0 0 68 50" fill="none" aria-hidden="true"><rect x="1" y="1" width="66" height="48" rx="9" fill="#D3B77A" stroke="#F3E1B1" strokeWidth="2"/><path d="M22 1v48M46 1v48M1 18h66M1 33h66M22 18c10 2 14 14 0 15M46 18c-10 2-14 14 0 15" stroke="#907044" strokeWidth="1.6"/></svg><Wifi aria-hidden="true" className="virtual-card-contactless" /></span>
            <span className="academic-card-number">{card?.last4 ? `••••  ••••  ••••  ${card.last4}` : "••••  ••••  ••••  ————"}</span>
            <span className="academic-card-bottom"><span><small>TITULAR</small><strong>{card?.holder_name ?? "Titular não indicado"}</strong></span><span className="virtual-card-currency">{card?.currency ?? "—"}</span></span>
            <span className="card-status-mark">{frozen ? "CONGELADO" : card?.status ?? "SEM CARTÃO"}</span>
          </span>
          <span className="virtual-card-face virtual-card-back" aria-hidden={!flipped}>
            <span className="virtual-card-back-band" />
            <span className="virtual-card-back-content"><span className="card-brand-lockup"><BrandMark compact /><strong>NandBank</strong></span><span>Cartão académico protegido</span><span className="virtual-card-back-description">Não são disponibilizados número completo, CVV nem dados de pagamento. Apenas informação autorizada pelo Gateway.</span><strong>Estado: {card?.status ?? "Sem cartão"}</strong></span>
          </span>
        </span>
      </button>
      <div className="virtual-card-flip-hint"><RotateCcw size={16} aria-hidden="true" /><span>{flipped ? "Toque para voltar à frente" : "Toque para virar o cartão"}</span></div>
    </div>
  );
}

export function ClientCardsPage() {
  const queryClient = useQueryClient();
  const profile = useNandQuery(["client-profile"], gateway.me, DEMO_CUSTOMER);
  const cards = useNandQuery(["client-cards"], gateway.cards, DEMO_CARDS);
  const [accountId, setAccountId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const request = useMutation({
    mutationFn: () => gateway.requestCard(accountId),
    onSuccess: async (result) => {
      setMessage(result.message);
      await queryClient.invalidateQueries({ queryKey: ["client-cards"] });
    },
    onError: (error) => setMessage(errorMessage(error)),
  });
  const toggle = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "freeze" | "unfreeze" }) => gateway.setCardState(id, action),
    onSuccess: async (result) => {
      setMessage(`Estado actualizado pelo Gateway: ${result.status}.`);
      await queryClient.invalidateQueries({ queryKey: ["client-cards"] });
    },
    onError: (error) => setMessage(errorMessage(error)),
  });

  return (
    <DashboardShell mode="customer" title="Cartões digitais" eyebrow="Serviços académicos">
      <div className="page-stack">
        <PageIntro title="Cartões virtuais académicos." description="Apenas dados devolvidos pelo Gateway são apresentados. Não são cartões de pagamento reais." />
        <NetworkMessage loading={cards.isPending} error={cards.error} retry={cards.refetch} />
        {cards.data?.length ? <div className="card-gallery">{cards.data.map((card) => <article className="card-record" key={card.id}><VirtualCardVisual card={card} /><div className="card-record-details"><span className="eyebrow eyebrow-ink">{card.status}</span><h3>Cartão associado à conta</h3><p>{card.branch ?? "Filial não indicada"} · {card.currency ?? "Moeda não indicada"}</p>{card.id && <small>Referência: {card.id}</small>}{card.status === "ACTIVE" || card.status === "FROZEN" ? <Button variant={card.status === "FROZEN" ? "default" : "outline"} disabled={toggle.isPending || DEMO_MODE} onClick={() => toggle.mutate({ id: card.id, action: card.status === "FROZEN" ? "unfreeze" : "freeze" })}>{card.status === "FROZEN" ? "Descongelar cartão" : "Congelar cartão"}</Button> : null}</div></article>)}</div> : !cards.isPending && !cards.isError ? <div className="card-empty-state"><VirtualCardVisual /><div><p className="eyebrow eyebrow-ink">Sem cartão associado</p><h3>Peça um cartão académico.</h3><p>O pedido fica sujeito à revisão de um gerente regional.</p></div></div> : null}
        <section className="form-section">
          <div className="form-section-heading"><span className="form-section-icon"><CreditCard aria-hidden="true" /></span><div><p className="eyebrow eyebrow-ink">Pedido</p><h3>Solicitar cartão virtual</h3><p>Escolha uma conta elegível devolvida pelo Gateway.</p></div></div>
          {profile.data?.accounts.length ? <form className="inline-form" onSubmit={(event) => { event.preventDefault(); setMessage(null); request.mutate(); }}><label className="form-field"><span>Conta</span><Select value={accountId} onValueChange={setAccountId}><SelectTrigger aria-label="Seleccionar conta"><SelectValue placeholder="Escolha uma conta" /></SelectTrigger><SelectContent>{profile.data.accounts.map((account) => <SelectItem key={account.id} value={account.id}>{account.branch} · {account.currency} · {account.id}</SelectItem>)}</SelectContent></Select></label><Button type="submit" disabled={!accountId || request.isPending || DEMO_MODE}>{request.isPending ? "A enviar…" : "Pedir cartão"}<ArrowRight aria-hidden="true" /></Button></form> : <p className="field-note">As contas disponíveis só aparecem após resposta válida do Gateway.</p>}
          {message && <p role={request.isError || toggle.isError ? "alert" : "status"} className={request.isError || toggle.isError ? "form-message form-message-error" : "form-message form-message-success"}>{message}</p>}
          {DEMO_MODE && <p className="field-note">Na demonstração, o pedido e o bloqueio não enviam alterações ao servidor.</p>}
        </section>
        <div className="security-footnote"><ShieldCheck aria-hidden="true" /><span>Nunca é apresentado CVV ou número completo.</span></div>
      </div>
    </DashboardShell>
  );
}

const supportedServices = [
  { title: "Contas", text: "Consultar contas e detalhes autorizados.", to: "/cliente/contas" as const, icon: Wallet },
  { title: "Transferências", text: "Obter cotação e submeter transferências suportadas.", to: "/cliente/transferir" as const, icon: ArrowLeftRight },
  { title: "Cartões académicos", text: "Solicitar ou gerir cartões devolvidos pelo Gateway.", to: "/cliente/cartoes" as const, icon: CreditCard },
  { title: "Movimentos", text: "Consultar o histórico real de operações.", to: "/cliente/movimentos" as const, icon: History },
];

export function ClientServicesPage() {
  return (
    <DashboardShell mode="customer" title="Serviços" eyebrow="Área pessoal">
      <div className="page-stack">
        <PageIntro title="Serviços suportados." description="Apenas operações existentes no Gateway aparecem como acções disponíveis." />
        <div className="service-list">{supportedServices.map((service, index) => { const Icon = service.icon; return <Link to={service.to} className="service-row" key={service.title}><span className="service-number">0{index + 1}</span><span className="service-icon"><Icon aria-hidden="true" /></span><div className="min-w-0"><h3>{service.title}</h3><p>{service.text}</p></div><ArrowRight aria-hidden="true" /></Link>; })}</div>
        <div className="academic-note-panel"><Landmark aria-hidden="true" /><div><h3>Serviços não disponíveis nesta versão</h3><p>Investimentos, pagamentos de serviços e recargas não são apresentados como operações porque não constam dos contratos fornecidos.</p></div></div>
      </div>
    </DashboardShell>
  );
}

export function ClientSystemPage() {
  const regions = [["AF", "África"], ["EU", "Europa"], ["AS", "Ásia"], ["NA", "América do Norte"], ["SA", "América do Sul"], ["OC", "Oceânia"]];
  return (
    <DashboardShell mode="customer" title="Sobre o sistema" eyebrow="Informação">
      <div className="page-stack">
        <PageIntro title="Uma rede académica distribuída." description="O NandBank demonstra uma experiência digital para um sistema bancário distribuído, sem representar serviços financeiros reais." />
        <section className="system-overview">
          <div><p className="eyebrow eyebrow-gold">Arquitectura do projecto</p><h3>Operações supervisionadas pelo Gateway.</h3><p>As contas, as cotações, os cartões e as operações aparecem apenas quando o servidor devolve informação autorizada. O agente de nós permanece no computador Windows e nunca é controlado directamente pelo navegador.</p></div>
          <div className="system-stamp"><Globe2 aria-hidden="true" /><span>6</span><small>regiões</small></div>
        </section>
        <div className="region-list">{regions.map(([code, name]) => <div key={code}><span>{code}</span><strong>{name}</strong></div>)}</div>
        <div className="security-footnote"><ShieldCheck aria-hidden="true" /><span>Protótipo académico · dinheiro fictício · sem ligação a bancos reais.</span></div>
      </div>
    </DashboardShell>
  );
}