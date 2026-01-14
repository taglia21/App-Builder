/**
 * Feature Flags Configuration
 *
 * SAFE TO MODIFY: Toggle features on/off without changing code.
 * AI agents can safely enable/disable functionality here.
 *
 * @ai-safe-edit
 */

export const featuresConfig = {
  /**
   * Authentication features
   */
  auth: {
    /** Enable social login (Google, GitHub) */
    socialLogin: false,
    /** Enable "Remember me" checkbox */
    rememberMe: true,
    /** Enable password reset functionality */
    passwordReset: false,
    /** Enable email verification requirement */
    emailVerification: false,
  },

  /**
   * Dashboard features
   */
  dashboard: {
    /** Show analytics/stats cards on dashboard */
    showStats: true,
    /** Enable dark mode toggle */
    darkMode: true,
    /** Show recent activity feed */
    activityFeed: false,
    /** Enable keyboard shortcuts */
    keyboardShortcuts: false,
  },

  /**
   * AutomationWorkflow features
   */
  automationworkflow: {
    /** Enable bulk actions (select multiple) */
    bulkActions: false,
    /** Show advanced filters */
    advancedFilters: false,
    /** Enable export to CSV/Excel */
    exportEnabled: false,
    /** Enable import from CSV */
    importEnabled: false,
  },

  /**
   * UI/UX features
   */
  ui: {
    /** Show loading skeletons vs spinners */
    useSkeletons: true,
    /** Enable animations */
    animations: true,
    /** Show toast notifications */
    toasts: true,
    /** Enable offline support */
    offlineSupport: false,
  },
} as const;

export type FeaturesConfig = typeof featuresConfig;

/**
 * Check if a feature is enabled
 * Usage: isFeatureEnabled("auth.socialLogin")
 */
export function isFeatureEnabled(path: string): boolean {
  const keys = path.split(".");
  let value: any = featuresConfig;
  for (const key of keys) {
    value = value?.[key];
  }
  return value === true;
}
