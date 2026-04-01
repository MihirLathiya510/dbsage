<!-- src/lib/components/ToolsGrid.svelte -->
<script lang="ts">
  import { TOOLS, type ToolCategory } from '$lib/data/tools';

  const CATEGORY_ORDER: ToolCategory[] = [
    'Discovery', 'Schema', 'Sampling', 'Query', 'Semantic', 'Connections', 'Comparison',
  ];

  const byCategory = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    tools: TOOLS.filter((t) => t.category === cat),
  }));
</script>

<section>
  <div class="inner">
    <h2>21 tools. Everything an AI agent needs to understand a database.</h2>

    <div class="categories">
      {#each byCategory as group}
        <div class="group">
          <p class="category-label">{group.category}</p>
          <ul class="grid" role="list" style="--cols: {Math.min(group.tools.length, 4)}">
            {#each group.tools as tool}
              <li class="card">
                <code class="tool-name">{tool.name}</code>
                <p class="tool-desc">{tool.description}</p>
              </li>
            {/each}
          </ul>
        </div>
      {/each}
    </div>
  </div>
</section>

<style>
  section {
    padding: 96px 40px;
    max-width: 1200px;
    margin: 0 auto;
  }

  h2 {
    font-size: clamp(24px, 3vw, 36px);
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--color-text);
    margin-bottom: 64px;
    max-width: 600px;
  }

  .categories {
    display: flex;
    flex-direction: column;
    gap: 48px;
  }

  .group {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .category-label {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-muted);
    padding-bottom: 12px;
    border-bottom: 1px solid var(--color-border);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(var(--cols, 4), 1fr);
    gap: 1px;
    background: var(--color-border);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    list-style: none;
    padding: 0;
  }

  .card {
    background: var(--color-bg);
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: background 0.15s ease;
  }

  .card:hover {
    background: var(--color-surface);
  }

  .tool-name {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text);
  }

  .tool-desc {
    font-size: 13px;
    color: var(--color-muted);
    line-height: 1.5;
  }

  @media (max-width: 900px) {
    .grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 640px) {
    section {
      padding: 64px 20px;
    }

    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
