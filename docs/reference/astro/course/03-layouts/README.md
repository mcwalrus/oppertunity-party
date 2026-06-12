# Unit 03 — Layouts & Reusable Structure

## What you will learn

- Extract a reusable HTML shell into a Layout component
- Pass page metadata (title, description) to layouts via props
- Use named slots for `<head>` content and other layout zones
- Provide slot fallback content
- Compose layouts by nesting one inside another
- Declare a layout in Markdown frontmatter

## Why this unit exists

In Unit 02 every page wrote its own `<!doctype html>` shell. That is duplicated structure — change the global font and you edit every file. Layouts fix this. They are the load-bearing pattern for every real Astro project and the prerequisite for understanding how pages and content entries get rendered in Unit 05.

---

## 1. A Layout Is Just a Component with a `<slot />`

A layout provides the page shell and renders its children via `<slot />`:

```astro
---
// src/layouts/Base.astro
interface Props {
  title: string
}

const { title } = Astro.props
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width" />
    <title>{title}</title>
  </head>
  <body>
    <slot />   <!-- page content goes here -->
  </body>
</html>
```

Any page can now use it:

```astro
---
// src/pages/about.astro
import Base from '../layouts/Base.astro'
---

<Base title="About">
  <h1>About me</h1>
  <p>Hello from the about page.</p>
</Base>
<!-- → one full HTML document, no duplication -->
```

Astro inserts the children exactly where `<slot />` sits. Change the `<head>` in `Base.astro` once and every page picks it up.

---

## 2. Named Slots in Layouts

Sometimes a page needs to inject content into the `<head>` — extra meta tags, canonical URLs, OG images — but `<head>` lives inside the layout. Named slots solve this:

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
    <slot name="head" />     <!-- pages inject extra head tags here -->
  </head>
  <body>
    <slot />                 <!-- main page content -->
  </body>
</html>
```

A page targets the named slot with `slot="head"`:

```astro
---
import Base from '../layouts/Base.astro'
---

<Base title="Blog Post">
  <meta slot="head" name="description" content="My first post." />
  <link slot="head" rel="canonical" href="https://example.com/blog/first" />

  <h1>My first post</h1>
</Base>
```

The `<meta>` and `<link>` land inside `<head>`; the `<h1>` lands in `<body>`.

---

## 3. Slot Fallback Content

Provide default content for a slot — rendered when the parent passes nothing:

```astro
<footer>
  <slot name="footer">
    <p>© 2025 My Site</p>   <!-- shown if no footer content is passed -->
  </slot>
</footer>
```

---

## 4. Nested Layouts

A specialized layout can itself use a base layout. This is the standard composition pattern:

```astro
---
// src/layouts/BlogPost.astro
import Base from './Base.astro'

interface Props {
  title: string
  pubDate: Date
}

const { title, pubDate } = Astro.props
---

<Base title={title}>
  <article>
    <h1>{title}</h1>
    <time datetime={pubDate.toISOString()}>
      {pubDate.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
    </time>
    <slot />   <!-- blog post body goes here -->
  </article>
</Base>
```

A blog page uses `BlogPost` instead of `Base` directly:

```astro
---
import BlogPost from '../layouts/BlogPost.astro'
---

<BlogPost title="Hello World" pubDate={new Date("2025-01-01")}>
  <p>This is my first post.</p>
</BlogPost>
```

**The hierarchy:** page → `BlogPost` layout → `Base` layout.

Each layer manages its own concern: `Base` handles the HTML shell, `BlogPost` handles the article chrome, and the page provides the prose. Change the footer in `Base` once — every page and every blog post picks it up.

---

## 5. Layouts for Markdown Pages

Markdown files under `src/pages/` declare a layout in their frontmatter:

```markdown
---
layout: ../layouts/BlogPost.astro
title: My Markdown Post
pubDate: 2025-03-15
---

Body of the post in **Markdown**.
```

Astro automatically passes frontmatter keys as props to the layout. The layout receives `title` and `pubDate` exactly as if they were passed by a parent component.

> **Surprise:** Astro also passes a special `frontmatter` object — `Astro.props.frontmatter.title` works alongside `Astro.props.title`. In practice, use the direct prop pattern; the `frontmatter` object exists for introspection.

---

## Practical Exercises

1. **Extract a base layout.** Move the full `<!doctype html>` shell from `src/pages/index.astro` into `src/layouts/Base.astro`. Accept a `title` prop. Update all existing pages to use it. Run `npm run build` and confirm the output HTML is identical to before.

2. **Named head slot.** Add `<slot name="head" />` to `Base.astro`. In one page, pass a `<meta name="description">` and a `<link rel="canonical">` through the slot. Run `npm run build` — open the output HTML and verify both tags appear inside `<head>`.

3. **Blog layout nesting.** Create `src/layouts/BlogPost.astro` that wraps `Base.astro`. Accept `title` (string) and `pubDate` (Date). Add a formatted `<time>` element and a styled `<article>` wrapper. Create a page that uses `BlogPost` and confirm both layout layers render correctly.

4. **Markdown layout.** Create `src/pages/posts/first.md` with `layout`, `title`, and `pubDate` in frontmatter. Run `npm run build` — verify the Markdown body is wrapped in your article layout.

---

## Self-Check

1. A layout needs to inject a `<link rel="canonical">` that changes per page. What's the right pattern? Sketch the `<slot>` declaration in the layout and the `slot="…"` usage in a page.
2. You have `Base.astro` and a `Docs.astro` that adds a sidebar. How do you compose them so `Base` handles the HTML shell and `Docs` handles the sidebar? Sketch the component tree.
3. A Markdown file declares `layout: ../layouts/BlogPost.astro` and has `title: Hello` in frontmatter. How does `BlogPost.astro` receive `title` — as a prop or from some other mechanism?

---

## Key Takeaways

- A layout is an `.astro` component that uses `<slot />` to render its children — no special API.
- Named slots (`<slot name="x" />` + `slot="x"` on the child) enable multiple injection points per layout.
- Nest layouts to compose concerns: base HTML shell → specialized chrome → page content.
- Markdown pages declare their layout in frontmatter; Astro passes frontmatter keys as props automatically.
- Slot fallback content renders when the parent passes nothing for that slot.
- Layouts live in `src/layouts/` by convention — Astro does not enforce this.

---

## Next

[Unit 04 — Islands & Client Directives →](../04-islands-client-directives/README.md)
