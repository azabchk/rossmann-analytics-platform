import type { Metadata } from "next";

import DemoLoginPanel from "@/features/auth/demo-login-panel";
import { getPublicSupabaseRuntimeConfig } from "@/lib/config/public-runtime-config";

export const metadata: Metadata = {
  title: "Login - Sales Forecasting Platform",
  description: "Sign in, sign up, or enable local thesis demo access",
};

export default function LoginPage() {
  const supabaseConfig = getPublicSupabaseRuntimeConfig();

  return <DemoLoginPanel supabaseConfig={supabaseConfig} />;
}
