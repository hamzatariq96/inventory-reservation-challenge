import type { Reservation } from "./lib/stock";

export interface Product {
  id: number;
  sku: string;
  name: string;
  total_stock: number;
  available: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export const api = {
  listProducts: () => request<Product[]>("/products"),
  createProduct: (sku: string, name: string, totalStock: number) =>
    request<Product>("/products", {
      method: "POST",
      body: JSON.stringify({ sku, name, total_stock: totalStock }),
    }),
  reserve: (productId: number, quantity: number, idempotencyKey: string) =>
    request<Reservation>("/reservations", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity, idempotency_key: idempotencyKey }),
    }),
  confirm: (id: number) => request<Reservation>(`/reservations/${id}/confirm`, { method: "POST" }),
  release: (id: number) => request<Reservation>(`/reservations/${id}/release`, { method: "POST" }),
};
