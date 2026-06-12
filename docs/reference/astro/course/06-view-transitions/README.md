# Unit 06 — View Transitions & Enhancing Navigation

## What you will learn

- Understand the difference between MPA navigation and View Transitions
- Enable client-side navigation with `<ClientRouter />`
- Apply built-in animations (`fade`, `slide`) and custom transitions
- Morph elements across pages with `transition:name`
- Persist DOM nodes (and their JS state) across navigations with `transition:persist`
- Use lifecycle events to re-run scripts after navigation
- Handle accessibility and `prefers-reduced-motion`

## Why this unit exists

Without this unit, every link in your Astro site causes a full browser navigation — a white flash, full layout repaint, loss of scroll position. View Transitions gives you the animated continuity of a SPA with the HTML-first foundation of an MPA. It is also the unit where client-side state management becomes relevant for the first time.

---

## 1. MPA Navigation vs. View Transitions

By default, Astro sites are MPAs: every link click fetches a new HTML document. That is fast and correct, but the full-document swap causes a visible flash.

The [View Transitions browser API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transitions_API) allows the browser to screenshot the current page, swap the document, and animate between the two screenshots. Astro's `<ClientRouter />` implements this — plus a JavaScript fallback for browsers that don't support the native API:

```astro
---
// src/layouts/Base.astro — add once, in the base layout
import { ClientRouter } from 'astro:transitions'
---

<!doctype html>
<html lang="en">
  <head>
    <ClientRouter />   <!-- enables client-side navigation for the whole site -->
  </head>
  <body>
    <slot />
  </body>
</html>
```

That single line turns every in-site `<a>` link into a smooth animated transition.

> **Surprise:** Unlike React Router or Next.js Link, `<ClientRouter />` works on **your existing `<a>` tags**. You don't replace links with a `<Link>` component. Remove `<ClientRouter />` and everything still works — just without animation. The progressive enhancement is genuine.

---

## 2. Built-in Transition Animations

Astro ships two built-in animations. Apply them to any element with `transition:animate`:

```astro
---
import { fade, slide } from 'astro:transitions'
---

<!-- Default fade — applies to this element during every navigation -->
<main transition:animate="fade">
  <slot />
</main>

<!-- Slide transition -->
<nav transition:animate="slide">...</nav>

<!-- Customise duration via the helper function -->
<main transition:animate={fade({ duration: '0.3s' })}>
  <slot />
</main>
```

You can define entirely custom animations using CSS keyframes — see the [Astro transitions API docs](https://docs.astro.build/en/guides/view-transitions/#customizing-animations) for the `TransitionAnimation` object shape.

---

## 3. Named Transitions — Morphing Elements Across Pages

Give two elements the **same `transition:name`** on two different pages, and Astro morphs one into the other during navigation. The browser animates the element from its old position/size to its new one — no explicit keyframes needed.

```astro
---
// src/pages/blog/index.astro — list page
import { getCollection } from 'astro:content'
const posts = await getCollection('blog')
---

{posts.map(post => (
  <a href={`/blog/${post.id}`}>
    <img
      src={post.data.cover}
      alt={post.data.title}
      transition:name={`cover-${post.id}`}
    />
    <h2>{post.data.title}</h2>
  </a>
))}
```

```astro
---
// src/pages/blog/[id].astro — detail page
const { post } = Astro.props
---

<img
  src={post.data.cover}
  alt={post.data.title}
  transition:name={`cover-${post.id}`}   <!-- same name → morph on navigation -->
/>
<h1>{post.data.title}</h1>
```

The cover image flies from its list-page thumbnail position to its full-width detail-page position. The browser calculates the path; you just matched the names.

**Rules for `transition:name`:**
- Must be unique per page (two elements with the same name on one page is an error)
- Use a dynamic value (`cover-${post.id}`) for elements that repeat, like collection items
- The element doesn't have to exist on both pages — if it only exists on one, it fades instead

---

## 4. Persisting Elements Across Navigation

`transition:persist` keeps a DOM node **alive** across navigations, reusing it rather than replacing it. The node is transplanted into the new document's DOM after each navigation.

```astro
<!-- Audio player keeps playing as user navigates -->
<audio controls src="/podcast.mp3" transition:persist />

<!-- Theme toggle keeps its local state -->
<ThemeToggle client:load transition:persist="theme-toggle" />
```

Use a string value for `transition:persist` when the element might not appear on every page — it acts as an identifier for re-attachment.

**When to use `transition:persist`:**
- Audio or video players that should keep playing
- Theme toggles or sidebar state that must survive navigation
- Shopping cart icons with client-side count state

**Constraint:** `transition:persist` preserves the DOM node, so React/Vue/Svelte islands that are persisted keep their JavaScript state too. This is usually what you want. But if the persisted island should receive new server-side props on the next page, those props are silently ignored — the island keeps the props it was first initialized with.

---

## 5. Navigation Lifecycle Events

Astro fires custom DOM events at each stage of a View Transition:

| Event | When it fires |
|---|---|
| `astro:before-preparation` | Just before the new page starts fetching |
| `astro:after-preparation` | New page HTML fetched, before DOM swap |
| `astro:before-swap` | Immediately before the DOM is updated |
| `astro:after-swap` | DOM updated, old scripts unloaded |
| `astro:page-load` | All done — animation finished, page fully ready |

**`astro:page-load` is the most useful.** It replaces `DOMContentLoaded` for any code that must re-run after each navigation:

```astro
<script>
  // Without ClientRouter: DOMContentLoaded fires once, on first load.
  // With ClientRouter:    astro:page-load fires on first load AND after every navigation.
  document.addEventListener('astro:page-load', () => {
    // Re-initialize syntax highlighting, tooltips, scroll listeners, etc.
    document.querySelectorAll('pre code').forEach(el => {
      // hljs.highlightElement(el)
    })
  })
</script>
```

> **Common gotcha:** You add `<ClientRouter />` and a third-party script (analytics, highlight.js, tooltips) stops working after the first navigation. The cause is always the same: the script ran on `DOMContentLoaded` (or no event at all), which only fires once. Move it to `astro:page-load`.

---

## 6. Accessibility & `prefers-reduced-motion`

View Transitions can cause accessibility issues: focus may be lost; screen readers may not re-announce the new page. Astro handles focus automatically (moves focus to `<body>` after each swap), but always test with a screen reader.

Respect the user's motion preference with a CSS media query:

```css
/* src/styles/global.css */
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(root),
  ::view-transition-new(root) {
    animation: none;   /* disable all View Transition animations */
  }
}
```

Astro's JavaScript fallback (for Firefox, older Safari) still runs — users get instant navigation rather than a flash, but without the animation overhead.

---

## Practical Exercises

1. **Enable `<ClientRouter />`.** Add it to your base layout. Navigate between pages — notice the default fade. Open the Network panel: subsequent navigations should fetch only the new page's HTML, not a full reload.

2. **Apply `transition:animate`.** Add `transition:animate="slide"` to your `<nav>`. Compare how the navigation feels vs. the default fade on `<main>`.

3. **Named morph transition.** On your blog list page, add `transition:name={`cover-${post.id}`}` to each post's cover image. Add the same attribute to the cover image on the detail page. Click through — confirm the image animates from list to detail.

4. **Persist a counter.** Add a `<Counter client:load transition:persist />` to your base layout's header. Navigate to another page — confirm the counter value survives navigation.

5. **Fix a script after navigation.** Add a script that logs `"page ready"` on `DOMContentLoaded`. Navigate — notice it only runs once. Migrate it to `astro:page-load` and confirm it runs on every navigation.

---

## Self-Check

1. What is the difference between `transition:name` and `transition:persist`? Give a concrete use case for each.
2. You add `<ClientRouter />` and your syntax-highlighting library stops working after the first navigation. What is the root cause, and what is the fix?
3. A user has `prefers-reduced-motion: reduce` set. What should happen to View Transitions in your site, and where do you implement that behavior?

---

## Key Takeaways

- `<ClientRouter />` in the base layout's `<head>` enables client-side navigation — one line.
- `transition:animate` applies an animation (fade, slide, or custom) to an element during navigation.
- `transition:name` on matching elements across two pages creates a "morph" animation between them.
- `transition:persist` keeps a DOM node (and its JS state) alive across navigations.
- `astro:page-load` replaces `DOMContentLoaded` for scripts that must re-run after each navigation.
- Always add a `prefers-reduced-motion` CSS rule to disable animations for users who prefer it.

---

## Next

[Unit 07 — Integrations, SSR Modes & Deployment →](../07-integrations-ssr-deploy/README.md)
