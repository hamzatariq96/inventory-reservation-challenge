// Pure helpers used by the UI. They take "now" as an argument instead of reading
// the system clock, which keeps them trivially testable.

export type ReservationStatus = "active" | "confirmed" | "released" | "expired";

export interface Reservation {
  id: number;
  product_id: number;
  quantity: number;
  status: ReservationStatus;
  created_at: string;
  expires_at: string;
}

/** The API returns naive UTC timestamps; parse them as UTC explicitly. */
export function parseUtc(timestamp: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(timestamp) ? timestamp : `${timestamp}Z`);
}

/** "m:ss" until expiry, or "expired" once the deadline has passed. */
export function formatRemaining(expiresAt: string, now: Date): string {
  const ms = parseUtc(expiresAt).getTime() - now.getTime();
  if (ms <= 0) return "expired";
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/** Mirrors the server's view of a reservation so the UI updates without a refetch. */
export function currentStatus(reservation: Reservation, now: Date): ReservationStatus {
  if (reservation.status === "active" && parseUtc(reservation.expires_at).getTime() <= now.getTime()) {
    return "expired";
  }
  return reservation.status;
}

/** Returns an error message, or null when the quantity can be requested. */
export function validateQuantity(raw: string, available: number): string | null {
  if (!/^\d+$/.test(raw.trim())) return "Enter a whole number";
  const quantity = Number(raw);
  if (quantity < 1) return "Quantity must be at least 1";
  if (quantity > available) return `Only ${available} available`;
  return null;
}
