# Astro — The Web Framework for Content-Driven Websites

A ground-up course for working web developers who know HTML, CSS, JS/TS, and the command line. You'll learn Astro from its mental models outward: how it renders everything to static HTML by default, how islands add interactivity without the SPA overhead, and how content collections give you a typed data layer for any source. Each unit builds on the one before — no forward references, no assumed knowledge beyond the prerequisites.

## Course Structure

| Unit | Topic | Practical goal |
|------|-------|----------------|
| [01](course/01-setup-components/README.md) | Project Setup & Component Fundamentals | Create a working Astro project, write and compose `.astro` components with frontmatter, props, and slots |
| [02](course/02-routing-pages/README.md) | File-Based Routing & Pages | Build a multi-page site with static and dynamic routes using `src/pages/` |
| [03](course/03-layouts/README.md) | Layouts & Reusable Structure | Extract shared page shells with layouts, named slots, and nested layout composition |
| [04](course/04-islands-client-directives/README.md) | Islands & Client Directives | Add interactivity with `client:load`, `client:idle`, `client:visible`, and framework components |
| [05](course/05-content-collections/README.md) | Content Collections & the Content Layer | Define typed collections with Zod schemas, load from Markdown or APIs, and render dynamic content pages |
| [06](course/06-view-transitions/README.md) | View Transitions & Enhancing Navigation | Enable animated page transitions with `ClientRouter`, persist elements across navigations, and control fallbacks |
| [07](course/07-integrations-ssr-deploy/README.md) | Integrations, SSR Modes & Deployment | Add UI framework integrations, switch between static/server/hybrid rendering, and deploy to production |

## Prerequisites

**You must know:**
- HTML, CSS, and JavaScript/TypeScript fundamentals
- How to use a terminal (cd, npm, etc.)
- What a component is (React/Vue/Svelte — any framework is fine)
- Basic Markdown syntax

**You do NOT need:**
- Prior Astro experience
- Understanding of static-site generators or Islands Architecture
- A specific UI framework — Astro supports React, Vue, Svelte, Solid, Preact, or none at all
- Knowledge of build tools like Vite or Webpack

## Installation & Setup

```bash
# Create a new Astro project (interactive CLI wizard)
npm create astro@latest my-site

# CLI will ask: template → choose "Basics"
#               install deps? → Yes
#               init git? → Yes

cd my-site

# Start the dev server
npm run dev
# → Astro v5.x.x started in XXms
# → Local: http://localhost:4321/

# Verify: open http://localhost:4321/ in your browser
# You should see the Astro welcome page
```

**Verify your install:**
```bash
npx astro --version
# → astro v5.x.x
```

> **Grounded:** Setup commands sourced from [Astro Install docs](https://docs.astro.build/en/install-and-setup/). Astro v5 (released Dec 2024) is the current major version. Always verify the version at [npm](https://www.npmjs.com/package/astro) if your install looks different.

## Core Mental Models (Read Before Unit 1)

### 1. Astro is server-first, zero-JS by default
Everything renders to static HTML at build time. JavaScript ships *only* when you opt in with a `client:*` directive. There is no client runtime unless you ask for one. This is the single biggest difference from SPA frameworks like React or Next.js, where JavaScript is always present.

> *Source: [Islands Architecture docs](https://docs.astro.build/en/concepts/islands/) — "stripping out all client-side JavaScript automatically"*

### 2. Islands are independent hydration zones
Each component tagged with a `client:*` directive becomes an isolated interactive "island" in a sea of static HTML. Islands hydrate independently and in parallel — a slow carousel won't block an interactive header. The win: you control interactivity at the component level, not the page level.

> *Source: [Islands Architecture docs](https://docs.astro.build/en/concepts/islands/) — "parallel loading", per-component loading strategies*

### 3. File paths ARE your routes
`src/pages/about.astro` becomes `/about`. `src/pages/blog/[slug].astro` becomes `/blog/hello-world`. The filesystem is the routing contract — no route config file needed. Dynamic segments use `[bracket]` syntax, and `getStaticPaths()` tells Astro which paths to generate at build time.

> *Source: [Routing docs](https://docs.astro.build/en/guides/routing/) — "file-based routing"*

### 4. Content Collections are typed, queryable data stores
Define a collection with a Zod schema and a loader (filesystem, API, custom). Query it with `getCollection()`. Render entries with `render()`. You get full TypeScript inference — no manual typing. Astro v5's Content Layer API decouples collections from Vite, enabling caching and remote data sources.

> *Source: [Content Collections docs](https://docs.astro.build/en/guides/content-collections/) — `defineCollection`, `glob` loader, Content Layer API*

### 5. Astro components run once at render time, not in the browser
The `---` code fence is a build-time script block. It fetches data, imports components, and sets up variables. The template below it produces static HTML. Template expressions are dynamic but **never reactive** — if you need reactivity, that's what `client:*` and a framework component are for.

> *Source: [Components docs](https://docs.astro.build/en/basics/astro-components/) — "templates that only run once, during the rendering step"*

## Recommended Sequence

**Phase 1 — Foundations (spend the most time here)**
- Units 01–03. These are non-skippable. Every later concept depends on understanding components, routing, and layouts.

**Phase 2 — The Astro Difference**
- Units 04–05. This is where Astro distinguishes itself from every other framework. Islands and content collections are the reasons to choose Astro over alternatives. Work through the exercises — these concepts need hands-on practice.

**Phase 3 — Production Ready**
- Units 06–07. View transitions polish the UX; integrations and SSR modes unlock real deployment. Read these once you're comfortable building with Astro and want to ship.

## Key Reference Commands

```bash
# Create a new project
npm create astro@latest

# Dev server (hot reload)
npm run dev                    # → http://localhost:4321

# Build for production
npm run build                 # → outputs to dist/

# Preview the production build locally
npm run preview               # → http://localhost:4321

# Add an integration (e.g., React)
npx astro add react

# Type-check the project
npx astro check

# Clear the Astro cache
npx astro info                # → debug info about your project
```