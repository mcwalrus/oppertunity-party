## Site path structure

```
/                          Homepage
│
├── /policy                Policy index (hub)
│   ├── Priority policies
│   │   ├── /healthy-oceans
│   │   ├── /abundant-energy
│   │   ├── /productivity-unleashed
│   │   ├── /citizens-voice
│   │   └── /tax-reset
│   └── Other policies
│       ├── /clean_up_politics
│       ├── /honouring_te_tiriti
│       ├── /future_fit_education
│       ├── /healthy_land
│       ├── /healthy_people
│       ├── /climate_action
│       ├── /intergenerational_infrastructure
│       ├── /affordable_housing
│       └── /smart_on_crime
│
├── /team                  Candidates / people
├── /about                 Party background
├── /meet-q                Leader profile (Qiulae Wong)
├── /events                Events listing
├── /news                  News / media releases
│
├── /get-involved          Conversion hub
│   ├── /volunteer
│   ├── /join
│   └── /donate
│
├── /contact               Contact form
├── /party-information     Constitution / registration / governance
│
└── Account / auth (NationBuilder-managed)
    ├── /login
    ├── /subscribe         Create account
    └── /cdn-cgi/l/email-protection   (Cloudflare email obfuscation)
```

Two URL conventions coexist: hyphenated slugs (`/healthy-oceans`) for the newer priority policies and underscore slugs (`/clean_up_politics`) for the older set — a sign the priority policies were added/renamed more recently than the rest.

## What's publicly learnable about the party

On the political side, the party rebranded from "The Opportunities Party (TOP)" to "Opportunity Party" and is led by Qiulae Wong, who took over in November 2025 following the resignation of Raf Manji, and is aiming to reach the 5% threshold required to enter parliament at the next election. The site positions them in the political centre with three pillars — stopping political division, building a sustainable high-wage economy, and restoring nature — and an explicit 2026 election footing (a banner notes 16 newly announced candidates). Their registered address and authorising agent are public on every page: Hayden Cargo, 2D Amera Place, Auckland.

On the technical/infrastructure side, the site reveals a fair amount:

The site runs on **NationBuilder**, the campaign-CMS platform widely used by political parties (asset URLs point to `assets.nationbuilder.com`). The account slug embedded in those asset paths is **`garethmorgan`** — a legacy artefact from founder Gareth Morgan's original setup, still underlying the rebranded site nearly a decade later. This is the kind of detail that persists invisibly through rebrands.

They use **Google Tag Manager** (container `GTM-5M8XMTND`) for analytics/marketing tags, and **Cloudflare** in front of the site (the email-protection endpoint). NationBuilder also implies a built-in supporter CRM behind the public pages: the homepage embeds a signup form capturing name, email, tertiary institution, student ID, and an under-30 "Young Opportunity" flag — so they're segmenting supporters by age and student status for organising purposes.

Their full off-site presence is linked in the footer: Facebook, Instagram, LinkedIn, TikTok, X, and YouTube (all under `opportunity`/`opportunitynz` handles), plus a media section linking coverage from NBR, TVNZ, The Spinoff, Stuff, NZ Herald, and RNZ.
