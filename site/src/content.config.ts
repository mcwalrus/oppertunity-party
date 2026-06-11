import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const policies = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/policies" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    url: z.string().optional(),
    scrapedAt: z.string().optional(),
    pdfDownloads: z.array(z.string()).optional(),
  }),
});

const blog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/blog" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    date: z.string().optional(),
    author: z.string().optional(),
    url: z.string().optional(),
    scrapedAt: z.string().optional(),
  }),
});

const events = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/events" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    date: z.string().optional(),
    when: z.string().optional(),
    venue: z.string().optional(),
    address: z.string().optional(),
    location: z.string().optional(),
    url: z.string().optional(),
    scrapedAt: z.string().optional(),
  }),
});

const team = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/team" }),
  schema: z.object({
    name: z.string(),
    slug: z.string(),
    role: z.string().optional(),
    electorate: z.string().optional(),
    url: z.string().optional(),
    scrapedAt: z.string().optional(),
  }),
});

const partyInfo = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/party-info" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    url: z.string().optional(),
    scrapedAt: z.string().optional(),
  }),
});

export const collections = { policies, blog, events, team, "party-info": partyInfo };