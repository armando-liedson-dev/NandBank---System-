import type {
  GatewayCard,
  GatewayMe,
  GatewayNode,
  GatewayStats,
  GatewayTransfer,
} from "./types";

export const DEMO_CUSTOMER: GatewayMe = {
  user: {
    id: "demo-customer-01",
    name: "Cliente de demonstração",
    email: "cliente.demo@example.invalid",
    role: "client",
    region: "AF",
    branch: "Maputo",
  },
  accounts: [
    {
      id: "NB-DEMO-AF-001",
      region: "AF",
      branch: "Maputo",
      currency: "MZN",
      balance: "18420.00",
      balance_minor: 1842000,
      status: "ACTIVE",
    },
    {
      id: "NB-DEMO-EU-002",
      region: "EU",
      branch: "Lisboa",
      currency: "EUR",
      balance: "126.40",
      balance_minor: 12640,
      status: "ACTIVE",
    },
  ],
};

export const DEMO_TRANSFERS: GatewayTransfer[] = [
  {
    id: "DEMO-TX-2026-01",
    source_id: "NB-DEMO-AF-001",
    destination_id: "NB-DEMO-EU-002",
    source_region: "AF",
    dest_region: "EU",
    source_currency: "MZN",
    dest_currency: "EUR",
    amount: "1250.00",
    status: "COMMITTED",
    created_at: "2026-11-20T10:30:00Z",
  },
  {
    id: "DEMO-TX-2026-02",
    source_id: "NB-DEMO-EU-002",
    destination_id: "NB-DEMO-AF-001",
    source_region: "EU",
    dest_region: "AF",
    source_currency: "EUR",
    dest_currency: "MZN",
    amount: "35.00",
    status: "PREPARING",
    created_at: "2026-11-19T13:15:00Z",
  },
];

export const DEMO_CARDS: GatewayCard[] = [
  {
    id: "DEMO-CARD-01",
    status: "ACTIVE",
    last4: "0042",
    holder_name: "Cliente de demonstração",
    currency: "MZN",
    branch: "Maputo",
    account_id: "NB-DEMO-AF-001",
  },
];

export const DEMO_STATS: GatewayStats = {
  clients: 248,
  transfers: { COMMITTED: 1280, PREPARING: 2, ABORTED: 7 },
  operations: { DEPOSIT: 42, WITHDRAW: 19 },
  regions: 6,
};

export const DEMO_NODES: GatewayNode[] = [
  { code: "AF", region: "AF", region_name: "África", primary_up: true, standby_up: true, service_available: true },
  { code: "EU", region: "EU", region_name: "Europa", primary_up: true, standby_up: true, service_available: true },
  { code: "AS", region: "AS", region_name: "Ásia", primary_up: true, standby_up: true, service_available: true },
  { code: "NA", region: "NA", region_name: "América do Norte", primary_up: true, standby_up: true, service_available: true },
  { code: "SA", region: "SA", region_name: "América do Sul", primary_up: true, standby_up: true, service_available: true },
  { code: "OC", region: "OC", region_name: "Oceânia", primary_up: true, standby_up: true, service_available: true },
];