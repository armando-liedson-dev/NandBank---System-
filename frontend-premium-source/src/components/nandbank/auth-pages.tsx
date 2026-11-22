import { useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BrandLogo } from "@/components/nandbank/brand";
import { errorMessage } from "@/lib/nandbank/query";
import { isValidRegistrationPassword } from "@/lib/nandbank/validation";
import { clearAccessToken, DEMO_MODE, gateway, roleHome, saveAccessToken } from "@/services/api/client";

function AuthLayout({
  children,
  title,
  intro,
}: {
  children: ReactNode;
  title: string;
  intro: string;
}) {
  return (
    <main className="auth-layout">
      <aside className="auth-brand-panel">
        <BrandLogo />
        <div className="auth-brand-copy">
          <p className="eyebrow eyebrow-gold">NandBank · projecto académico</p>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
        <div className="auth-assurance"><ShieldCheck aria-hidden="true" /><span>As operações e permissões são validadas pelo Gateway existente.</span></div>
        <Link to="/" className="auth-back-link"><ArrowLeft aria-hidden="true" /> Voltar à página inicial</Link>
      </aside>
      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <BrandLogo compact tone="light" />
          {children}
        </div>
      </section>
    </main>
  );
}

function DemoLinks() {
  if (!DEMO_MODE) return null;
  return (
    <div className="demo-choice-list">
      <p className="demo-banner-inline">Pré-visualização de interface — dados fictícios</p>
      <Link to="/cliente/visao-geral">Abrir área do cliente <ArrowRight aria-hidden="true" /></Link>
      <Link to="/gerente/visao-geral">Abrir painel regional <ArrowRight aria-hidden="true" /></Link>
      <Link to="/gerente-global/visao-geral">Abrir painel global <ArrowRight aria-hidden="true" /></Link>
    </div>
  );
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: async () => {
      const result = await gateway.login(email.trim(), password);
      saveAccessToken(result.access_token);
      return gateway.me();
    },
    onSuccess: async (profile) => {
      queryClient.clear();
      const destination = roleHome(profile.user.role);
      if (!destination) {
        clearAccessToken();
        setFormError("Este perfil ainda não tem uma área disponível nesta interface.");
        return;
      }
          await navigate({ to: destination });
    },
    onError: (error) => {
      clearAccessToken();
      setFormError(errorMessage(error));
    },
  });

  return (
    <AuthLayout title="Bem-vindo de volta." intro="Entre na sua área para consultar a informação devolvida pelo Gateway NandBank.">
      <div className="auth-title-block">
        <p className="eyebrow eyebrow-ink">Acesso seguro</p>
        <h2>Entrar na sua conta</h2>
        <p>Use o endereço de email associado ao seu perfil.</p>
      </div>
      {DEMO_MODE ? <DemoLinks /> : (
        <form className="auth-form" onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          mutation.mutate();
        }}>
          <label className="form-field">
            <span>Email</span>
            <Input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nome@exemplo.com" />
          </label>
          <label className="form-field">
            <span>Palavra-passe</span>
            <div className="password-input-wrap">
              <Input type={showPassword ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
              <Button type="button" variant="ghost" size="icon" aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"} onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
          </label>
          {formError && <p role="alert" className="form-message form-message-error">{formError}</p>}
          <Button type="submit" size="lg" className="min-h-12 w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "A validar acesso…" : "Entrar"} <ArrowRight aria-hidden="true" />
          </Button>
          <p className="auth-switch-copy">Ainda não tem acesso? <Link to="/criar-conta">Criar conta</Link></p>
        </form>
      )}
      <p className="auth-academic-note">Protótipo académico. Não utilize credenciais bancárias reais.</p>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [branch, setBranch] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => gateway.register({ name: name.trim(), email: email.trim(), password, branch: branch.trim() }),
    onSuccess: (result) => {
      setSuccessMessage(result.message || "Conta criada. Entre para iniciar sessão.");
      setPassword("");
    },
    onError: (error) => setFormError(errorMessage(error)),
  });

  return (
    <AuthLayout title="Uma experiência, várias regiões." intro="O acesso é criado pelo Gateway e associado a uma filial suportada pelo sistema académico.">
      <div className="auth-title-block">
        <p className="eyebrow eyebrow-ink">Novo acesso</p>
        <h2>Criar conta</h2>
        <p>Preencha os dados pedidos pelo sistema académico.</p>
      </div>
      {DEMO_MODE ? <DemoLinks /> : (
        <form className="auth-form" onSubmit={(event) => {
          event.preventDefault();
          setSuccessMessage(null);
          setFormError(null);
          if (!isValidRegistrationPassword(password)) {
            setFormError("Use pelo menos 12 caracteres, com maiúscula, minúscula e número.");
            return;
          }
          mutation.mutate();
        }}>
          <label className="form-field">
            <span>Nome completo</span>
            <Input autoComplete="name" minLength={3} maxLength={120} required value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="form-field">
            <span>Email</span>
            <Input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nome@exemplo.com" />
          </label>
          <label className="form-field">
            <span>Filial</span>
            <Input required value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="Código da filial fornecido pelo Gateway" />
            <small>A filial é validada pelo servidor; a moeda é atribuída segundo a configuração regional.</small>
          </label>
          <label className="form-field">
            <span>Palavra-passe</span>
            <div className="password-input-wrap">
              <Input
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                minLength={12}
                maxLength={200}
                pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).{12,}"
                title="Use pelo menos 12 caracteres, com maiúscula, minúscula e número."
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <Button type="button" variant="ghost" size="icon" aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"} onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
            <small>Mínimo de 12 caracteres, com maiúscula, minúscula e número.</small>
          </label>
          {formError && <p role="alert" className="form-message form-message-error">{formError}</p>}
          {successMessage && <p role="status" className="form-message form-message-success">{successMessage}</p>}
          <Button type="submit" size="lg" className="min-h-12 w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "A criar conta…" : "Criar conta"} <ArrowRight aria-hidden="true" />
          </Button>
          <p className="auth-switch-copy">Já tem acesso? <Link to="/entrar">Entrar</Link></p>
        </form>
      )}
      <p className="auth-academic-note">O NandBank é um protótipo académico e não cria contas em instituições reais.</p>
    </AuthLayout>
  );
}