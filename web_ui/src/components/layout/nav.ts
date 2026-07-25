import {
  LayoutDashboard,
  ShieldCheck,
  ScrollText,
  Store,
  Radar,
  Smartphone,
  Bot,
  Share2,
  Cpu,
  ServerCog,
  KeyRound,
  Scale,
  type LucideIcon,
} from "lucide-react";

export type ViewId =
  | "overview"
  | "safety"
  | "constitution"
  | "audit"
  | "platforms"
  | "olx"
  | "fleet"
  | "swarm"
  | "kg"
  | "ml"
  | "services"
  | "admin";

export interface NavItem {
  id: ViewId;
  label: string;
  icon: LucideIcon;
  description: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Monitoring",
    items: [
      { id: "overview", label: "Overview", icon: LayoutDashboard, description: "System health & live KPIs" },
      { id: "safety", label: "Safety & Compliance", icon: ShieldCheck, description: "Risk scoring & guardrails" },
      { id: "constitution", label: "Constitution", icon: Scale, description: "67 governance articles" },
      { id: "audit", label: "Audit Stream", icon: ScrollText, description: "Immutable activity log" },
    ],
  },
  {
    label: "Operations",
    items: [
      { id: "platforms", label: "Platforms", icon: Store, description: "9 marketplace connectors" },
      { id: "olx", label: "OLX Collector", icon: Radar, description: "Live listings & subscriptions" },
      { id: "fleet", label: "Android Fleet", icon: Smartphone, description: "Emulator & device pool" },
      { id: "swarm", label: "Agent Swarm", icon: Bot, description: "Autonomous agent roster" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { id: "kg", label: "Knowledge Graph", icon: Share2, description: "Federated entity graph" },
      { id: "ml", label: "Model Registry", icon: Cpu, description: "ML model catalog & evals" },
    ],
  },
  {
    label: "Administration",
    items: [
      { id: "services", label: "Services", icon: ServerCog, description: "Systemd process control" },
      { id: "admin", label: "Secure Admin", icon: KeyRound, description: "Control access & verified backups" },
    ],
  },
];

export const ALL_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function findItem(id: ViewId): NavItem {
  return ALL_ITEMS.find((i) => i.id === id) ?? ALL_ITEMS[0];
}
