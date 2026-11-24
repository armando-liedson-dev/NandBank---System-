CREATE TABLE IF NOT EXISTS users(
  id text PRIMARY KEY, email text UNIQUE NOT NULL, name text NOT NULL,
  password_hash text NOT NULL,
  role text NOT NULL CHECK(role IN ('client','teller','branch_manager','regional_manager','global_manager')),
  region text, branch text, created_at timestamptz DEFAULT now(),
  status text NOT NULL DEFAULT 'ACTIVE',status_reason text NOT NULL DEFAULT '',
  status_changed_at timestamptz,status_changed_by text
);
CREATE TABLE IF NOT EXISTS account_registry(
  id text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id),
  region text NOT NULL, branch text NOT NULL, currency text NOT NULL,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_registry_owner ON account_registry(user_id);
CREATE TABLE IF NOT EXISTS fx_rates(
  currency text PRIMARY KEY, units_per_eur numeric(25,10) NOT NULL CHECK(units_per_eur>0),
  source text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO fx_rates(currency,units_per_eur,source) VALUES
 ('EUR',1,'DEMO'),('MZN',70.11,'DEMO'),('USD',1.10,'DEMO'),('CNY',7.90,'DEMO'),('ZAR',20,'DEMO'),('GHS',13.50,'DEMO')
 ON CONFLICT (currency) DO NOTHING;
CREATE TABLE IF NOT EXISTS transfers(
  id text PRIMARY KEY, actor_id text NOT NULL,
  request_key text NOT NULL, source_id text NOT NULL, destination_id text NOT NULL,
  source_region text NOT NULL, dest_region text NOT NULL,
  source_currency text NOT NULL, dest_currency text NOT NULL,
  amount_minor bigint NOT NULL,fee_minor bigint NOT NULL,credit_minor bigint NOT NULL,
  rate_text text NOT NULL, status text NOT NULL,
  note text NOT NULL DEFAULT '', last_error text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(),
  UNIQUE(actor_id,request_key)
);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON transfers(status);
CREATE TABLE IF NOT EXISTS operation_registry(
  id text PRIMARY KEY, actor_id text NOT NULL, account_id text NOT NULL,
  operation_type text NOT NULL, amount_minor bigint NOT NULL,
  deposit_currency text NOT NULL, credited_minor bigint NOT NULL,
  account_currency text NOT NULL, rate_text text NOT NULL,
  status text NOT NULL, created_at timestamptz DEFAULT now(),
  UNIQUE(actor_id,id)
);
CREATE TABLE IF NOT EXISTS audit_events(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id text, type text NOT NULL, details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- NandBank; também criadas automaticamente na inicialização para volumes existentes.
CREATE TABLE IF NOT EXISTS virtual_cards (id text PRIMARY KEY,account_id text NOT NULL REFERENCES account_registry(id),user_id text NOT NULL REFERENCES users(id),region text NOT NULL,last4 text NOT NULL,status text NOT NULL DEFAULT 'REQUESTED' CHECK(status IN ('REQUESTED','ACTIVE','FROZEN','REJECTED','CANCELLED')),created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now(),reviewed_by text,reviewed_at timestamptz);
CREATE INDEX IF NOT EXISTS ix_cards_user ON virtual_cards(user_id);
CREATE TABLE IF NOT EXISTS node_control_jobs (id text PRIMARY KEY, region text NOT NULL,action text NOT NULL CHECK(action IN ('STOP_PRIMARY','START_PRIMARY')),reason text NOT NULL,note text NOT NULL DEFAULT '',actor_id text NOT NULL REFERENCES users(id),status text NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','RUNNING','COMPLETED','FAILED')),result text NOT NULL DEFAULT '',created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_node_jobs_status ON node_control_jobs(status,created_at);
