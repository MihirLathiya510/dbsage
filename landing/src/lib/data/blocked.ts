// src/lib/data/blocked.ts

export const BLOCKED_KEYWORDS = [
  'INSERT', 'UPDATE', 'DELETE', 'DROP',
  'ALTER', 'TRUNCATE', 'CREATE', 'GRANT', 'REVOKE',
] as const;

export type BlockedKeyword = (typeof BLOCKED_KEYWORDS)[number];
