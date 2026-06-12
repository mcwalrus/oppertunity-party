# Unit 01 — Project Setup & Component Fundamentals

## What you will learn

- Create a new Astro project with the CLI and understand its directory structure
- Anatomy of a `.astro` file: the frontmatter script block and the HTML template
- Pass typed props into components using `Astro.props`
- Use default and named `<slot />` elements to compose components
- Apply scoped styles with `<style>` blocks

## Why this unit exists

Every concept in this course — routing, layouts, islands, content collections — is expressed through `.astro` files. This unit is the minimal vocabulary. Skip it and every later unit's syntax will be opaque.

---

## 1. Project Structure

After `npm create astro@latest my-site` (choose the **Basics** template), you get:

```
my-site/
├── public/            # Static assets served as-is (images, fonts, favicon)
├── src/
│   ├── pages/         # Routes — every .astro file here becomes a URL
│   └── components/    # Reusable .astro components (not routes, just convention)
├── astro.config.mjs   # Project config
├── tsconfig.json      # TypeScript config (Astro ships with TS support built in)
└── package.json
```

**One rule: `src/pages/` is special.** Files here become routes. Files anywhere else do not. `src/components/` is just a convention — Astro doesn't care what you name non-page directories.

---

## 2. The .astro File Format

A `.astro` file has two sections, separated by triple-dash fences:

```astro
---
// FRONTMATTER — runs once at build time (Node.js environment)
// Never runs in the browser. No window, no document.
const greeting = "Hello, Astro"
---

<!-- TEMPLATE — outputs static HTML -->
<p>{greeting}</p>
<!-- → <p>Hello, Astro</p> -->
```

> **Coming from React?** The frontmatter looks like a function body and the template looks like JSX — but the key difference is that **this code never runs in the browser**. There is no `useState`, no `useEffect`. It's a build-time render, not a runtime render.
>
> **Coming from Vue / Svelte?** The `---` fence is analogous to `<script setup>` in Vue SFCs or the `<script>` block in Svelte — except there is no reactivity system at all. It executes once and stops.

Template expressions use single curly braces `{value}` and produce static HTML. Conditionals and lists use JavaScript directly:

```astro
---
const show = true
const items = ["Apples", "Bananas", "Cherries"]
---

{show && <p>Visible!</p>}

<ul>
  {items.map(item => <li>{item}</li>)}
</ul>
<!-- → <ul><li>Apples</li><li>Bananas</li><li>Cherries</li></ul> -->
```

---

## 3. Component Props

Define props with a TypeScript interface and destructure from `Astro.props`:

```astro
---
// src/components/Greeting.astro
interface Props {
  name: string
  emoji?: string   // optional prop
}

const { name, emoji = "👋" } = Astro.props
---

<p>{emoji} Hello, {name}!</p>
<!-- → <p>👋 Hello, Ada!</p> -->
```

Use it in another component or page:

```astro
---
import Greeting from '../components/Greeting.astro'
---

<Greeting name="Ada" />
<Greeting name="Alan" emoji="🤖" />
```

TypeScript inference is automatic. Your editor knows `name` is `string` and will error if you pass a number. If you omit the `interface Props`, props are typed as `Record<string, any>` — valid but unguarded.

---

## 4. Slots — Injecting Content

Slots let a component accept arbitrary children. The `<slot />` element marks where the injected content renders:

```astro
---
// src/components/Card.astro
---

<div class="card">
  <slot />   <!-- children go here -->
</div>
```

```astro
---
import Card from '../components/Card.astro'
---

<Card>
  <h2>My title</h2>
  <p>My content.</p>
</Card>
<!-- → <div class="card"><h2>My title</h2><p>My content.</p></div> -->
```

### Named Slots

When a component needs multiple injection points, name them:

```astro
---
// src/components/TwoColumn.astro
---

<div class="layout">
  <aside>
    <slot name="sidebar" />
  </aside>
  <main>
    <slot />   <!-- unnamed = default slot -->
  </main>
</div>
```

```astro
<TwoColumn>
  <nav slot="sidebar">Sidebar nav</nav>   <!-- targets the "sidebar" slot -->
  <article>Main content</article>         <!-- targets the default slot -->
</TwoColumn>
```

### Slot Fallback Content

Provide default content rendered when the parent passes nothing:

```astro
<slot>
  <p>No content provided.</p>   <!-- rendered only when slot is empty -->
</slot>
```

---

## 5. Scoped Styles

Styles written in a `<style>` block inside a `.astro` file are **automatically scoped** to that component:

```astro
---
const label = "Click me"
---

<button>{label}</button>

<style>
  button {
    background: cornflowerblue;  /* only applies to THIS component's <button> */
    color: white;
    border-radius: 4px;
  }
</style>
```

No CSS Modules, no BEM, no `className` gymnastics. Astro adds a unique attribute (e.g. `data-astro-cid-abc123`) to both the HTML element and the selector at build time. A plain `button` selector on another page is completely unaffected.

To write a truly global style, use `<style is:global>` — but reach for it sparingly.

---

## Practical Exercises

1. **Scaffold and explore.** Run `npm create astro@latest` with the "Basics" template. Open `src/pages/index.astro` and identify the frontmatter and template sections. Add a `<p>` tag that uses a variable defined in frontmatter.

2. **Write a `Button` component.** In `src/components/Button.astro`, accept a `label` (string) and `variant` ("primary" | "secondary") prop. Render a `<button>` with the label and a class based on variant. Import it into `src/pages/index.astro` and use it twice with different variants.

3. **Build a `MediaCard` component.** Accept `img` (src string), `title`, and `body` via props, AND a `footer` named slot. Render an image, heading, paragraph, then whatever is passed into the `footer` slot. Use it with an `<a>` link in the footer slot.

4. **Add scoped styles.** Add a `<style>` block to your `Button` component. In devtools, inspect the rendered HTML — confirm Astro added a `data-astro-cid-*` attribute. Add a plain `button` selector to a global stylesheet and confirm the component's button is unaffected.

---

## Self-Check

1. What environment does the frontmatter (`---`) block run in — browser or build-time Node.js? What does that mean if you try to access `window` or `document`?
2. You have a component that needs two separate areas for injected content: a header and a body. What Astro feature handles this? Write the `<slot />` declarations inside the component.
3. You define `interface Props { count: number }` but a teammate passes `count="5"` (a string). What happens at build time?

---

## Key Takeaways

- The `---` frontmatter is a Node.js build-time script — it **never runs in the browser**.
- Template expressions `{value}` produce static HTML — they are not reactive.
- Props are typed via `interface Props` and accessed with `Astro.props`.
- `<slot />` inserts children; `<slot name="x" />` creates named injection points.
- `<style>` blocks in `.astro` files are automatically scoped to that component.
- `src/pages/` is the only directory Astro treats as special at build time.

---

## Next

[Unit 02 — File-Based Routing & Pages →](../02-routing-pages/README.md)
