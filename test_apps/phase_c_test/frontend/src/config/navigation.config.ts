/**
 * Navigation Configuration
 *
 * SAFE TO MODIFY: This file is intentionally separated from business logic
 * for AI-assisted customization. Modify navigation items here without
 * touching component code.
 *
 * @ai-safe-edit
 */

import {
  LayoutDashboard,
  Box,
  Settings,
  Users,
  FileText,
  BarChart,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Optional badge to show (e.g., notification count) */
  badge?: string | number;
  /** Whether this item is visible */
  visible?: boolean;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

/**
 * Main navigation items for the sidebar
 */
export const mainNavigation: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    href: "/dashboard/automationworkflows",
    label: "AutomationWorkflows",
    icon: Box,
  },
];

/**
 * Settings and account navigation
 */
export const settingsNavigation: NavItem[] = [
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: Settings,
  },
];

/**
 * All navigation sections
 */
export const navigationConfig = {
  appName: "AI-PoweredCrmAutomation",
  main: mainNavigation,
  settings: settingsNavigation,
} as const;

export type NavigationConfig = typeof navigationConfig;
