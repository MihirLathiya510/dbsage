<!-- src/lib/components/Install.svelte -->
<script lang="ts">
  type Tab = 'claude-code' | 'cursor' | 'claude-desktop';

  const TABS: { id: Tab; label: string }[] = [
    { id: 'claude-code',    label: 'Claude Code' },
    { id: 'cursor',         label: 'Cursor' },
    { id: 'claude-desktop', label: 'Claude Desktop' },
  ];

  const CONFIGS: Record<Tab, string> = {
    'claude-code': `# ~/.claude/mcp.json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host",
        "DBSAGE_DB_NAME": "your-db",
        "DBSAGE_DB_USER": "your-user",
        "DBSAGE_DB_PASSWORD": "your-password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}`,
    'cursor': `# .cursor/mcp.json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host",
        "DBSAGE_DB_NAME": "your-db",
        "DBSAGE_DB_USER": "your-user",
        "DBSAGE_DB_PASSWORD": "your-password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}`,
    'claude-desktop': `# ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host",
        "DBSAGE_DB_NAME": "your-db",
        "DBSAGE_DB_USER": "your-user",
        "DBSAGE_DB_PASSWORD": "your-password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}`,
  };

  let activeTab = $state<Tab>('claude-code');
  let copied = $state(false);

  function copy() {
    navigator.clipboard.writeText(CONFIGS[activeTab]);
    copied = true;
    setTimeout(() => { copied = false; }, 2000);
  }
</script>

<section>
  <div class="inner">
    <h2>Connect in 60 seconds.</h2>

    <div class="panel">
      <div class="tabs" role="tablist" aria-label="MCP client installation">
        {#each TABS as tab}
          <button
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls="panel-{tab.id}"
            id="tab-{tab.id}"
            onclick={() => { activeTab = tab.id; copied = false; }}
          >{tab.label}</button>
        {/each}
      </div>

      <div class="code-area" id="panel-{activeTab}" role="tabpanel" aria-labelledby="tab-{activeTab}">
        <button class="copy-btn" onclick={copy} aria-live="polite">
          {copied ? 'copied' : 'copy'}
        </button>
        <pre><code>{CONFIGS[activeTab]}</code></pre>
      </div>
    </div>
  </div>
</section>

<style>
  section {
    padding: 0 40px 96px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .inner {
    max-width: 1200px;
  }

  h2 {
    font-size: clamp(24px, 3vw, 36px);
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--color-text);
    margin-bottom: 32px;
  }

  .panel {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .tabs button {
    padding: 12px 20px;
    font-size: 13px;
    font-family: var(--font-mono);
    color: var(--color-muted);
    border-right: 1px solid var(--color-border);
    border-radius: 0;
    transition: color 0.15s ease, background 0.15s ease;
  }

  .tabs button:hover {
    color: var(--color-text);
    background: var(--color-bg);
  }

  .tabs button[aria-selected='true'] {
    color: var(--color-text);
    background: var(--color-bg);
    border-bottom: 2px solid var(--color-text);
    margin-bottom: -1px;
  }

  .code-area {
    position: relative;
    background: var(--color-bg);
  }

  pre {
    padding: 24px;
    overflow-x: auto;
    margin: 0;
  }

  code {
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.7;
    color: var(--color-muted);
  }

  .copy-btn {
    position: absolute;
    top: 12px;
    right: 12px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--color-muted);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 4px 10px;
    transition: color 0.15s ease, border-color 0.15s ease;
    min-width: 52px;
    text-align: center;
  }

  .copy-btn:hover {
    color: var(--color-text);
    border-color: var(--color-muted);
  }

  @media (max-width: 640px) {
    section {
      padding: 0 20px 64px;
    }

    .tabs button {
      padding: 10px 14px;
      font-size: 12px;
    }
  }
</style>
