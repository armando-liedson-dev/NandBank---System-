CREATE TABLE IF NOT EXISTS accounts(
    id text PRIMARY KEY,owner_id text NOT NULL,branch text NOT NULL,
    currency text NOT NULL,balance_minor bigint NOT NULL DEFAULT 0 CHECK(balance_minor>=0),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_accounts_owner ON accounts(owner_id);
CREATE TABLE IF NOT EXISTS ledger(
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id text NOT NULL,account_id text NOT NULL REFERENCES accounts(id),
    kind text NOT NULL,delta_minor bigint NOT NULL,
    currency text NOT NULL,details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(operation_id,account_id)
);
CREATE INDEX IF NOT EXISTS idx_ledger_account ON ledger(account_id,created_at DESC);
