// Run with: npm test  (uses Node's built-in test runner, no extra packages)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calculatePremium, ageFactor } from './premium.ts';

test('age bands', () => {
  assert.equal(ageFactor(25), 1.0);
  assert.equal(ageFactor(30), 1.3);
  assert.equal(ageFactor(50), 1.8);
});

test('premium calculation', () => {
  assert.equal(calculatePremium('Bronze', 25, false), 1000);
  assert.equal(calculatePremium('Silver', 40, false), 2600);
  assert.equal(calculatePremium('Gold', 55, true), 7560);
});

test('rejects invalid age', () => {
  assert.throws(() => ageFactor(-1));
  assert.throws(() => ageFactor(30.5));
});
