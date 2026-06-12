# Unit 05 — Content Collections & the Content Layer

## What you will learn

- Define a content collection with a Zod schema for compile-time type safety
- Use the `glob` loader to load Markdown files from the filesystem
- Query collections with `getCollection()`, filter, and sort entries
- Render a collection entry's body with `render()`
- Generate dynamic routes for every collection entry (connecting `getStaticPaths()` from Unit 02)
- Understand Astro v5's Content Layer API and when to use a remote loader

## Why this unit exists

Hard-coding content in `getStaticPaths()` doesn't scale. Content Collections are the correct Astro pattern for any site with repeating content — blog posts, docs pages, team members, products. Without this unit, you'll reach for third-party CMSs prematurely or hand-manage JSON arrays.

---

## 1. What Is a Content Collection?

A content collection is a set of content files (Markdown, MDX, JSON, YAML, or remote data) wired to:

- A **schema** — a Zod definition of every entry's fields, so you get TypeScript errors on bad frontmatter rather than silent `undefined`s at runtime
- A **loader** — how Astro fetches the entries (filesystem glob, `fetch()` call, CMS API)
- A **query API** — `getCollection()`, `getEntry()`, `render()`

Before Astro v5, collections lived in `src/content/` and were always filesystem-bound. Astro v5's **Content Layer API** decouples the loader from Vite's module graph, enabling build-time caching, incremental updates, and remote data sources.

---

## 2. Defining a Collection

Collections are configured in `src/content.config.ts` (Astro v5 convention):

```ts
// src/content.config.ts
import { defineCollection, z } from 'astro:content'
import { glob } from 'astro/loaders'

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/data/blog' }),
  schema: z.object({
    title:       z.string(),
    pubDate:     z.coerce.date(),           // coerce "2025-01-15" string → Date
    description: z.string().optional(),
    draft:       z.boolean().default(false),
    tags:        z.array(z.string()).default([]),
  }),
})

export const collections = { blog }
```

Zod validates every entry's frontmatter at build time. A missing `title` surfaces as a clear schema error during `npm run build` — not a silent `undefined` on the live site.

> **v4 note:** If you're on Astro v4, use `src/content/config.ts` and `type: 'content'` instead of a `loader`. In v4, `render()` was a method on the entry (`entry.render()`). In v5 it's a top-level import from `astro:content`. See the [migration guide](https://docs.astro.build/en/guides/upgrade-to/v5/) if you're upgrading.

---

## 3. Adding Content Files

Create Markdown files in the directory the `glob` loader watches:

```
src/data/blog/
├── hello-world.md
├── second-post.md
└── draft-post.md
```

Each file's frontmatter must satisfy the Zod schema:

```markdown
---
title: Hello, World!
pubDate: 2025-01-15
description: My first Astro post.
tags: [astro, web]
---

This is the body of the post in **Markdown**.

You can use any Markdown syntax here, including ## headings, `code`, and links.
```

The filename (without extension) becomes the entry's `id` — `hello-world`. The body (everything after the closing `---`) is stored separately and rendered on demand.

---

## 4. Querying Collections

```astro
---
// src/pages/blog/index.astro
import { getCollection } from 'astro:content'

const allPosts = await getCollection('blog')
// → CollectionEntry<'blog'>[]
//   each entry: { id, data, body, ... }

// Filter out drafts — data.draft is typed boolean, not any
const published = allPosts.filter(p => !p.data.draft)

// Sort newest first — data.pubDate is typed Date
published.sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
---

<ul>
  {published.map(post => (
    <li>
      <a href={`/blog/${post.id}`}>{post.data.title}</a>
      <time datetime={post.data.pubDate.toISOString()}>
        {post.data.pubDate.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
      </time>
    </li>
  ))}
</ul>
```

`post.data` is fully typed. Hover over `post.data.title` in VS Code — you'll see `string`. Misspell a field and TypeScript catches it before the build runs.

---

## 5. Generating Dynamic Pages from a Collection

Connect `getCollection()` to `getStaticPaths()` (from Unit 02) to generate one HTML page per entry:

```astro
---
// src/pages/blog/[id].astro
import { getCollection, render } from 'astro:content'
import BlogPost from '../../layouts/BlogPost.astro'

export async function getStaticPaths() {
  const posts = await getCollection('blog', ({ data }) => !data.draft)
  return posts.map(post => ({
    params: { id: post.id },
    props:  { post },
  }))
}

// Type the props — CollectionEntry<'blog'> carries full type inference
import type { CollectionEntry } from 'astro:content'
interface Props { post: CollectionEntry<'blog'> }

const { post } = Astro.props
const { Content, headings } = await render(post)
// Content  → a component that outputs the rendered Markdown HTML
// headings → array of { depth, slug, text } — useful for a ToC
---

<BlogPost title={post.data.title} pubDate={post.data.pubDate}>
  <Content />
</BlogPost>
```

`render()` converts the stored Markdown body into a renderable `Content` component. Use `<Content />` exactly like any other Astro component.

> **The `getStaticPaths()` + `getCollection()` pattern is the canonical Astro way to build content-driven sites.** It pre-generates every content page at build time — one HTML file per entry, no server needed.

---

## 6. The Content Layer — Remote Data

Astro v5's Content Layer accepts any async loader, not just filesystem globs. This example fetches from a REST API:

```ts
// src/content.config.ts
import { defineCollection, z } from 'astro:content'

const products = defineCollection({
  loader: async () => {
    const res  = await fetch('https://fakestoreapi.com/products')
    const data = await res.json() as Array<{ id: number; title: string; price: number }>
    // loader must return an array with a unique `id` field (string or number)
    return data
  },
  schema: z.object({
    title: z.string(),
    price: z.number(),
  }),
})

export const collections = { products }
```

The loader runs **at build time**. Results are cached on disk — on subsequent builds, Astro only re-fetches entries that changed (Astro v5 incremental caching). This makes remote-data builds fast even for large catalogs.

---

## Practical Exercises

1. **Blog collection.** Create `src/content.config.ts` with a `blog` collection using the `glob` loader. Define a schema for `title`, `pubDate`, `description`, and `draft`. Create three Markdown files in `src/data/blog/`. Mark one as `draft: true`.

2. **Listing page.** Build `src/pages/blog/index.astro` that renders a linked list of published posts sorted by date. Confirm draft filtering works: the draft file should not appear in the list.

3. **Dynamic detail pages.** Create `src/pages/blog/[id].astro`. Wire `getStaticPaths()` to your collection. Use `render()` and your `BlogPost` layout to display the full post. Run `npm run build` — confirm one HTML file per published Markdown file appears in `dist/blog/`.

4. **Schema validation.** Intentionally break one Markdown file's frontmatter (remove `title`). Run `npm run build` — read the Zod validation error. Restore it and note how early this surfaced compared to a runtime check.

---

## Self-Check

1. What does the `schema` in `defineCollection` buy you beyond documentation comments?
2. You call `getCollection('blog')` and access `entry.data.pubDate`. Where is `pubDate` coming from, and when was the schema validated?
3. In `getStaticPaths()` you return `props: { post }` where `post` is a `CollectionEntry`. Why is accessing `post.data.title` safe inside the page — what guarantees the data shape?

---

## Key Takeaways

- `defineCollection()` in `src/content.config.ts` wires a Zod schema to a loader.
- The `glob` loader maps a file-glob pattern to a directory of Markdown/MDX/JSON files.
- `getCollection()` returns fully typed entries; `entry.data` fields are inferred from the Zod schema.
- `render(entry)` converts a content entry's body to a `Content` component — use `<Content />` in your template.
- Connect `getCollection()` + `getStaticPaths()` to generate one page per content entry.
- The Content Layer (v5) supports any async loader — filesystem, `fetch()`, CMS — with build-time caching.

---

## Next

[Unit 06 — View Transitions & Enhancing Navigation →](../06-view-transitions/README.md)
