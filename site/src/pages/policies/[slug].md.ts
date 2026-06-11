import type { APIRoute, GetStaticPaths } from "astro";
import { getCollection } from "astro:content";
import fs from "node:fs";
import path from "node:path";

export const getStaticPaths: GetStaticPaths = async () => {
  const policies = await getCollection("policies");
  return policies.map((p) => ({
    params: { slug: p.data.slug },
    props: { policy: p },
  }));
};

export const GET: APIRoute = async ({ props }) => {
  const { policy } = props as { policy: any };
  // Read the raw markdown file from content dir
  const contentPath = path.join(process.cwd(), "src/content/policies", `${policy.data.slug}.md`);
  const raw = fs.readFileSync(contentPath, "utf-8");
  // Strip YAML frontmatter
  const body = raw.replace(/^---\n[\s\S]*?\n---\n/, "");

  const lines: string[] = [
    `# ${policy.data.title}`,
    "",
    body.trim(),
  ];

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};