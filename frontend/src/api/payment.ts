import { API_BASE_URL } from "@/lib/env";
import type { AuthUser } from "@/stores/auth";

const PAYMENT_API = `${API_BASE_URL}/api/v1/payment`;

export async function cancelSubscription(): Promise<AuthUser | null> {
  const res = await fetch(`${PAYMENT_API}/cancel`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function confirmPayment(
  data: { paymentKey: string; orderId: string; amount: number },
): Promise<AuthUser | null> {
  const res = await fetch(`${PAYMENT_API}/confirm`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) return null;
  return res.json();
}
