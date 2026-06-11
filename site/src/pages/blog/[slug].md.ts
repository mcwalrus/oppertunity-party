import type { APIRoute, GetStaticPaths } from "astro";
import { getCollection } from "astro:content";
import fs from "node:fs";
import path from "node:path";

export const getStaticPaths: GetStaticPaths = async () => {
  const posts = await getCollection("blog");
  return posts.map((p) => ({
    params: { slug: p.data.slug },
    props: { post: p },
  }));
};

export const GET: APIRoute = async ({ props }) => {
  const { post } = props as { post: any };
  const contentPath = path.join(process.cwd(), "src/content/blog", `${post.data.slug}.md`);
  const raw = fs.readFileSync(contentPath, "utf-8");
  const body = raw.replace(/^---\n[\s\S]*?\n---\n/, "");

  const lines: string[] = [
    `# ${post.data.title}`,
    "",
    post.data.date ? `**Date:** ${post.data.date}` : "",
    post.data.author ? `**Author:** ${post.data.author}` : "",
    "",
    body.trim(),
  ];

  return new Response(lines.join("\n"), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};