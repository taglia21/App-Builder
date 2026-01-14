/**
 * Copy/Content Configuration
 *
 * SAFE TO MODIFY: This file contains all user-facing text strings.
 * AI agents can safely edit these without affecting application logic.
 *
 * @ai-safe-edit
 */

export const copyConfig = {
  /**
   * Application branding
   */
  app: {
    name: "AI-PoweredCrmAutomation",
    tagline: "Your AI-PoweredCrmAutomation dashboard",
    description: "AI-Powered Crm Automation",
  },

  /**
   * Authentication pages
   */
  auth: {
    login: {
      title: "Welcome back",
      subtitle: "Sign in to your account",
      emailLabel: "Email",
      passwordLabel: "Password",
      submitButton: "Sign in",
      registerLink: "Don't have an account? Sign up",
      forgotPasswordLink: "Forgot password?",
    },
    register: {
      title: "Create an account",
      subtitle: "Get started with AI-PoweredCrmAutomation",
      emailLabel: "Email",
      passwordLabel: "Password",
      confirmPasswordLabel: "Confirm password",
      nameLabel: "Full name",
      submitButton: "Create account",
      loginLink: "Already have an account? Sign in",
    },
  },

  /**
   * Dashboard pages
   */
  dashboard: {
    welcome: "Welcome to AI-PoweredCrmAutomation",
    emptyState: "No automationworkflows found. Create your first one!",
    createButton: "Create AutomationWorkflow",
  },

  /**
   * Common UI elements
   */
  common: {
    loading: "Loading...",
    error: "Something went wrong",
    retry: "Try again",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    view: "View",
    search: "Search...",
    noResults: "No results found",
  },

  /**
   * Error messages
   */
  errors: {
    networkError: "Unable to connect. Please check your internet connection.",
    unauthorized: "Please sign in to continue.",
    notFound: "The requested resource was not found.",
    serverError: "An unexpected error occurred. Please try again later.",
  },
} as const;

export type CopyConfig = typeof copyConfig;

/**
 * Helper to get nested copy values
 * Usage: getCopy("auth.login.title")
 */
export function getCopy(path: string): string {
  const keys = path.split(".");
  let value: any = copyConfig;
  for (const key of keys) {
    value = value?.[key];
  }
  return typeof value === "string" ? value : path;
}
