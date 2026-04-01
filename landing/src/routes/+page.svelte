<!-- src/routes/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import type { PageData } from './$types';
  import Nav from '$lib/components/Nav.svelte';
  import Hero from '$lib/components/Hero.svelte';
  import Guarantee from '$lib/components/Guarantee.svelte';
  import ToolsGrid from '$lib/components/ToolsGrid.svelte';
  import Install from '$lib/components/Install.svelte';
  import Footer from '$lib/components/Footer.svelte';

  let { data }: { data: PageData } = $props();

  let liveStars = $state<number | null>(null);
  const stars = $derived(liveStars ?? data.stars);

  onMount(async () => {
    try {
      const res = await fetch('https://api.github.com/repos/MihirLathiya510/dbsage');
      if (res.ok) {
        const json = await res.json() as { stargazers_count: number };
        liveStars = json.stargazers_count;
      }
    } catch {
      // keep build-time value
    }
  });
</script>

<Nav {stars} />

<main>
  <Hero />
  <Guarantee />
  <ToolsGrid />
  <Install />
</main>

<Footer />
