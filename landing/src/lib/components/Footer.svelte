<!-- src/lib/components/Footer.svelte -->
<script lang="ts">
</script>

<footer>
  <p>
    dbsage
    <span class="sep">·</span>
    MIT License
    <span class="sep">·</span>
    <a
      href="https://github.com/MihirLathiya510/dbsage"
      target="_blank"
      rel="noopener noreferrer"
    >GitHub</a>
  </p>
</footer>

<style>
  footer {
    border-top: 1px solid var(--color-border);
    padding: 32px 40px;
    text-align: center;
  }

  p {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-muted);
    letter-spacing: 0.04em;
  }

  .sep {
    margin: 0 8px;
  }

  a {
    color: var(--color-muted);
    transition: color 0.15s ease;
  }

  a:hover {
    color: var(--color-text);
  }

  @media (max-width: 640px) {
    footer {
      padding: 24px 20px;
    }
  }
</style>
