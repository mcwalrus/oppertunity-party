# Unit 02 — File-Based Routing & Pages

## What you will learn

- Map filesystem paths to URLs — the full routing contract
- Build nested routes with subdirectories under `src/pages/`
- Create dynamic routes with `[param]` syntax and `getStaticPaths()`
- Pass data to generated pages via `props` in `getStaticPaths()`
- Use rest-parameter routes (`[...path]`) for catch-all segments
- Provide a custom 404 page

## Why this unit exists

Routing is how content reaches users. Astro's file-based router means there is no config file to maintain — the filesystem IS the config. This unit establishes the full routing contract before you add dynamic content in Unit 05. If you skip it, `getStaticPaths()` in Unit 05 will be a mystery.

---

## 1. Static Routes

Every `.astro` (or `.md`, `.html`) file under `src/pages/` maps directly to a URL:

```
src/pages/index.astro       → /
src/pages/about.astro       → /about
src/pages/contact.astro     → /contact
src/pages/blog/index.astro  → /blog
src/pages/blog/hello.astro  → /blog/hello
```

No configuration. No `<Route path="..." />`. The path in the filesystem IS the URL path.

> **Analogy to Apache/Nginx static file hosting:** same idea — file path = URL path — except Astro compiles `.astro` files to HTML rather than serving them raw.

---

## 2. Pages Are Full HTML Documents

A page file is an `.astro` component that provides its own HTML shell:

```astro
---
// src/pages/about.astro
const title = "About"
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>{title}</title>
  </head>
  <body>
    <h1>About me</h1>
    <p>Hello from the about page.</p>
  </body>
</html>
```

Without the full HTML shell, Astro builds a bare HTML fragment — fine for partials, but not for navigable pages. In Unit 03 you'll extract this shell into a **Layout** component so you don't repeat it on every page.

---

## 3. Dynamic Routes — `[param].astro`

For routes where the path segment is variable (e.g. `/blog/my-post`), use bracket syntax:

```
src/pages/blog/[slug].astro   → /blog/:slug
```

Because Astro renders everything at build time by default, it needs to know **all possible values** of `[slug]` before the build runs. Provide them with `getStaticPaths()`:

```astro
---
// src/pages/blog/[slug].astro
export function getStaticPaths() {
  return [
    { params: { slug: "hello-world" } },
    { params: { slug: "second-post" } },
  ]
}

const { slug } = Astro.params
---

<!doctype html>
<html>
  <body>
    <h1>Post: {slug}</h1>
  </body>
</html>
```

At build time, Astro calls `getStaticPaths()`, collects every `{ params }` object, and generates one HTML file per entry:

```
dist/blog/hello-world/index.html
dist/blog/second-post/index.html
```

---

## 4. Passing Data to Dynamic Pages

Return a `props` key alongside `params` to pre-load page data at build time — no second fetch needed:

```astro
---
// src/pages/blog/[slug].astro
export function getStaticPaths() {
  return [
    { params: { slug: "hello-world" }, props: { title: "Hello, World!", views: 42 } },
    { params: { slug: "second-post" }, props: { title: "Second Post",   views: 11 } },
  ]
}

interface Props {
  title: string
  views: number
}

const { slug }         = Astro.params
const { title, views } = Astro.props
---

<h1>{title}</h1>
<p>slug: {slug} — views: {views}</p>
```

> **Why pass props here instead of fetching in frontmatter?** `getStaticPaths()` runs once per build; the props it returns are available to every page instance without an extra fetch per page. For large datasets this is significantly faster.

---

## 5. Multiple Dynamic Segments

Nest brackets for multiple variable path segments:

```
src/pages/[category]/[slug].astro   → /:category/:slug
```

```astro
---
export function getStaticPaths() {
  return [
    { params: { category: "news",   slug: "breaking"   } },
    { params: { category: "guides", slug: "beginners"  } },
  ]
}

const { category, slug } = Astro.params
---

<p>{category} / {slug}</p>
<!-- → news / breaking -->
```

---

## 6. Rest-Parameter Routes — `[...path].astro`

A `[...path]` segment matches **any number** of path segments, including zero:

```
src/pages/docs/[...path].astro   → /docs, /docs/intro, /docs/api/reference, …
```

```astro
---
export function getStaticPaths() {
  return [
    { params: { path: undefined        } },   // → /docs
    { params: { path: "intro"          } },   // → /docs/intro
    { params: { path: "api/reference"  } },   // → /docs/api/reference
  ]
}

const { path } = Astro.params   // undefined | string
---

<p>Docs path: {path ?? "(root)"}</p>
```

---

## 7. Custom 404 Page

Create `src/pages/404.astro` — Astro serves it for any unmatched URL in both dev and production:

```astro
---
// src/pages/404.astro
---

<!doctype html>
<html>
  <body>
    <h1>Page not found</h1>
    <a href="/">← Back home</a>
  </body>
</html>
```

---

## Practical Exercises

1. **Static multi-page site.** Add `src/pages/about.astro` and `src/pages/contact.astro` to your project. Run `npm run dev` and navigate to `/about` and `/contact`. Confirm they render.

2. **Dynamic route.** Create `src/pages/posts/[id].astro`. Hard-code three entries in `getStaticPaths()` with `id: "1"`, `"2"`, `"3"`. Pass a `title` prop from each entry and render it. Run `npm run build` and inspect `dist/posts/` — confirm three folders were created.

3. **Props from `getStaticPaths`.** Extend the previous exercise: add a `body` prop (a short string). Render both `title` and `body` on the page. Verify that TypeScript errors if you forget the `interface Props` declaration.

4. **404 page.** Create `src/pages/404.astro` with a friendly message and a link back to `/`. Navigate to `/does-not-exist` in dev mode — confirm it renders your custom page, not the default Astro 404.

---

## Self-Check

1. What file would you create to handle the URL `/products/gadgets/wireless-earbuds`? Write the exact path using bracket syntax and a `getStaticPaths()` call that returns one entry for it.
2. Why does Astro require `getStaticPaths()` for dynamic routes in static mode? What would happen at build time if you omit it?
3. What is the difference between `[slug].astro` and `[...slug].astro`?

---

## Key Takeaways

- File path under `src/pages/` = URL path. No router config file needed.
- Dynamic segments use `[param]` brackets; rest segments use `[...param]`.
- `getStaticPaths()` tells Astro every URL it must generate — required for dynamic routes in static mode.
- Return `props` alongside `params` in `getStaticPaths()` to pre-load page data at build time.
- `src/pages/404.astro` is the convention for custom error pages.

---

## Next

[Unit 03 — Layouts & Reusable Structure →](../03-layouts/README.md)
