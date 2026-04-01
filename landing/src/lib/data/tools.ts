// src/lib/data/tools.ts

export type ToolCategory =
  | 'Discovery'
  | 'Schema'
  | 'Sampling'
  | 'Query'
  | 'Semantic'
  | 'Connections'
  | 'Comparison';

export type Tool = {
  readonly name: string;
  readonly description: string;
  readonly category: ToolCategory;
};

export const TOOLS: readonly Tool[] = [
  // Discovery
  { name: 'list_tables',                      category: 'Discovery',   description: 'List all visible tables with row counts.' },
  { name: 'search_tables',                    category: 'Discovery',   description: 'Filter tables by keyword — useful in large schemas.' },
  // Schema
  { name: 'describe_table',                   category: 'Schema',      description: 'Column definitions, types, nullability, and foreign key annotations.' },
  { name: 'table_relationships',              category: 'Schema',      description: 'Foreign key graph for one table or the entire database.' },
  { name: 'schema_summary',                   category: 'Schema',      description: 'All tables with row counts, sizes, and FK map in one call.' },
  { name: 'show_create_view',                 category: 'Schema',      description: 'Full CREATE VIEW SQL — untruncated.' },
  // Sampling
  { name: 'sample_table',                     category: 'Sampling',    description: 'Return N rows from a table to understand value formats.' },
  { name: 'sample_column_values',             category: 'Sampling',    description: 'Distinct values with counts — understand categorical columns.' },
  { name: 'table_row_count',                  category: 'Sampling',    description: 'Approximate row count from information_schema.' },
  { name: 'inspect_json_column',              category: 'Sampling',    description: 'Formatted JSON samples from a column storing structured JSON.' },
  // Query
  { name: 'run_read_only_query',              category: 'Query',       description: 'Execute a SELECT query with automatic LIMIT and timeout enforcement.' },
  { name: 'explain_query',                    category: 'Query',       description: 'EXPLAIN output — inspect query plans before execution.' },
  // Semantic
  { name: 'get_database_context',             category: 'Semantic',    description: 'Full business mental model: domain, vocabulary, core workflow.' },
  { name: 'get_table_semantics',              category: 'Semantic',    description: 'Business description, column meanings, and common queries for a table.' },
  { name: 'search_schema_by_meaning',         category: 'Semantic',    description: 'Find tables and columns by business term, not column name.' },
  // Connections
  { name: 'list_connections',                 category: 'Connections', description: 'All configured connection profiles with host, database, and type.' },
  { name: 'ping_connections',                 category: 'Connections', description: 'Health check (SELECT 1) across one or all connection profiles.' },
  // Comparison
  { name: 'compare_query_across_connections', category: 'Comparison',  description: 'Run the same query on multiple databases and show results side by side.' },
  { name: 'diff_schema',                      category: 'Comparison',  description: 'Compare table lists or column definitions between two connections.' },
  { name: 'find_table_across_connections',    category: 'Comparison',  description: 'Discover which connections contain a given table.' },
  { name: 'compare_row_counts',               category: 'Comparison',  description: 'Approximate row counts for a table across multiple connections.' },
] as const;
