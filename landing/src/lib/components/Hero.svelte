<!-- src/lib/components/Hero.svelte -->
<script lang="ts">
  import Terminal from './Terminal.svelte';

  let copied = $state(false);

  function copyInstall() {
    navigator.clipboard.writeText('uvx dbsage');
    copied = true;
    setTimeout(() => { copied = false; }, 2000);
  }
</script>

<section>
  <div class="content">
    <div class="left">
      <p class="eyebrow">MCP Server · MySQL · PostgreSQL</p>

      <h1>
        Let AI in.<br />
        Keep your<br />
        data safe.
      </h1>

      <p class="subline">
        21 read-only tools. Zero mutations.<br />
        Plugs into Claude, Cursor, and any MCP client.
      </p>

      <div class="actions">
        <button class="install-pill" onclick={copyInstall} aria-label="Copy install command">
          <span class="pill-prefix">$</span>
          <span class="pill-cmd">uvx dbsage</span>
          <span class="pill-copy" aria-hidden="true">
            {copied ? '✓ copied' : 'copy'}
          </span>
        </button>

        <a
          href="https://github.com/MihirLathiya510/dbsage"
          class="github-link"
          target="_blank"
          rel="noopener noreferrer"
        >
          View on GitHub →
        </a>
      </div>
    </div>

    <div class="right">
      <Terminal />
    </div>
  </div>
</section>

<style>
  section {
    padding: 80px 40px 100px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .content {
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 64px;
    align-items: center;
  }

  .eyebrow {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-muted);
    margin-bottom: 20px;
  }

  h1 {
    font-size: clamp(52px, 6vw, 80px);
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1.05;
    color: var(--color-text);
    margin-bottom: 24px;
  }

  .subline {
    font-size: 18px;
    line-height: 1.6;
    color: var(--color-muted);
    margin-bottom: 40px;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
  }

  .install-pill {
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 10px 16px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--color-text);
    transition: border-color 0.15s ease;
  }

  .install-pill:hover {
    border-color: var(--color-muted);
  }

  .pill-prefix {
    color: var(--color-muted);
  }

  .pill-cmd {
    color: var(--color-text);
  }

  .pill-copy {
    font-size: 11px;
    color: var(--color-muted);
    border-left: 1px solid var(--color-border);
    padding-left: 10px;
    margin-left: 2px;
    min-width: 46px;
  }

  .github-link {
    font-size: 14px;
    color: var(--color-muted);
    transition: color 0.15s ease;
  }

  .github-link:hover {
    color: var(--color-text);
  }

  @media (max-width: 900px) {
    .content {
      grid-template-columns: 1fr;
      gap: 48px;
    }

    section {
      padding: 60px 20px 80px;
    }
  }
</style>
