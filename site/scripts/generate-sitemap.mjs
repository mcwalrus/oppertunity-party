#!/usr/bin/env node
/**
 * generate-sitemap.mjs
 *
 * Reads site/dist/docs_site_map.md (the Astro-built sitemap with relative links)
 * and writes a resolved copy back to the same path with fully-qualified absolute URLs.
 *
 * Usage (from inside site/):
 *   SITE_URL=https://opportunity.org.nz node scripts/generate-sitemap.mjs
 *
 * SITE_URL may also be declared in .env.local (relative to site/ directory).
 * The file is loaded before process.env is consulted, but existing env vars
 * always take precedence (CI/deployment variables win over .env.local).
 *
 * Relative links transformed:
 *   [Policies](/policies.md)  →  [Policies](https://opportunity.org.nz/policies.md)
 *
 * Pattern matched: ](/path) — any markdown link whose href starts with a single /.
 * Extensions are preserved exactly as they appear in the source; no normalisation.
 *
 * Fails fast (exit 1) if:
 *   - SITE_URL is not set after loading .env.local
 *   - dist/docs_site_map.md does not exist (build has not been run)
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const __dirname = dirname(fileURLToPath(import.meta.url));
/** Absolute path to the site/ directory (parent of scripts/). */
const SITE_ROOT = resolve(__dirname, "..");

const SOURCE_PATH = resolve(SITE_ROOT, "dist", "docs_site_map.md");
const OUTPUT_PATH = resolve(SITE_ROOT, "dist", "docs_site_map.md");

// ---------------------------------------------------------------------------
// Load .env.local (if present) — does NOT overwrite existing env vars
// ---------------------------------------------------------------------------

function loadEnvLocal() {
  const envPath = resolve(SITE_ROOT, ".env.local");
  if (!existsSync(envPath)) return;

  const raw = readFileSync(envPath, "utf-8");
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    // Skip blank lines and comments
    if (!trimmed || trimmed.startsWith("#")) continue;

    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;

    const key = trimmed.slice(0, eqIdx).trim();
    // Strip optional surrounding quotes from the value
    const value = trimmed
      .slice(eqIdx + 1)
      .trim()
      .replace(/^(["'])(.*)\1$/, "$2");

    // Existing env vars (e.g. from CI) always win
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

loadEnvLocal();

// ---------------------------------------------------------------------------
// Validate SITE_URL
// ---------------------------------------------------------------------------

const rawSiteUrl = process.env.SITE_URL;
if (!rawSiteUrl) {
  console.error(
    [
      "❌  SITE_URL is not set.",
      "",
      "    For local development, create site/.env.local and add:",
      "        SITE_URL=http://localhost:4321",
      "",
      "    For CI / deployment, set the SITE_URL environment variable in your",
      "    pipeline or hosting dashboard (e.g. Cloudflare Pages → Settings →",
      "    Environment Variables).",
      "",
      "    Example (one-shot):",
      "        SITE_URL=https://opportunity.org.nz node scripts/generate-sitemap.mjs",
    ].join("\n"),
  );
  process.exit(1);
}

/** Base URL with any trailing slashes stripped. */
const BASE_URL = rawSiteUrl.replace(/\/+$/, "");

// ---------------------------------------------------------------------------
// Validate source file
// ---------------------------------------------------------------------------

if (!existsSync(SOURCE_PATH)) {
  console.error(
    [
      `❌  Source file not found: ${SOURCE_PATH}`,
      "",
      "    Run the site build first so that Astro generates the sitemap:",
      "        pnpm build          # from inside site/",
      "        just site-build     # from the project root",
    ].join("\n"),
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Resolve relative links
// ---------------------------------------------------------------------------

const source = readFileSync(SOURCE_PATH, "utf-8");

/**
 * Replace every markdown link of the form ](/path...) with ](BASE_URL/path...).
 *
 * The regex matches:
 *   \]      — closing bracket of link text
 *   \(      — opening paren of href
 *   \/      — href starts with exactly one slash
 *   ([^)]+) — capture the rest of the href up to the closing paren
 *   \)      — closing paren
 *
 * Protocol-relative URLs (//) are excluded by the [^)] guard because the
 * second slash is just another character in the captured group — but that
 * is fine since the source file should never contain protocol-relative hrefs.
 */
const RELATIVE_LINK_RE = /\]\(\/([^)]+)\)/g;

let count = 0;
const resolved = source.replace(RELATIVE_LINK_RE, (_match, path) => {
  count++;
  return `](${BASE_URL}/${path})`;
});

// ---------------------------------------------------------------------------
// Write output
// ---------------------------------------------------------------------------

writeFileSync(OUTPUT_PATH, resolved, "utf-8");

console.log(
  [
    `✅  docs_site_map.md resolved.`,
    `    Links rewritten : ${count}`,
    `    Base URL        : ${BASE_URL}`,
    `    Output          : ${OUTPUT_PATH}`,
  ].join("\n"),
);
