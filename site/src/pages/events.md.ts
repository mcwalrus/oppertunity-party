import type { APIRoute } from "astro";
import { getCollection } from "astro:content";

export const GET: APIRoute = async () => {
  const events = (await getCollection("events")).sort((a, b) =>
    (a.data.date || "").localeCompare(b.data.date || "")
  );

  const lines: string[] = [
    "# Opportunity Party — Events",
    "",
    `All ${events.length} events from the Opportunity Party.`,
    "",
  ];

  for (const ev of events) {
    lines.push(
      `## [${ev.data.title}](/events/${ev.data.slug})`,
      "",
      ev.data.when ? `**When:** ${ev.data.when}` : "",
      ev.data.venue ? `**Venue:** ${ev.data.venue}` : "",
      ev.data.address ? `**Address:** ${ev.data.address}` : "",
      ""
    );
  }

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};