import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import Install from './Install.svelte';

describe('Install', () => {
  it('renders the Claude Code tab by default', () => {
    render(Install);
    expect(screen.getByRole('tab', { name: 'Claude Code' })).toHaveAttribute('aria-selected', 'true');
  });

  it('switches to Cursor tab on click', async () => {
    render(Install);
    await fireEvent.click(screen.getByRole('tab', { name: 'Cursor' }));
    expect(screen.getByRole('tab', { name: 'Cursor' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Claude Code' })).toHaveAttribute('aria-selected', 'false');
  });

  it('copy button resets after 2 seconds', async () => {
    vi.useFakeTimers();
    render(Install);
    const copyBtn = screen.getByRole('button', { name: /copy/i });
    await fireEvent.click(copyBtn);
    expect(copyBtn).toHaveTextContent('copied');
    vi.advanceTimersByTime(2000);
    await tick();
    expect(copyBtn).toHaveTextContent('copy');
    vi.useRealTimers();
  });
});
