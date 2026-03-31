import type { Metadata } from "next";

import DemoLoginPanel from "@/features/auth/demo-login-panel";

export const metadata: Metadata = {
  title: "Login - Sales Forecasting Platform",
  description: "Enable local demo access for the protected MVP pages",
};

export default function LoginPage() {
  return <DemoLoginPanel />;
}
