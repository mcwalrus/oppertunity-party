# Unit 07 — Integrations, SSR Modes & Deployment

## What you will learn

- Add official and community integrations with `npx astro add`
- Understand the three output modes: `static`, `server`, and `hybrid`
- Install an SSR adapter and configure on-demand rendering
- Create API routes (endpoints) that handle HTTP methods
- Use `export const prerender` to mix static and dynamic pages in hybrid mode
- Deploy to Vercel, Netlify, Cloudflare, and self-hosted Node.js

## Why this unit exists

Most real projects need at least one server-rendered page — a contact form handler, a gated dashboard, an API endpoint. This unit is where Astro's "zero-JS by default" meets the real world. Understanding the three output modes and when to choose each is the difference between over-engineering a simple blog and under-engineering a data-driven app.

---

## 1. Integrations

Astro integrations extend the build: UI frameworks, CSS processors, sitemaps, image optimisation, and more. The CLI makes adding them one command:

```bash
npx astro add react         # → @astrojs/react (+ peer deps)
npx astro add tailwind      # → @astrojs/tailwind
npx astro add sitemap       # → @astrojs/sitemap
npx astro add mdx           # → @astrojs/mdx (Markdown + JSX in .mdx files)
npx astro add partytown     # → @astrojs/partytown (offload third-party scripts to a Web Worker)
npx astro add db            # → @astrojs/db (Astro DB — edge SQL)
```

Each command installs the package **and** updates `astro.config.mjs` automatically. Manually wiring integrations is discouraged — `astro add` handles peer-dependency resolution and config generation.

Check what's installed:

```bash
npx astro info
# → lists integrations, adapter, Astro version, Node version
```

---

## 2. Rendering Modes

Set in `astro.config.mjs`:

```ts
// astro.config.mjs
import { defineConfig } from 'astro/config'

export default defineConfig({
  output: 'static',   // default
  // output: 'server',
  // output: 'hybrid',
})
```

| Mode | Default behaviour | Use when |
|---|---|---|
| `static` | All pages pre-rendered to HTML at build time | Blogs, docs, marketing — content doesn't vary by user or request |
| `server` | All pages server-rendered on every request | Dashboards, user-specific pages — most content is dynamic |
| `hybrid` | Static by default; individual pages opt in to server rendering | Most real apps — mostly static with a handful of dynamic pages |

> **Recommendation (grounded in Astro docs):** Start with `static`. Switch to `hybrid` when you need a specific page to be dynamic (e.g., `/dashboard`, `/api/*`). Reach for `server` only when the **majority** of your pages are user-specific or real-time.

---

## 3. SSR Adapters

`server` and `hybrid` modes require an **adapter** — the bridge between Astro's server runtime and your deployment platform:

```bash
npx astro add vercel      # → @astrojs/vercel (Vercel Edge Functions / Serverless)
npx astro add netlify     # → @astrojs/netlify (Netlify Functions)
npx astro add cloudflare  # → @astrojs/cloudflare (Cloudflare Workers)
npx astro add node        # → @astrojs/node (standalone Node.js HTTP server)
```

```ts
// astro.config.mjs — example with Vercel adapter
import { defineConfig } from 'astro/config'
import vercel from '@astrojs/vercel'

export default defineConfig({
  output: 'hybrid',
  adapter: vercel(),
})
```

Each adapter produces the right build artifact: Vercel output configuration, a Netlify Functions bundle, a Cloudflare Worker script, or a standalone Node server entry point.

---

## 4. Server-Rendered Pages & the `prerender` Flag

In `hybrid` mode, pages are static by default. Opt a single page into server rendering:

```astro
---
// src/pages/dashboard.astro
export const prerender = false   // render this page on every request

// Access request-specific data
const cookie  = Astro.cookies.get('session')?.value
if (!cookie) return Astro.redirect('/login')

const user = await fetchUserFromDB(cookie)
---

<h1>Welcome back, {user.name}</h1>
<p>Your last login: {user.lastLogin}</p>
```

In `server` mode, the flag is reversed — everything server-renders by default; opt a page back into static pre-rendering:

```astro
export const prerender = true   // build this page at build time, not on request
```

| Mode | Default | Override with |
|---|---|---|
| `hybrid` | static | `export const prerender = false` |
| `server` | server | `export const prerender = true` |

---

## 5. API Routes (Endpoints)

`.ts` (or `.js`) files under `src/pages/` become HTTP endpoints when they export method handlers. No Express, no separate server needed:

```ts
// src/pages/api/subscribe.ts
import type { APIRoute } from 'astro'

export const POST: APIRoute = async ({ request }) => {
  const body = await request.json() as { email?: string }

  if (!body.email) {
    return new Response(JSON.stringify({ error: 'Email required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // save to DB, call email provider, etc.

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

// You can export GET, POST, PUT, DELETE, PATCH on the same file
export const GET: APIRoute = ({ url }) => {
  const q = url.searchParams.get('q') ?? ''
  return new Response(JSON.stringify({ query: q }), {
    headers: { 'Content-Type': 'application/json' },
  })
}
```

Calling it from a client island:

```tsx
// src/components/SubscribeForm.tsx
async function handleSubmit(email: string) {
  const res  = await fetch('/api/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  const json = await res.json()
  // handle response
}
```

> **In `static` mode:** endpoints that export only `GET` can be pre-rendered to a static file (e.g., a JSON feed or RSS). Endpoints that must respond to `POST` require `server` or `hybrid` mode.

---

## 6. Environment Variables

```bash
# .env (never commit to git — add to .gitignore)
SECRET_API_KEY=abc123          # server-only — never sent to the browser
PUBLIC_ANALYTICS_ID=GA-123456  # client-safe — prefix with PUBLIC_ to expose
```

```ts
// Accessible anywhere (server-side code: frontmatter, API routes, getStaticPaths)
const key = import.meta.env.SECRET_API_KEY

// Accessible in client islands too (PUBLIC_ prefix required)
const id  = import.meta.env.PUBLIC_ANALYTICS_ID

// Built-in boolean flags
const isProd = import.meta.env.PROD    // true in production build
const isDev  = import.meta.env.DEV     // true during dev server
```

Non-`PUBLIC_` variables are stripped from client bundles by Vite. Accessing `SECRET_API_KEY` inside a React island returns `undefined` — not an error. This is a common silent bug.

---

## 7. Deployment

### Static output (default)

```bash
npm run build    # → dist/  — all static HTML, CSS, JS assets
```

Upload `dist/` to any static host:

| Host | How to deploy |
|---|---|
| **Vercel** | Connect your Git repo at vercel.com — zero config for static |
| **Netlify** | Connect your repo at app.netlify.com — auto-detects Astro |
| **Cloudflare Pages** | Connect your repo in the Cloudflare dashboard |
| **GitHub Pages** | Push `dist/` to the `gh-pages` branch |
| **AWS S3 + CloudFront** | Sync `dist/` to a bucket, point CloudFront at it |

### Server / hybrid output (with adapter)

After installing an adapter, the build output includes a server entry point:

```bash
npm run build
# → dist/           (static assets)
# → dist/server/    (server bundle — shape varies by adapter)

# Self-hosted Node.js:
node dist/server/entry.mjs    # → starts HTTP server on PORT (default 4321)
```

For Vercel, Netlify, and Cloudflare Pages: connect your repo in their dashboards. They detect the adapter and handle the rest — no extra configuration.

---

## Practical Exercises

1. **Add Tailwind.** Run `npx astro add tailwind`. Add Tailwind utility classes to a component. Run `npm run build && npm run preview` — confirm the production build renders the classes correctly.

2. **Static API route.** Create `src/pages/api/hello.ts` that exports a `GET` handler returning `{ message: "Hello, world!" }` as JSON. Fetch it in a page's frontmatter (`await fetch('/api/hello').then(r => r.json())`) and display the result. In `static` mode, this runs at build time.

3. **Hybrid mode + server page.** Add `@astrojs/node` adapter, set `output: 'hybrid'`. Create `src/pages/time.astro` with `export const prerender = false`. Return the current server timestamp (`new Date().toISOString()`). Run the built server with `node dist/server/entry.mjs` — refresh `/time` multiple times and confirm the timestamp changes.

4. **Environment variables.** Add `PUBLIC_SITE_NAME="My Astro Site"` to `.env`. Use it in your base layout's `<title>`. Then add `SECRET_KEY=hunter2` and try to access it inside a React island — observe it is `undefined` in the browser.

---

## Self-Check

1. Your project is a 200-post blog with one `/dashboard` page that requires authentication. Which `output` mode do you choose, and what flag goes on the dashboard page?
2. What does an SSR adapter do? Why is it required for `server` or `hybrid` output but not for `static`?
3. A teammate's `SECRET_API_KEY` is `undefined` inside their React island. Why? How do you fix it, and what are the security implications?

---

## Key Takeaways

- `npx astro add <name>` installs and configures any integration — including SSR adapters — in one command.
- `output: 'static'` pre-renders everything; `'server'` renders everything on request; `'hybrid'` mixes both.
- Adapters (`vercel`, `netlify`, `cloudflare`, `node`) target a specific server runtime — required for `server` / `hybrid` output.
- In `hybrid` mode, `export const prerender = false` opts a page into server rendering; in `server` mode, `export const prerender = true` opts it back to static.
- `.ts` files under `src/pages/` are HTTP endpoints — export `GET`, `POST`, `PUT`, etc.
- Variables without the `PUBLIC_` prefix are server-only and are stripped from client bundles.
