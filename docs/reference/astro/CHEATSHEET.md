# Astro Cheatsheet

Single-page reference for day-to-day Astro development.

---

# ── SETUP ──

```bash
# Create a new project (interactive wizard)
npm create astro@latest my-site

# Dev server — hot reload at http://localhost:4321
npm run dev

# Build for production → dist/
npm run build

# Preview the production build locally
npm run preview

# Type-check the whole project
npx astro check

# Print debug info (version, integrations, adapter)
npx astro info

# Add integrations (installs packages + updates astro.config.mjs)
npx astro add react
npx astro add vue
npx astro add tailwind
npx astro add mdx
npx astro add sitemap
npx astro add partytown

# Add SSR adapters
npx astro add vercel
npx astro add netlify
npx astro add cloudflare
npx astro add node

# Re-generate content collection types after schema changes
npx astro sync
```

---

# ── .ASTRO COMPONENT TEMPLATE ──

```astro
---
// Frontmatter — runs at build time (Node.js). NEVER in the browser.
// window / document are not available here.

interface Props {
  title: string
  count?: number
}

const { title, count = 0 } = Astro.props

// Fetch data — runs once at build time
const data = await fetch('https://api.example.com/items').then(r => r.json())
---

<!-- Template — outputs static HTML. Expressions use {single} braces. -->
<article>
  <h1>{title}</h1>
  <p>Count: {count}</p>

  <!-- Conditionals -->
  {count > 0 && <p>Items found!</p>}

  <!-- Lists -->
  <ul>
    {data.map((item: any) => <li>{item.name}</li>)}
  </ul>
</article>

<style>
  /* Auto-scoped to this component — selectors won't leak */
  article { padding: 1rem; }
</style>

<script>
  /* Runs in the browser. Not scoped, but Astro deduplicates it. */
  /* Re-add astro:page-load listener if using <ClientRouter /> */
  console.log('loaded')
</script>
```

---

# ── ROUTING ──

```
src/pages/index.astro           → /
src/pages/about.astro           → /about
src/pages/blog/index.astro      → /blog
src/pages/blog/[slug].astro     → /blog/:slug          (dynamic)
src/pages/[cat]/[slug].astro    → /:cat/:slug          (multi-segment)
src/pages/docs/[...path].astro  → /docs, /docs/a/b/c  (rest param)
src/pages/404.astro             → custom 404 page
src/pages/api/hello.ts          → /api/hello           (HTTP endpoint)
```

### Dynamic route pattern

```astro
---
export function getStaticPaths() {
  return [
    { params: { slug: 'hello' }, props: { title: 'Hello', views: 42 } },
    { params: { slug: 'world' }, props: { title: 'World', views: 7  } },
  ]
}

interface Props { title: string; views: number }

const { slug }         = Astro.params    // from params
const { title, views } = Astro.props     // from props
---

<h1>{title} — {slug}</h1>
```

---

# ── LAYOUTS ──

```astro
---
// src/layouts/Base.astro
interface Props { title: string }
const { title } = Astro.props
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>{title}</title>
    <slot name="head" />    <!-- named slot: inject extra <head> content -->
  </head>
  <body>
    <slot />                <!-- default slot: main page content -->
    <footer>
      <slot name="footer">
        <p>© 2025 My Site</p>   <!-- fallback if no footer slot provided -->
      </slot>
    </footer>
  </body>
</html>
```

```astro
---
import Base from '../layouts/Base.astro'
---

<Base title="My Page">
  <meta slot="head" name="description" content="Page description" />
  <h1>Page content here</h1>
</Base>
```

### Markdown layout (via frontmatter)

```markdown
---
layout: ../layouts/BlogPost.astro
title: My Post
pubDate: 2025-01-01
---

Post body in **Markdown**.
```

---

# ── CLIENT DIRECTIVES (ISLANDS) ──

```astro
<!-- No directive = static HTML only, zero JS shipped -->
<Counter />

<!-- Hydration strategies -->
<Counter client:load />                          <!-- immediately on page load -->
<Counter client:idle />                          <!-- after requestIdleCallback -->
<Counter client:visible />                       <!-- when scrolled into viewport -->
<Counter client:media="(max-width: 768px)" />    <!-- when media query matches -->
<Counter client:only="react" />                  <!-- client render only, no SSR -->
```

### When to use which directive

| Directive | Use case |
|---|---|
| `client:load` | Critical UI, above the fold, must be interactive on first paint |
| `client:idle` | Secondary widgets — share buttons, newsletter forms |
| `client:visible` | Heavy below-fold widgets — charts, comment sections |
| `client:media` | UI that only matters at a specific breakpoint |
| `client:only` | Components using `window`, `localStorage`, browser-only APIs |

**Island props must be JSON-serializable.** No functions, no class instances, no `Map`/`Set`.

---

# ── CONTENT COLLECTIONS ──

```ts
// src/content.config.ts
import { defineCollection, z } from 'astro:content'
import { glob } from 'astro/loaders'

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/data/blog' }),
  schema: z.object({
    title:       z.string(),
    pubDate:     z.coerce.date(),
    description: z.string().optional(),
    draft:       z.boolean().default(false),
    tags:        z.array(z.string()).default([]),
  }),
})

export const collections = { blog }
```

```astro
---
import { getCollection, render } from 'astro:content'
import type { CollectionEntry }  from 'astro:content'

// List all entries (filter + sort)
const posts = (await getCollection('blog'))
  .filter(p => !p.data.draft)
  .sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())

// Generate pages — in [id].astro
export async function getStaticPaths() {
  const posts = await getCollection('blog', ({ data }) => !data.draft)
  return posts.map(post => ({
    params: { id: post.id },
    props:  { post },
  }))
}

interface Props { post: CollectionEntry<'blog'> }
const { post } = Astro.props
const { Content, headings } = await render(post)
// headings → [{ depth, slug, text }] — for a table of contents
---

<Content />
```

### Remote loader (Content Layer API — v5)

```ts
const products = defineCollection({
  loader: async () => {
    const items = await fetch('https://api.example.com/products').then(r => r.json())
    return items   // must be Array<{ id: string | number, ...fields }>
  },
  schema: z.object({ title: z.string(), price: z.number() }),
})
```

---

# ── VIEW TRANSITIONS ──

```astro
---
// Add once to base layout <head>
import { ClientRouter } from 'astro:transitions'
import { fade, slide }  from 'astro:transitions'
---

<ClientRouter />

<!-- Animate an element on every navigation -->
<main transition:animate="fade">…</main>
<nav  transition:animate="slide">…</nav>
<main transition:animate={fade({ duration: '0.3s' })}>…</main>

<!-- Morph element between pages (same name on both pages) -->
<img src={cover} transition:name={`hero-${post.id}`} />

<!-- Persist DOM node (and JS state) across navigations -->
<audio src="/podcast.mp3" transition:persist />
<ThemeToggle client:load transition:persist="theme-toggle" />
```

```js
// Re-run scripts after every navigation (replaces DOMContentLoaded)
document.addEventListener('astro:page-load', () => {
  // re-initialize syntax highlighting, tooltips, scroll listeners, etc.
})
```

```css
/* Respect prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(root),
  ::view-transition-new(root) { animation: none; }
}
```

---

# ── RENDERING MODES & ADAPTERS ──

```ts
// astro.config.mjs
import { defineConfig } from 'astro/config'
import vercel from '@astrojs/vercel'

export default defineConfig({
  output: 'hybrid',   // 'static' | 'server' | 'hybrid'
  adapter: vercel(),  // required for server / hybrid
})
```

```astro
<!-- hybrid mode: opt this page into server rendering -->
---
export const prerender = false
---

<!-- server mode: opt this page back into static pre-rendering -->
---
export const prerender = true
---
```

### When to use which output mode

| Scenario | Mode |
|---|---|
| Blog, docs, marketing site — all content is static | `static` (default) |
| Mostly static with a few dynamic pages (auth, API) | `hybrid` |
| User-specific pages on every route (dashboard, app) | `server` |

---

# ── API ROUTES (ENDPOINTS) ──

```ts
// src/pages/api/items.ts
import type { APIRoute } from 'astro'

export const GET: APIRoute = ({ url }) => {
  const id = url.searchParams.get('id')
  return new Response(JSON.stringify({ id }), {
    headers: { 'Content-Type': 'application/json' },
  })
}

export const POST: APIRoute = async ({ request }) => {
  const body = await request.json()
  if (!body.name) {
    return new Response(JSON.stringify({ error: 'name required' }), { status: 400 })
  }
  return new Response(JSON.stringify({ ok: true }), { status: 201 })
}
```

---

# ── ENVIRONMENT VARIABLES ──

```bash
# .env — add to .gitignore
SECRET_KEY=abc123          # server-only (stripped from client bundles)
PUBLIC_SITE=My Site        # client-safe (visible in browser JS)
```

```ts
import.meta.env.SECRET_KEY          // server & build time only
import.meta.env.PUBLIC_SITE         // everywhere, including client islands
import.meta.env.PROD                // boolean — true in production
import.meta.env.DEV                 // boolean — true in dev server
```

---

# ── COMMON GOTCHAS ──

| Symptom | Likely cause |
|---|---|
| Component renders but clicks do nothing | Missing `client:*` directive — component is static HTML, no JS hydration |
| `window is not defined` at build time | Code in frontmatter (or no `client:only`) accesses browser APIs |
| Island prop silently `undefined` | Prop is not JSON-serializable (function, class instance, `Map`) |
| `getStaticPaths() required` build error | Dynamic `[param].astro` is missing the `getStaticPaths()` export |
| Styles bleeding into other components | Using `<style is:global>` instead of a plain (scoped) `<style>` |
| `astro:page-load` never fires | `<ClientRouter />` not added to the base layout's `<head>` |
| View Transitions work in dev, broken in prod | `<ClientRouter />` must appear in **every** page's `<head>` (put it in the layout) |
| `SECRET_KEY` is `undefined` in a client island | Non-`PUBLIC_` env vars are stripped from browser bundles — use `PUBLIC_` prefix or fetch from an API route |
| Type error on `entry.data.field` | Schema changed but types not regenerated — run `npx astro sync` |
| `getCollection()` returns 0 entries | `glob` loader `base` path or `pattern` doesn't match the actual file locations |
| Script only runs on first page load | Script listens on `DOMContentLoaded` — switch to `astro:page-load` when using `<ClientRouter />` |

---

# ── DECISION TABLE: WHEN TO USE WHAT ──

| Scenario | Solution |
|---|---|
| Global nav, footer, `<head>` setup | Layout component in `src/layouts/` |
| Repeating UI (card, button, badge, callout) | Component in `src/components/` |
| Repeating content (posts, docs, products, team) | Content Collection in `src/content.config.ts` |
| Interactive widget (counter, form, dropdown) | Framework component + `client:*` directive |
| Audio/video that keeps playing across pages | `transition:persist` on the media element |
| Animated page-to-page navigation | `<ClientRouter />` + `transition:animate` |
| Page with user-specific or real-time data | `export const prerender = false` (hybrid mode) |
| Third-party analytics / ads script | `@astrojs/partytown` (moves script to Web Worker) |
| Auto-generated sitemap | `@astrojs/sitemap` integration |
| Markdown with embedded React/Vue components | `@astrojs/mdx` integration (`.mdx` files) |
