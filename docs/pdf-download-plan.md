# Plan: Automated PDF Download as Part of Scrape

## Problem

Policy PDFs in `data/policy-assets/` are currently downloaded manually. The download links (Google Drive URLs) are embedded in the policy pages on the website. When running `just scrape`, PDFs are **not** fetched — only the web pages are scraped, and then any PDFs already sitting in `policy-assets/` are converted to markdown.

This means a fresh scrape on a new machine produces no PDF-derived content until someone manually downloads the PDFs.

## Current Flow

```
1. scrape_policies()     → fetches web pages, saves .md files
2. convert_all_pdfs()    → reads pre-existing PDFs from data/policy-assets/, converts to .md
```

The missing step: **downloading the PDFs that `convert_all_pdfs()` depends on**.

## Where the Links Come From

The policy pages on the website contain Google Drive download links in their HTML. After markdown conversion they look like:

- `[Download the full policy paper](https://drive.google.com/file/d/1-QMkAP3CI8_14Sn7FKRafLi283B_O7zI/view?usp=drive_link)`
- `[DOWNLOAD](https://drive.google.com/file/d/1KgTXUgjVipAA7EcDas-EJmOr6ZkeCf9B/view?usp=drive_link)`

Known policies with PDF links:

| Policy | Download Links |
|--------|---------------|
| abundant-energy | 1 Google Drive link (policy paper) |
| healthy-oceans | 1 Google Drive link (policy paper) |
| citizens-voice | 1 Google Drive link (policy paper) |
| tax-reset | 2 Google Drive links (policy overview + transition plan) |

Some policies (e.g. affordable-housing, climate-action) don't currently have PDF download links on their pages.

## Proposed New Flow

```
1. scrape_policies()      → fetches web pages, saves .md files
   └─ also extracts Google Drive PDF links from each page (from BeautifulSoup before markdownify)
2. download_policy_pdfs()  → NEW: downloads PDFs from extracted links → data/policy-assets/
3. convert_all_pdfs()     → reads PDFs from data/policy-assets/, converts to .md
```

## Implementation Plan

### 1. Add `pdf_downloads` field to `PolicyPage` model

In `scraper/models.py`, add an optional list of download URLs to `PolicyPage`:

```python
pdf_downloads: list[str] = field(default_factory=list)
```

### 2. Extract PDF links during policy scraping

In `scraper/policies.py`, modify `_extract_markdown()` or add a new `_extract_pdf_links()` function that runs **before** markdownify on the BeautifulSoup object. Look for `<a>` tags linking to Google Drive (or other file hosts):

```python
def _extract_pdf_links(soup) -> list[str]:
    """Extract Google Drive download links from a policy page."""
    links = []
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        if "drive.google.com" in href or href.endswith(".pdf"):
            links.append(href)
    return links
```

This should be called on the raw `soup` **before** any decomposition, so we don't lose links.

### 3. Create `scraper/pdf_download.py`

New module that handles downloading PDFs:

```python
def download_policy_pdfs(policies: list[PolicyPage]) -> list[Path]:
    """Download all PDFs from policy page download links."""
    ...
```

Key responsibilities:

- **Google Drive URL conversion**: Transform `/file/d/FILE_ID/view` URLs into direct download URLs: `https://drive.google.com/uc?export=download&id=FILE_ID`
- **Skip already-downloaded files**: Check if the target file already exists in `data/policy-assets/` (by Google Drive file ID)
- **Download via curl**: Use the existing `subprocess.run(["curl", ...])` pattern from `client.py`
- **Handle large files / virus scan warnings**: Google Drive shows an interstitial for large files. Use `curl -L` (follow redirects) and potentially handle the confirm=XXX token in the response
- **Name files sensibly**: Use the policy slug + document description to name the PDF, or fall back to extracting the filename from the response headers

### 4. Update `main.py` pipeline

Insert the download step between scraping and PDF conversion:

```python
SCRAPER_MAP = {
    "policies": ("policies", scrape_policies, save_policies),
    "pdfs": None,  # Will be handled in sequence
    ...
}

def run_scrapers(...):
    ...
    # After scraping policies, download any PDFs
    if "policies" in selected:
        download_policy_pdfs(policies_scraped)

    # Then convert PDFs
    convert_all_pdfs()
```

### 5. Update `client.py`'s `clean_data()`

Currently `clean_data()` preserves the entire `policy-assets/` directory. This should still be the default, but we might want an option to also clear downloaded PDFs on a full `--clean` reset.

### 6. Save a reference file

After downloading, save `data/policy-assets/reference.json` mapping each PDF to:

- Source URL (Google Drive link)
- Policy slug it came from
- Download timestamp
- File size

This replaces the need for a manual `reference.md` and serves as the source of truth for where each PDF came from.

## Google Drive Download Details

Google Drive URLs come in this form:

```
https://drive.google.com/file/d/FILE_ID/view?usp=drive_link
```

Direct download URL:

```
https://drive.google.com/uc?export=download&id=FILE_ID
```

For files over ~100MB, Google Drive returns an HTML page with a virus scan warning and a `confirm=TOKEN` parameter. The download flow then becomes:

1. Request `uc?export=download&id=FILE_ID`
2. If response is HTML (virus scan warning), extract the `confirm=TOKEN` and `uuid=UUID` from the form
3. Re-request with `confirm=TOKEN&uuid=UUID` added

For the policy PDFs (which are likely <5MB each), the simple download URL should work. We should still handle the virus scan interstitial as a fallback.

## curl Command Pattern

```bash
curl \
  --silent \
  --show-error \
  --fail \
  --location \
  --max-time 60 \
  --output "data/policy-assets/filename.pdf" \
  "https://drive.google.com/uc?export=download&id=FILE_ID"
```

## File Naming Convention

Name the downloaded PDFs consistently. Options:

1. **Keep original Google Drive filename** (from Content-Disposition header) — most portable
2. **Derive from policy slug** — e.g. `abundant-energy_policy-overview.pdf`
3. **Hybrid** — prefix with policy slug for sortability

Recommendation: **Option 1** for backwards compatibility (matching existing files like `Opportunity_Policy_Abundant Energy.pdf`), with the reference JSON mapping providing the structured metadata.

## Edge Cases

- **Policy with no PDF link**: Skip gracefully, log info
- **PDF already downloaded**: Check by file ID in reference JSON, skip if file still exists
- **Download fails**: Log error, continue — don't block the rest of the pipeline
- **New PDF link appears on a policy page**: Automatically discovered and downloaded on next scrape
- **Multiple PDF links per policy** (e.g. tax-reset has 2): Handle each link separately
- **Link points to non-Google-Drive host**: Support generic PDF URL downloads too (any `*.pdf` URL)

## Testing

1. Run `just scrape` on a clean `data/` directory (minus policy-assets)
2. Verify PDFs appear in `data/policy-assets/`
3. Verify `reference.json` is created with correct mappings
4. Verify markdown conversion still works (`pdf-*.md` files created)
5. Run again — verify already-downloaded PDFs are skipped (idempotent)