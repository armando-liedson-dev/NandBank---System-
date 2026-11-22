export type GatewayRole =
  | "client"
  | "regional_manager"
  | "global_manager"
  | "branch_manager"
  | "teller";

export interface GatewayUser {
  id: string;
  name: string;
  email: string;
  role: GatewayRole;
  region?: string | null;
  branch?: string | null;
}

export interface GatewayAccount {
  id: string;
  region: string;
  branch: string;
  currency: string;
  balance?: string | null;
  balance_minor?: number | null;
  status?: string;
}

export interface GatewayMe {
  user: GatewayUser;
  accounts: GatewayAccount[];
}

export interface GatewayConfig {
  name?: string;
  currencies?: string[];
  regions?: unknown;
  notice?: string;
}

export interface LoginResult {
  access_token: string;
  token_type: "bearer" | string;
  role: GatewayRole;
  name: string;
}

export interface GatewayTransfer {
  id: string;
  source_id: string;
  destination_id: string;
  source_region?: string;
  dest_region?: string;
  source_currency: string;
  dest_currency: string;
  amount_minor?: number;
  amount?: string;
  fee_minor?: number;
  fee?: string;
  credit_minor?: number;
  credited?: string;
  status: string;
  created_at?: string;
  rate_text?: string;
}

export interface GatewayCard {
  id: string;
  status: "REQUESTED" | "ACTIVE" | "FROZEN" | "REJECTED" | string;
  last4?: string | null;
  holder_name?: string | null;
  currency?: string;
  branch?: string;
  account_id?: string;
  created_at?: string;
}

export interface GatewayStats {
  clients: number;
  transfers: Record<string, number>;
  operations: Record<string, number>;
  regions: number;
}

export interface GatewayNode {
  code?: string;
  region?: string;
  region_name?: string;
  name?: string;
  primary_up?: boolean | null;
  standby_up?: boolean | null;
  service_available?: boolean | null;
  last_event?: string | null;
  event_at?: string | null;
  primary_status?: string;
  standby_status?: string;
  primary_name?: string;
  standby_name?: string;
}

export interface GatewayNodeActions {
  agent_online: boolean;
  jobs: Array<{
    id: string;
    region: string;
    action: string;
    status: string;
    reason: string;
    result?: string;
    created_at?: string;
    updated_at?: string;
  }>;
}

export interface GatewayQuote {
  source_currency: string;
  destination_currency: string;
  amount_minor: number;
  fee_minor: number;
  total_debit_minor: number;
  credit_minor: number;
  rate: string;
  source_amount: string;
  fee: string;
  total_debit: string;
  recipient_amount: string;
  fx_source: string;
  updated_at: string;
  notice: string;
}

export interface GatewayErrorPayload {
  detail?: string | { message?: string };
  message?: string;
}