import { describe, it, expect } from 'vitest';
import { BLOCKED_KEYWORDS } from './blocked';

describe('BLOCKED_KEYWORDS', () => {
  it('has exactly 9 entries', () => {
    expect(BLOCKED_KEYWORDS).toHaveLength(9);
  });

  it('contains the required SQL mutation keywords', () => {
    const required = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'CREATE', 'GRANT', 'REVOKE'];
    for (const kw of required) {
      expect(BLOCKED_KEYWORDS).toContain(kw);
    }
  });
});
