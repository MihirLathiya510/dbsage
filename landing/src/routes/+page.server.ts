// src/routes/+page.server.ts
export const prerender = true;

export async function load({ fetch }): Promise<{ stars: number }> {
  try {
    const res = await fetch('https://api.github.com/repos/MihirLathiya510/dbsage');
    if (!res.ok) return { stars: 0 };
    const data = await res.json() as { stargazers_count: number };
    return { stars: data.stargazers_count };
  } catch {
    return { stars: 0 };
  }
}
