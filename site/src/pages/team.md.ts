import type { APIRoute } from "astro";
import { getCollection } from "astro:content";

export const GET: APIRoute = async () => {
  const team = (await getCollection("team")).sort((a, b) =>
    a.data.name.localeCompare(b.data.name)
  );

  const lines: string[] = [
    "# Opportunity Party — Team",
    "",
    `All ${team.length} team members.`,
    "",
  ];

  for (const member of team) {
    lines.push(
      `## ${member.data.name}`,
      "",
      member.data.role ? `**Role:** ${member.data.role}` : "",
      member.data.electorate ? `**Electorate:** ${member.data.electorate}` : "",
      ""
    );
  }

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};