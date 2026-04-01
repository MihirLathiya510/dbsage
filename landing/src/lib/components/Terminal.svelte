<!-- src/lib/components/Terminal.svelte -->
<script lang="ts">
</script>

<div class="window">
  <div class="chrome">
    <span class="dot red"></span>
    <span class="dot yellow"></span>
    <span class="dot green"></span>
    <span class="chrome-title">MCP Exchange</span>
  </div>

  <div class="body">
    <p class="line" style="--i:0">
      <span class="speaker claude">Claude</span>
      <span class="arrow">→</span>
      <span>list the top 5 users by order count</span>
    </p>

    <div class="line sql-block" style="--i:1">
      <span class="speaker sage">dbsage</span>
      <span class="arrow">→</span>
      <pre><code>SELECT u.email, COUNT(o.id) AS orders
FROM users u
JOIN orders o ON o.user_id = u.id
GROUP BY u.id
ORDER BY orders DESC
LIMIT 5</code></pre>
    </div>

    <div class="line table-block" style="--i:2">
      <pre><code class="table-output">┌───────────────────────────┬────────┐
│ email                     │ orders │
├───────────────────────────┼────────┤
│ alice@example.com         │    142 │
│ bob@example.com           │     98 │
│ carol@example.com         │     87 │
└───────────────────────────┴────────┘</code></pre>
    </div>

    <p class="line" style="--i:3">
      <span class="speaker claude">Claude</span>
      <span class="arrow">→</span>
      <span>now drop the users table</span>
    </p>

    <p class="line blocked" style="--i:4">
      <span class="speaker sage">dbsage</span>
      <span class="arrow">→</span>
      <span class="blocked-text">✗ Blocked: DROP is a forbidden operation.</span>
    </p>
  </div>
</div>

<style>
  .window {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.6;
  }

  .chrome {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg);
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot.red    { background: #ff5f57; }
  .dot.yellow { background: #febc2e; }
  .dot.green  { background: #28c840; }

  .chrome-title {
    margin-left: 8px;
    font-size: 11px;
    color: var(--color-muted);
    letter-spacing: 0.05em;
  }

  .body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .line {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    opacity: 0;
  }

  .speaker {
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    padding-top: 2px;
    min-width: 52px;
  }

  .speaker.claude { color: var(--color-muted); }
  .speaker.sage   { color: var(--color-text); }

  .arrow {
    color: var(--color-border);
    padding-top: 2px;
  }

  pre {
    margin: 0;
    white-space: pre;
    overflow-x: auto;
  }

  code {
    color: var(--color-text);
  }

  .table-output {
    color: var(--color-muted);
    font-size: 12px;
  }

  .table-block {
    padding-left: calc(52px + 8px + 16px + 8px);
  }

  .blocked-text {
    color: var(--color-red);
    font-weight: 500;
  }

  @media (prefers-reduced-motion: no-preference) {
    .line {
      animation: line-in 0.3s ease forwards;
      animation-delay: calc(var(--i) * 0.35s + 0.4s);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .line { opacity: 1; }
  }

  @keyframes line-in {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
