import type { APIRoute } from "astro";
import { getCollection } from "astro:content";

export const GET: APIRoute = async () => {
  const policies = (await getCollection("policies")).sort((a, b) =>
    a.data.title.localeCompare(b.data.title)
  );
  const blog = (await getCollection("blog"))
    .sort((a, b) => (b.data.date || "").localeCompare(a.data.date || ""));
  const events = (await getCollection("events")).sort((a, b) =>
    (a.data.date || "").localeCompare(b.data.date || "")
  );
  const team = (await getCollection("team")).sort((a, b) =>
    a.data.name.localeCompare(b.data.name)
  );

  const lines: string[] = [
    "# Opportunity Party — Documentation Site Map",
    "",
    "A plain-text, LLM-accessible mirror of the Opportunity Party website (opportunity.org.nz).",
    "",
    "## Section Maps",
    "",
    `- [Policies](/policies.md) — ${policies.length} policies`,
    `- [Blog](/blog.md) — ${blog.length} posts`,
    `- [Events](/events.md) — ${events.length} events`,
    `- [Team](/team.md) — ${team.length} members`,
    "",
    "## Individual Pages",
    "",
    "### Policies",
    "",
    ...policies.map((p) => `- [${p.data.title}](/policies/${p.data.slug}.md)`),
    "",
    "### Blog Posts",
    "",
    ...blog.map((b) => `- [${b.data.title}](/blog/${b.data.slug}.md)`),
    "",
    "### Events",
    "",
    ...events.map((e) => `- [${e.data.title}](/events/${e.data.slug}.md)`),
    "",
    "### Team Members",
    "",
    ...team.map((t) => `- [${t.data.name}](/team/${t.data.slug}.md)`),
  ];

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};