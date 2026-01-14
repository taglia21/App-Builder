/**
 * Theme Configuration
 *
 * This file contains all design tokens for the "Modern" theme.
 * AI agents can safely modify colors, fonts, spacing, and other visual properties here
 * without affecting business logic in components.
 *
 * To change the theme:
 * 1. Modify the values in this file
 * 2. Update globals.css :root variables to match
 * 3. Components will automatically pick up the changes
 */

export const themeConfig = {
  /** Theme identifier */
  name: "Modern",

  /** Color palette - HSL values matching CSS variables in globals.css */
  colors: {
    primary: "hsl(var(--primary))",
    primaryForeground: "hsl(var(--primary-foreground))",
    secondary: "hsl(var(--secondary))",
    secondaryForeground: "hsl(var(--secondary-foreground))",
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    card: "hsl(var(--card))",
    cardForeground: "hsl(var(--card-foreground))",
    muted: "hsl(var(--muted))",
    mutedForeground: "hsl(var(--muted-foreground))",
    accent: "hsl(var(--accent))",
    accentForeground: "hsl(var(--accent-foreground))",
    destructive: "hsl(var(--destructive))",
    destructiveForeground: "hsl(var(--destructive-foreground))",
    border: "hsl(var(--border))",
    input: "hsl(var(--input))",
    ring: "hsl(var(--ring))",
  },

  /** Typography settings */
  fonts: {
    heading: "'Inter', system-ui, sans-serif",
    body: "'Inter', system-ui, sans-serif",
    mono: "monospace",
  },

  /** Spacing and sizing */
  spacing: {
    radius: "0.5rem",
    containerMaxWidth: "1400px",
    containerPadding: "2rem",
  },

  /** Visual effects */
  effects: {
    /** Border style preference: "solid" | "none" | "gradient" */
    borderStyle: "solid",
    /** Shadow intensity: "none" | "subtle" | "medium" | "strong" */
    shadowIntensity: "subtle",
    /** Enable animations */
    animationsEnabled: true,
  },
} as const;

export type ThemeConfig = typeof themeConfig;

/**
 * Helper to get a color value
 * Usage: getColor("primary") returns "hsl(var(--primary))"
 */
export function getColor(name: keyof typeof themeConfig.colors): string {
  return themeConfig.colors[name];
}
