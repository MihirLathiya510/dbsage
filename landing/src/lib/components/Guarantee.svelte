<!-- src/lib/components/Guarantee.svelte -->
<script lang="ts">
  import { BLOCKED_KEYWORDS } from '$lib/data/blocked';
</script>

<section>
  <div class="inner">
    <ul class="keywords" role="list" aria-label="Blocked SQL operations">
      {#each BLOCKED_KEYWORDS as keyword}
        <li><del>{keyword}</del></li>
      {/each}
    </ul>
    <p class="note">
      Enforced at the query layer. Not a promise — a hard block.
    </p>
  </div>
</section>

<style>
  section {
    border-top: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
    padding: 48px 40px;
  }

  .inner {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .keywords {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    list-style: none;
    padding: 0;
  }

  .keywords li del {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--color-red);
    text-decoration-color: var(--color-red);
    text-decoration-thickness: 2px;
    background: color-mix(in srgb, var(--color-red) 8%, transparent);
    padding: 5px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid color-mix(in srgb, var(--color-red) 20%, transparent);
  }

  .note {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-muted);
    text-align: center;
    letter-spacing: 0.02em;
  }

  @media (max-width: 640px) {
    section {
      padding: 36px 20px;
    }
  }
</style>
