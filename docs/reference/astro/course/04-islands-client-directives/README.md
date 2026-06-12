# Unit 04 — Islands & Client Directives

## What you will learn

- Understand what an "island" is and why it exists
- Add a UI framework (React) to an Astro project with one command
- Use all five `client:*` directives and choose between them deliberately
- Pass serializable data from Astro's build-time scope into a client component
- Understand `client:only` and its tradeoffs

## Why this unit exists

Every prior unit produced zero JavaScript in the browser. This unit is where you deliberately add it — and the discipline of choosing the right loading strategy is what makes Astro sites fast by default. Skipping this means you'll either send too much JS, or you won't understand why your components aren't interactive.

---

## 1. The Problem Islands Solve

In a traditional React SPA, every component hydrates — even purely decorative ones. The browser downloads, parses, and executes the full component tree just to make a hamburger menu clickable.

Astro's answer: **islands**. An island is a component that hydrates **independently** of everything else on the page. The rest of the page is static HTML with zero JS execution cost.

```
┌──────────────────────────────────────┐
│  <nav>Astro Site</nav>  ← static     │
│  <h1>Title</h1>         ← static     │
│  ┌────────────────────┐              │
│  │  <Counter />       │  ← island   │  hydrates independently
│  └────────────────────┘              │
│  <p>Lorem ipsum...</p>  ← static     │
│  <footer>              ← static     │
└──────────────────────────────────────┘
```

Each island is an isolated subtree. Islands hydrate in parallel. A slow carousel does not block a fast nav menu.

---

## 2. Adding a Framework Integration

Install React (or Vue, Svelte, Solid, Preact — same command pattern):

```bash
npx astro add react
# → installs @astrojs/react + react + react-dom
# → updates astro.config.mjs automatically
#   integrations: [react()]
```

Write a React component in `.tsx`:

```tsx
// src/components/Counter.tsx
import { useState } from "react"

export default function Counter() {
  const [count, setCount] = useState(0)
  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  )
}
```

---

## 3. The Five `client:*` Directives

Import the component into an `.astro` file and choose a loading strategy:

```astro
---
import Counter from '../components/Counter.tsx'
---

<Counter client:load />
```

**Without a `client:*` directive**, the component renders to static HTML at build time — its JavaScript never ships.

```astro
<!-- ❌ No JS shipped — button renders but click does nothing -->
<Counter />

<!-- ✅ JS ships and hydrates immediately -->
<Counter client:load />
```

### The full menu

| Directive | When it hydrates | Best for |
|---|---|---|
| `client:load` | Immediately on page load | Critical interactive UI visible above the fold (nav menu, modal trigger) |
| `client:idle` | After `requestIdleCallback` fires | Medium-priority widgets below the fold (share button, newsletter form) |
| `client:visible` | When the component enters the viewport (`IntersectionObserver`) | Heavy or below-fold widgets (comments, data charts) |
| `client:media="(query)"` | When a CSS media query matches | UI that only matters at a specific breakpoint (mobile drawer) |
| `client:only="react"` | Never on server — renders client-side only | Components that require browser APIs (`window`, `localStorage`, maps) |

```astro
<!-- Hydrate immediately — interactive on first paint -->
<Counter client:load />

<!-- Hydrate after idle — user won't notice the brief delay -->
<ShareButton client:idle />

<!-- Hydrate when scrolled into view — zero cost until visible -->
<CommentsSection client:visible />

<!-- Hydrate when viewport width ≤ 768px -->
<MobileMenu client:media="(max-width: 768px)" />

<!-- Never SSR — client-only render (must name the framework) -->
<MapWidget client:only="react" />
```

---

## 4. Passing Props Into Islands

Props work exactly as in any component — you pass them from Astro:

```astro
---
import UserBadge from '../components/UserBadge.tsx'
const user = { name: "Ada", role: "admin" }
---

<UserBadge
  name={user.name}
  isAdmin={user.role === "admin"}
  client:load
/>
```

**Critical constraint:** Props must be **JSON-serializable**. Astro serializes island props to hydrate the component on the client. Functions, class instances, and circular references will not work.

```astro
<!-- ✅ serializable — plain data -->
<Chart data={[10, 20, 30]} title="Sales" client:visible />

<!-- ❌ not serializable — function cannot be JSON-stringified -->
<Chart onHover={() => console.log("hovered")} client:visible />
```

If you need to pass behavior, pass a configuration object and define the handler inside the component instead.

---

## 5. `client:only` — Full Client Render

`client:only` skips server rendering entirely — the component produces **no HTML at build time**. Use it for components that read from `window`, `localStorage`, or any API that doesn't exist in Node.js:

```astro
<MapWidget client:only="react" />
```

You must name the framework ("react", "vue", "svelte", "solid", "preact") so Astro loads the right renderer. Unlike other directives, this element shows **nothing** until JavaScript runs — consider a `<noscript>` fallback or a CSS skeleton.

> **Avoid overusing `client:only`.** It surrenders the main Astro win (static HTML) and causes layout shift. Reach for it only when the component genuinely cannot render without browser APIs.

---

## Practical Exercises

1. **Add React and write a Counter.** Run `npx astro add react`. Create `src/components/Counter.tsx` with a button that increments a count. Import it into `src/pages/index.astro` with `client:load`. Confirm the counter works. Then check `view-source:` in the browser — verify the button HTML is present (server-rendered) even before JS loads.

2. **Compare directives.** Add four copies of `<Counter />` to a page, each with a different `client:*` directive (`client:load`, `client:idle`, `client:visible`, `client:media="(min-width: 1px)"`). Open devtools → Network tab. Notice when each JS bundle loads relative to page load.

3. **`client:visible` in action.** Create a page taller than the viewport (add large spacing elements). Place `<Counter client:visible />` near the bottom. Confirm the JS does **not** load until you scroll down.

4. **Prop serialization.** Try passing an arrow function as a prop to a `client:load` component. Read the error Astro throws. Refactor: move the handler inside the component and pass only the data it needs as a prop.

---

## Self-Check

1. What happens if you use a React component in Astro without any `client:*` directive?
2. You have a cookie-consent banner that must be interactive on first paint. Which directive do you use?
3. You have a `<MapWidget />` that calls `new window.google.maps.Map(...)` at render. Why does it require `client:only="react"`, and what is the cost of using it?

---

## Key Takeaways

- Without `client:*`, components render to static HTML — no JS ships, no hydration.
- Each `client:*` directive is a **hydration strategy**: when to download and execute the component's JavaScript.
- `client:load` → immediate; `client:idle` → deferred; `client:visible` → on scroll; `client:media` → on breakpoint; `client:only` → browser-only.
- Island props must be JSON-serializable — no functions, no class instances.
- `client:only` surrenders server rendering; use it only for components that genuinely require browser APIs.
- Islands hydrate in parallel and independently — a slow island does not block a fast one.

---

## Next

[Unit 05 — Content Collections & the Content Layer →](../05-content-collections/README.md)
