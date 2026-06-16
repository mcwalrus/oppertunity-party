
# Opportunity Party 

- [x] Generate the standard for llms.txt and llms-full.txt
- [x] Compare this to a firecrawl attempt for the same web-page.
- [ ] Produce a report to compare (on it)


The `llms.txt` and `llms-full.txt` files are emerging, machine-readable standards designed to provide Large Language Models (LLMs) and AI agents with direct, optimised access to your website's content and documentation. `robots.txt` tells crawlers what to avoid, these files are designed to guide AI models to the most useful content on your site. Notably these standards are accepted for developer tooling using agents, but not web-scrapers or index search bots. Policies against AI training is effective which are managed by CloudFlare. Presenting PDFs as fetch-able resources (not presented through Google Drives) are important for discoverability of policy details by users of AI. Currently, AI is not able to obtain download access to Google Drives dynamically. We want to state in plain english what the current policy standards for robots.txt is, it could be considered by the party whether we adjust these settings through Cloudflare to make the party's position searchable. 

## Future Standards

MCP is a useful protocol to provide AI with a set of tools which relates to promoting a product in market. Most of this is achievable through independent analysis, which is queried by AI at the time of when the user asks. Relying on our websites, we don't need to provide tools to provide explicit details to users of AI who are investigating the Opportunity party.

MCP could be developed by Opportunity Party for other reasons though. An MCP connector would signal by the party that they, unlike other parties understand the future of technology and their position in it. For the party, this might signal strength of understanding key developments in the AI field relative to other parties, this also may encourage those interested in the party to engage in conversation through AI. It's important to recognise key statistics about how convincing AI is at convincing people of ideas. There are current studies out which represent this. Consider the a list of useful reasons why this would be constructive to the parties interests.

## LLMs.txt

An `llms.txt` file is a proposed markdown standard hosted at the root of a website (e.g., `yourdomain.com/llms.txt`) designed to act as a clear, structured roadmap for AI models and autonomous agents. It directs language models to your most important, up-to-date content.

**Specification Proposal:** https://llmstxt.org/

**Adoption is low and flat.** A SE Ranking study of 300,000 domains found a 10.13% adoption rate — roughly one in ten sites after eighteen months of industry conversation. Other research puts it in the 5 to 15% range as of early 2026.

**Google explicitly declined to support it.** John Mueller publicly stated the Search team does not use or endorse llms.txt; it appeared on Google's own site only because their internal CMS added support and some teams didn't remove it. No major AI lab — OpenAI, Anthropic, Google, Meta, Mistral — treats it as a first-class input. [LBN Tech Blog](https://lbntechsolutions.com/blogs/llms-txt-google-search-seo-guide/)

**No measurable SEO or citation benefit.** An analysis of 94,614 cited URLs from 11,867 AI responses found essentially no indication that llms.txt provides a measurable advantage. One study found that an AI-citation model actually improved when the llms.txt variable was removed — meaning the file added noise rather than predictive signal. [ALLMO](https://allmo.ai/articles/llms-txt)[Codersera](https://codersera.com/blog/llms-txt-complete-guide-2026/)


**1. Major Web and AI Crawlers (Ignored)**

The large-scale bots that crawl the web for training data and search indexing—such as OpenAI's GPTBot, Google-Extended, Anthropic's ClaudeBot, and PerplexityBot—do not currently rely on `llms.txt`.

- **Google** has explicitly stated on the record that they do not use `llms.txt` and have no plans to support it for search or Gemini.
    
- **OpenAI and Anthropic** have not officially mandated or endorsed the file for their general web crawlers. Traffic analyses of millions of bot visits show that these large crawlers overwhelmingly skip the `/llms.txt` file and parse the HTML directly.

**2. IDE Agents and Developer Tools (Endorsed and Actively Used)**

Where `llms.txt` has found massive success and unofficial endorsement is in the realm of **agentic workflows and coding assistants**.

- Tools like **Cursor, Windsurf, GitHub Copilot, and Claude Code** actively look for `/llms.txt` and `/llms-full.txt` when a developer points them at a documentation site.
    
- Frameworks like LangChain have built tools specifically designed to fetch and route information using these files.
    
- Major documentation hosting platforms (such as Mintlify, Vercel Docs, and GitBook) now automatically generate and ship `llms.txt` files by default because coding agents rely on them to quickly understand a library's ecosystem without wasting context window space on navigation menus.



[https://opportunity.org.nz/](https://opportunity.org.nz/) is a political party in New Zealand. I am wondering if even informally it would be worth the party recognising the standard as to provide the indexed links in a way which shows the party up-to-date for LLMs. This would be making the case for SEO ranking and exposing policies hidden in PDFs more publicly.




This is better than the site-map approach.

Note, my approach may become redundant through 

https://www.opportunity.org.nz/llms.txt

Provide both:

https://modelcontextprotocol.io/llms-full.txt

Is there a standard I can use somewhere?

https://modelcontextprotocol.io/llms.txt


Opportunity Robots 

https://www.opportunity.org.nz/robots.txt

```
User-Agent: *
Disallow: /admin/
Disallow: /auth/
Disallow: /utils/
Disallow: /forms/
Disallow: /users/
Sitemap: https://www.opportunity.org.nz/sitemap_index.xml
```

What this means:

```
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap>
<loc>https://www.opportunity.org.nz/sitemap.xml</loc>
<lastmod>2026-06-14T01:29:39Z</lastmod>
</sitemap>
<sitemap>
<loc>https://www.opportunity.org.nz/sitemap_news.xml</loc>
<lastmod>2026-06-14T01:29:39Z</lastmod>
</sitemap>
</sitemapindex>
```

https://www.opportunity.org.nz/sitemap.xml

```
MUCH More...
```


https://opportunity.org.nz/robots.txt

```
# As a condition of accessing this website, you agree to abide by the following
# content signals:

# (a)  If a Content-Signal = yes, you may collect content for the corresponding
#      use.
# (b)  If a Content-Signal = no, you may not collect content for the
#      corresponding use.
# (c)  If the website operator does not include a Content-Signal for a
#      corresponding use, the website operator neither grants nor restricts
#      permission via Content-Signal with respect to the corresponding use.

# The content signals and their meanings are:

# search:   building a search index and providing search results (e.g., returning
#           hyperlinks and short excerpts from your website's contents). Search does not
#           include providing AI-generated search summaries.
# ai-input: inputting content into one or more AI models (e.g., retrieval
#           augmented generation, grounding, or other real-time taking of content for
#           generative AI search answers).
# ai-train: training or fine-tuning AI models.

# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
# RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT
# AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET.

# BEGIN Cloudflare Managed content

User-agent: *
Content-Signal: search=yes,ai-train=no
Allow: /

User-agent: Amazonbot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: CloudflareBrowserRenderingCrawler
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: GPTBot
Disallow: /

User-agent: meta-externalagent
Disallow: /

# END Cloudflare Managed Content
```

This is a robots.txt file with Content Signals, not specific to any site called "opportunity party" — that may be the domain you're asking about, but no domain name appears in the text you've shared.

What this file says:

For most crawlers (`User-agent: *`), `Content-Signal: search=yes, ai-train=no` means search indexing is permitted, but AI training is explicitly disallowed. Notably, this signal is silent on `ai-input` — under the rules stated at the top, that means neither granted nor restricted.

However, the `*` rule is then overridden for specific named bots. `ClaudeBot` is explicitly listed with `Disallow: /`, meaning Anthropic's crawler is blocked from accessing the site entirely — for any purpose, including search indexing.

## The argument _for_ letting LLMs read the site

For a political party, the calculus is different from a news publisher or a shop. You don't earn ad revenue from page views, and the content is campaign material you are actively trying to push into as many heads as possible. So:

- **Reach.** Voters increasingly ask AI assistants "what's [party]'s position on X." If your site is fully blocked, the assistant falls back on stale training data, third-party news, Wikipedia, or hostile commentary (recall the World Socialist Web Site piece that surfaced when I searched — that's the kind of source that fills the vacuum). For a party fighting to cross the 5% MMP threshold, being absent from AI answers is lost mindshare you can't afford.
- **Accuracy and narrative control.** When an assistant can read your own words, it tends to cite your framing ("largest tax cut for low-income working Kiwis") rather than an opponent's ("a tax on the family home"). Blocking your site doesn't stop AI discussing you — it just removes _your voice_ from the inputs.
- **Freshness.** You rebranded in late 2025, changed leader, and ran a new 2026 platform. Training data is stale by definition; only live fetching reflects the _current_ policy rather than the 2017 Gareth Morgan version. Allowing the real-time fetchers is the only way AI reflects today's platform.

## The argument _against_ (i.e. for restricting)

- **Misrepresentation risk.** AI summaries compress and can mangle nuance, and you have no control over the output. Your tax policy is unusually easy to caricature — an assistant that surfaces "1.75% tax on land including your home" without the offsetting Citizen's Income could do real political damage. On your own page that scary number sits inside a wall of FAQ reassurance; an AI answer strips that scaffolding away.
- **Training has low upside, lasting downside.** Content absorbed into a training set arrives with no attribution, no linkback, and can resurface years later, out of date, untraceable. For a party, `ai-train=no` is quite rational: little reach benefit (it's not live), and the risk of permanently baking in a superseded position. So your training block is arguably your _most_ defensible choice.
- **Principled / positioning stance.** Reserving rights against AurAI mining is itself a political signal a party might want to send, and it's consistent with taking data-rights positions publicly.
- **Bot load and adversarial analysis** — both minor here (Cloudflare handles load; the content is public anyway).

