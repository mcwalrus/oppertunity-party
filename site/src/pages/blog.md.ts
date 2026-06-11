import type { APIRoute } from "astro";
import { getCollection } from "astro:content";
import fs from "node:fs";
import path from "node:path";

export const GET: APIRoute = async () => {
  const posts = (await getCollection("blog"))
    .sort((a, b) => (b.data.date || "").localeCompare(a.data.date || ""));

  const lines: string[] = [
    "# Opportunity Party — Blog",
    "",
    `All ${posts.length} blog posts from the Opportunity Party.`,
    "",
  ];

  for (const post of posts) {
    const contentPath = path.join(process.cwd(), "src/content/blog", `${post.data.slug}.md`);
    const raw = fs.readFileSync(contentPath, "utf-8");
    const body = raw.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
    const summary = getSummary(body, 100);
    lines.push(
      `## ${post.data.date || "No date"} ${post.data.title}`,
      "",
      post.data.author ? `By ${post.data.author}` : "",
      summary,
      ""
    );
  }

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};

function getSummary(text: string, maxWords: number): string {
  const plain = text
    .replace(/^#+\s+/gm, "")
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^[>-]\s*/gm, "")
    .trim();

  const words = plain.split(/\s+/);
  return words.slice(0, maxWords).join(" ") + (words.length > maxWords ? "…" : "");
}