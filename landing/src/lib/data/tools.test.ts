import { describe, it, expect } from 'vitest';
import { TOOLS } from './tools';

describe('TOOLS', () => {
  it('has exactly 21 entries', () => {
    expect(TOOLS).toHaveLength(21);
  });

  it('every entry has a non-empty name, description, and category', () => {
    for (const tool of TOOLS) {
      expect(tool.name.length).toBeGreaterThan(0);
      expect(tool.description.length).toBeGreaterThan(0);
      expect(tool.category.length).toBeGreaterThan(0);
    }
  });

  it('has no duplicate names', () => {
    const names = TOOLS.map((t) => t.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it('categories are one of the seven allowed values', () => {
    const allowed = new Set([
      'Discovery', 'Schema', 'Sampling',
      'Query', 'Semantic', 'Connections', 'Comparison',
    ]);
    for (const tool of TOOLS) {
      expect(allowed.has(tool.category)).toBe(true);
    }
  });
});
