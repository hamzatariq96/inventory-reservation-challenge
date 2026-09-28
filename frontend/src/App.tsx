import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, Product } from "./api";
import { currentStatus, formatRemaining, Reservation, validateQuantity } from "./lib/stock";

function useNow(intervalMs = 1000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function App() {
  const now = useNow();
  const [products, setProducts] = useState<Product[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [newProduct, setNewProduct] = useState({ sku: "", name: "", stock: "10" });

  const refresh = useCallback(async () => {
    try {
      setProducts(await api.listProducts());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Re-read availability when a reservation lapses, since the server frees that stock.
  const expiredCount = reservations.filter((r) => currentStatus(r, now) === "expired").length;
  useEffect(() => {
    if (expiredCount > 0) void refresh();
  }, [expiredCount, refresh]);

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function replaceReservation(updated: Reservation) {
    setReservations((list) => list.map((r) => (r.id === updated.id ? updated : r)));
  }

  function onCreateProduct(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      await api.createProduct(newProduct.sku.trim(), newProduct.name.trim(), Number(newProduct.stock));
      setNewProduct({ sku: "", name: "", stock: "10" });
    });
  }

  function onReserve(product: Product) {
    const raw = quantities[product.id] ?? "1";
    const problem = validateQuantity(raw, product.available);
    if (problem) {
      setError(`${product.name}: ${problem}`);
      return;
    }
    void run(async () => {
      // A new key per click; retries of the same request would reuse it.
      const reservation = await api.reserve(product.id, Number(raw), crypto.randomUUID());
      setReservations((list) => [reservation, ...list]);
    });
  }

  const productName = (id: number) => products.find((p) => p.id === id)?.name ?? `#${id}`;

  return (
    <main>
      <h1>Inventory Reservations</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <section>
        <h2>Products</h2>
        <form onSubmit={onCreateProduct} className="row">
          <input placeholder="SKU" value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} required />
          <input placeholder="Name" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} required />
          <input type="number" min={0} value={newProduct.stock} onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })} />
          <button type="submit">Add product</button>
        </form>

        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Available</th>
              <th>Reserve</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>{p.sku}</td>
                <td>{p.name}</td>
                <td>
                  {p.available} / {p.total_stock}
                </td>
                <td className="row">
                  <input
                    aria-label={`Quantity for ${p.name}`}
                    value={quantities[p.id] ?? "1"}
                    onChange={(e) => setQuantities({ ...quantities, [p.id]: e.target.value })}
                  />
                  <button onClick={() => onReserve(p)} disabled={p.available === 0}>
                    Reserve
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>My reservations</h2>
        {reservations.length === 0 && <p className="muted">Nothing reserved yet.</p>}
        <ul>
          {reservations.map((r) => {
            const status = currentStatus(r, now);
            return (
              <li key={r.id} className={`status-${status}`}>
                <span>
                  {r.quantity} × {productName(r.product_id)}: <strong>{status}</strong>
                  {status === "active" && ` (${formatRemaining(r.expires_at, now)} left)`}
                </span>
                {status === "active" && (
                  <span className="row">
                    <button onClick={() => void run(async () => replaceReservation(await api.confirm(r.id)))}>Confirm</button>
                    <button onClick={() => void run(async () => replaceReservation(await api.release(r.id)))}>Release</button>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}
