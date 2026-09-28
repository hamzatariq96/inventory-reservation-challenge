import { currentStatus, formatRemaining, parseUtc, Reservation, validateQuantity } from "./stock";

// Fixed instant: no test reads the real clock.
const NOW = new Date("2026-01-01T12:00:00Z");

const reservation = (overrides: Partial<Reservation> = {}): Reservation => ({
  id: 1,
  product_id: 1,
  quantity: 2,
  status: "active",
  created_at: "2026-01-01T12:00:00",
  expires_at: "2026-01-01T12:10:00",
  ...overrides,
});

describe("parseUtc", () => {
  it("treats naive timestamps from the API as UTC", () => {
    expect(parseUtc("2026-01-01T12:00:00").toISOString()).toBe("2026-01-01T12:00:00.000Z");
  });

  it("keeps an explicit offset", () => {
    expect(parseUtc("2026-01-01T12:00:00+05:00").toISOString()).toBe("2026-01-01T07:00:00.000Z");
  });
});

describe("formatRemaining", () => {
  it("formats minutes and zero-padded seconds", () => {
    expect(formatRemaining("2026-01-01T12:09:05", NOW)).toBe("9:05");
  });

  it("rounds partial seconds up so it never shows 0:00 while still active", () => {
    expect(formatRemaining("2026-01-01T12:00:00.400", NOW)).toBe("0:01");
  });

  it("reports expired exactly at the deadline", () => {
    expect(formatRemaining("2026-01-01T12:00:00", NOW)).toBe("expired");
  });
});

describe("currentStatus", () => {
  it("keeps an unexpired reservation active", () => {
    expect(currentStatus(reservation(), NOW)).toBe("active");
  });

  it("marks an active reservation expired at its deadline", () => {
    expect(currentStatus(reservation({ expires_at: "2026-01-01T12:00:00" }), NOW)).toBe("expired");
  });

  it("never expires a confirmed reservation", () => {
    expect(currentStatus(reservation({ status: "confirmed", expires_at: "2025-12-31T00:00:00" }), NOW)).toBe(
      "confirmed",
    );
  });
});

describe("validateQuantity", () => {
  it.each([
    ["abc", 5, "Enter a whole number"],
    ["1.5", 5, "Enter a whole number"],
    ["0", 5, "Quantity must be at least 1"],
    ["6", 5, "Only 5 available"],
  ])("rejects %p when %i are available", (raw, available, message) => {
    expect(validateQuantity(raw, available)).toBe(message);
  });

  it("accepts a quantity within stock", () => {
    expect(validateQuantity(" 5 ", 5)).toBeNull();
  });
});
