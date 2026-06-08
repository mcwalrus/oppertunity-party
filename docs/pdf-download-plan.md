# Plan: Automated PDF Download + Organized Policy Storage

## Problem

1. **PDFs not downloaded automatically**: Policy PDFs in `data/policy-assets/` are currently downloaded manually. When running `just scrape`, PDFs are **not** fetched — only the web pages are scraped, and then any PDFs already sitting in `policy-assets/` are converted to markdown. A fresh scrape on a new machine produces no PDF-derived content until someone manually downloads the PDFs.

2. **Flat output structure**: Converted PDFs are dropped as loose markdown files in `data/policies/` alongside the HTML-sourced policy files. This makes it harder to see what content came from where, especially for policies like `tax-reset` that have multiple PDF documents.

## Current Flow

```
1. scrape_policies()     → fetches web pages, saves .md files
2. convert_all_pdfs()    → reads pre-existing PDFs from data/policy-assets/, converts to .md
```

The missing steps:
- **Downloading PDFs** that `convert_all_pdfs()` depends on
- **Organizing output** so each policy's files are grouped together

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
   └─ output organized by policy slug in data/policies/{slug}/
```

## Output Structure

After implementation, `data/policies/` will look like:

```
data/policies/
├── index.json                    # Combined index of all policies
├── abundant-energy/
│   ├── page.md                   # HTML-sourced content
│   ├── policy-overview.pdf       # Downloaded source PDF (if available)
│   └── policy-overview.md        # PDF converted to markdown
├── healthy-oceans/
│   ├── page.md
│   └── ...
├── tax-reset/
│   ├── page.md
│   ├── policy-overview.pdf
│   ├── policy-overview.md
│   ├── policy-addendum.pdf       # e.g. transition plan
│   └── policy-addendum.md
└── ... (one directory per policy)
```

**Note**: Single-file policies can remain flat if preferred, but the slug directory should still exist with at least `page.md`.

## Implementation Plan

### 1. `scraper/models.py` — Already Done

`PolicyPage` already has the `pdf_downloads: list[str]` field.

### 2. `scraper/policies.py` — Already Done

PDF link extraction is already implemented with `_extract_pdf_links()`.

### 3. Create `scraper/pdf_download.py`

New module that handles downloading PDFs and managing the reference registry.

**Key responsibilities:**

- **Convert Google Drive URLs**: Transform `/file/d/FILE_ID/view` URLs into direct download URLs
- **Skip existing**: Check `data/policy-assets/reference.json` to avoid re-downloading
- **Save with meaningful names**: Derive filename from the URL or Content-Disposition header
- **Update reference**: Track each download with source URL, policy slug, file ID, timestamp

```python
def download_policy_pdfs(policies: list[PolicyPage], dry_run: bool = False) -> list[dict]:
    """Download PDFs from policy page links, returning download metadata."""
```

### 4. Google Drive URL Handling

Google Drive URLs come in this form:

```
https://drive.google.com/file/d/FILE_ID/view?usp=drive_link
```

**Direct download URL:**

```
https://drive.google.com/uc?export=download&id=FILE_ID
```

**For files over ~100MB:** Google Drive shows an interstitial with a `confirm=TOKEN` parameter. The download flow handles this automatically:

1. Request `uc?export=download&id=FILE_ID`
2. If response is HTML (virus scan warning), extract `confirm=TOKEN` and `uuid=UUID`
3. Re-request with `confirm=TOKEN&uuid=UUID` added

For the policy PDFs (likely <5MB each), the simple download URL should work. Handle the virus scan as a fallback.

### 5. `curl` Download Pattern

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

### 6. Reference Registry (`data/policy-assets/reference.json`)

A JSON file tracking all downloadable PDFs:


```json
{
  "downloads": {
    "FILE_ID_1": {
      "source_url": "https://drive.google.com/file/d/FILE_ID_1/view?usp=drive_link",
      "policy_slug": "abundant-energy",
      "filename": "1KgTXUgjVipAA7EcDas-EJmOr6ZkeCf9B.pdf",
      "downloaded_at": "2026-06-08T12:00:00Z",
      "size_bytes": 2644730
    }
  }
}
```

This file serves as:
- **Idempotency source**: Check if file ID already exists before downloading
- **Audit trail**: Exactly where each PDF came from
- **Manual override**: Users can add entries manually to skip a download

### 7. File Naming Convention

Downloaded PDFs are named by their Google Drive file ID (without extension) to:
- Avoid conflicts when Google Drive uses generic names like "Opportunity_Policy_Abundant Energy.pdf"
- Ensure deterministic naming based on content, not title changes

After download, rename if the original has a meaningful name in Content-Disposition.

### 8. Update `scraper/policies.py` — Output to Slug Directories

Modify `save_policies()` to write each policy's page.md into its own directory:

```python
def save_policies(policies: list[PolicyPage]) -> dict[str, Path]:
    output_dir = DATA_DIR / "policies"
    saved: dict[str, Path] = {}

    for policy in policies:
        policy_dir = output_dir / policy.slug
        md_path = save_content(
            policy_dir,
            "page.md",
            _format_policy_md(policy),
        )
        saved[policy.slug] = md_path
    # ... rest unchanged
```

### 9. Update `scraper/pdf_convert.py` — Output to Slug Directories

Modify `convert_pdf()` to write markdown into the policy's directory:

```python
def convert_pdf(pdf_path: Path, policy_slug: str) -> dict:
    # ... same extraction logic ...
    
    policy_dir = DATA_DIR / "policies" / policy_slug
    save_content(policy_dir, output_file, markdown)
    # ...
```

Also update `convert_all_pdfs()` to pass the policy slug derived from the filename pattern (`Opportunity_{Policy}_{DocType}.pdf`).

### 10. Update `main.py` — Integrate PDF Downloads

Insert the download step between scraping and PDF conversion:

```python
from scraper.pdf_download import download_policy_pdfs

def run_scrapers(...):
    # ...
    for key, entry in selected.items():
        if key == "policies":
            # First scrape policies
            policies = scrape_policies()
            save_policies(policies)
            
            # Then download any PDFs
            downloads = download_policy_pdfs(policies)
            logger.info("Downloaded %d PDFs", len(downloads))
            
            # Then convert PDFs to markdown
            results = convert_all_pdfs()
            totals["policy PDFs"] = len(results)
        elif entry is None:
            # PDF conversion only (no web scraping)
            results = convert_all_pdfs()
            totals["policy PDFs"] = len(results)
        else:
            label, scrape_fn, save_fn = entry
            items = scrape_fn()
            save_fn(items)
            totals[label] = len(items)
```

### 11. Update `scraper/client.py` — Reconcile Filenames

After a successful download, compare the new file's name with reference.json.
If we downloaded `{file_id}.pdf` but Google Drive sent it as `Opportunity_Policy_Abundant Energy.pdf`:

1. Get the Content-Disposition header to extract original filename
2. Rename the file to the original name (preserving the extension)
3. Update `reference.json` with the new filename

This preserves backward compatibility with existing conversion logic.

## Idempotency (Repeatable Scrape)

The download step is fully idempotent:

1. Before downloading, check `reference.json` for each file ID
2. If file ID exists and file is present on disk, skip
3. If file ID exists but file is missing, re-download
4. If file ID doesn't exist, download and add to reference
5. If policy has no PDF links, skip gracefully
6. If download fails, log error and continue (don't block the pipeline)

**Verification:** Running `just scrape` twice should:
- First run: Download all missing PDFs
- Second run: Skip all PDFs (already downloaded), regenerate markdown from existing files

## Migration / Backward Compatibility

For existing `data/policy-assets/` content:

1. Scan existing PDFs on first run
2. For each existing PDF without a reference.json entry, generate one with:
   - `source_url`: null (unknown)
   - `downloaded_at`: file mtime
   - `filename`: current filename

2. After migration, existing PDFs are tracked in reference.json just like new downloads.