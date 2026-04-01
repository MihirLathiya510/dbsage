<!-- src/lib/components/Nav.svelte -->
<script lang="ts">
  let { stars }: { stars: number } = $props();
</script>

<nav>
  <a href="/" class="brand" aria-label="dbsage home">
    <img src="/logo.png" alt="" width="28" height="28" />
    <span class="wordmark">dbsage</span>
  </a>

  <a
    href="https://github.com/MihirLathiya510/dbsage"
    class="stars"
    target="_blank"
    rel="noopener noreferrer"
    aria-label="Star dbsage on GitHub"
  >
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
    </svg>
    <span>{stars > 0 ? stars.toLocaleString() : '—'}</span>
  </a>
</nav>

<style>
  nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 40px;
    border-bottom: 1px solid var(--color-border);
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .brand img {
    object-fit: contain;
    width: 28px;
    height: 28px;
  }

  .wordmark {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--color-text);
  }

  .stars {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--color-muted);
    font-size: 13px;
    font-family: var(--font-mono);
    transition: color 0.15s ease;
  }

  .stars:hover {
    color: var(--color-text);
  }

  @media (max-width: 640px) {
    nav {
      padding: 16px 20px;
    }
  }
</style>
