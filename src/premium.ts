// Dummy business logic for the OTA POC. No real tariffs or company data.
// Changing these rules is pure JavaScript, so it can ship as an OTA update.

export type Plan = 'Bronze' | 'Silver' | 'Gold';

export const RULES_VERSION = '2026.1';

const BASE_PREMIUM: Record<Plan, number> = {
  Bronze: 1000,
  Silver: 2000,
  Gold: 3500,
};

export function ageFactor(age: number): number {
  if (!Number.isInteger(age) || age < 0 || age > 120) {
    throw new Error(`Invalid age: ${age}`);
  }
  if (age < 30) return 1.0;
  if (age < 50) return 1.3;
  return 1.8;
}

export function calculatePremium(plan: Plan, age: number, smoker: boolean): number {
  const base = BASE_PREMIUM[plan] * ageFactor(age);
  const loaded = smoker ? base * 1.2 : base;
  return Math.round(loaded);
}
