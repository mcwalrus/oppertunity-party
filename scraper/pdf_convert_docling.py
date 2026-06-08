"""Convert policy PDFs to markdown using docling — output goes to staging/.

Replaces the pdftotext+subprocess approach in pdf_convert.py with
docling's DoclingParseDocumentBackend. Both converters write the same
output shape so the two directories can be diffed directly.

No ML model downloads are required: we use a custom pipeline that
builds layout clusters directly from the PDF's embedded text cells.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import (
    Cluster,
    InputFormat,
    LayoutPrediction,
)
from docling.datamodel.document import InputDocument
from docling.datamodel.pipeline_options import OcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.stages.layout.layout_model import LayoutModel
from docling.models.stages.ocr.auto_ocr_model import BaseOcrModel
from docling.models.stages.page_assemble.page_assemble_model import (
    PageAssembleModel,
    PageAssembleOptions,
)
from docling.models.stages.page_preprocessing.page_preprocessing_model import (
    PagePreprocessingModel,
    PagePreprocessingOptions,
)
from docling.models.stages.reading_order.readingorder_model import (
    ReadingOrderModel,
    ReadingOrderOptions,
)
from docling.models.stages.table_structure.table_structure_model import (
    TableStructureModel,
)
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling_core.types.doc.base import BoundingBox
from docling_core.types.doc.labels import DocItemLabel

from .client import DATA_DIR, save_content
from .pdf_convert import _get_policy_slug_from_reference, _slug_from_filename, _slugify

logger = logging.getLogger(__name__)

POLICY_ASSETS_DIR = DATA_DIR / "policy-assets"
REFERENCE_FILE = POLICY_ASSETS_DIR / "reference.json"
STAGING_DIR = DATA_DIR.parent / "staging"

# Same header key-value pattern the party PDFs use
HEADER_FIELD_RE = re.compile(r"^(Date|Policy|Document Type)\s{2,}(.+)$")
KNOWN_HEADER_KEYS = {"Date", "Policy", "Document Type"}


# ---------------------------------------------------------------------------
# Minimal docling pipeline — no ML model downloads
# ---------------------------------------------------------------------------

class _TextLayoutModel(LayoutModel):
    """Builds layout clusters from the PDF backend's embedded text cells."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __call__(self, conv_res, page_batch):
        for page in page_batch:
            cells = (
                page._backend.get_text_cells()
                if page._backend and page._backend.is_valid()
                else []
            )
            size = page._backend.get_size() if page._backend else None
            page_height = size.height if size else 842.0
            page.predictions.layout = _cells_to_layout(cells, page_height)
            yield page


class _NoOpOcr(BaseOcrModel):
    """Pass-through — text-native PDFs don't need OCR."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    @classmethod
    def get_options_type(cls):
        return OcrOptions

    def __call__(self, conv_res, page_batch):
        yield from page_batch


class _NoOpTable(TableStructureModel):
    """Pass-through table model."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __call__(self, conv_res, page_batch):
        yield from page_batch


class _MinimalPdfPipeline(StandardPdfPipeline):
    """Docling pipeline wired for text-native PDFs with no model downloads."""

    def _init_models(self) -> None:
        self.keep_images = False
        self.preprocessing_model = PagePreprocessingModel(
            options=PagePreprocessingOptions(
                images_scale=self.pipeline_options.images_scale
            )
        )
        self.ocr_model = _NoOpOcr()
        self.layout_model = _TextLayoutModel()
        self.table_model = _NoOpTable()
        self.assemble_model = PageAssembleModel(options=PageAssembleOptions())
        self.reading_order_model = ReadingOrderModel(options=ReadingOrderOptions())
        self.keep_backend = False
        self.enrichment_pipe = []


# Singleton — the converter and its pipeline are expensive to initialise.
_CONVERTER: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _CONVERTER
    if _CONVERTER is None:
        opts = PdfPipelineOptions()
        opts.do_ocr = False
        opts.do_table_structure = False
        _CONVERTER = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=opts,
                    pipeline_cls=_MinimalPdfPipeline,
                    backend=DoclingParseDocumentBackend,
                )
            },
        )
    return _CONVERTER


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _cells_to_layout(cells, page_height: float) -> LayoutPrediction:
    """Group text cells into line-level clusters and assign labels."""
    # Bucket cells by Y band so cells on the same visual line share a cluster
    lines: dict[int, list] = {}
    for cell in cells:
        bbox = cell.to_bounding_box()
        y_key = round(bbox.t)
        matched = next((k for k in lines if abs(k - y_key) <= 3), None)
        if matched is None:
            lines[y_key] = []
            matched = y_key
        lines[matched].append(cell)

    clusters: list[Cluster] = []
    for cid, (y_top, line_cells) in enumerate(sorted(lines.items())):
        bboxes = [c.to_bounding_box() for c in line_cells]
        bbox = BoundingBox(
            l=min(b.l for b in bboxes),
            t=min(b.t for b in bboxes),
            r=max(b.r for b in bboxes),
            b=max(b.b for b in bboxes),
        )
        texts = {c.text.strip() for c in line_cells}

        if y_top < 100:
            # Near the top of the page — header metadata or running head
            label = DocItemLabel.PAGE_HEADER
        elif y_top > page_height - 60:
            # Near the bottom — running footer ("Opportunity Party … Page N")
            label = DocItemLabel.PAGE_FOOTER
        elif texts <= {"•", "·", ""}:
            # Lone bullet marker
            label = DocItemLabel.LIST_ITEM
        elif any(t in ("•", "·") for t in texts):
            label = DocItemLabel.LIST_ITEM
        else:
            label = DocItemLabel.PARAGRAPH

        clusters.append(
            Cluster(
                id=cid,
                label=label,
                bbox=bbox,
                confidence=1.0,
                cells=line_cells,
                children=[],
            )
        )
    return LayoutPrediction(clusters=clusters)


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def _extract_metadata(pdf_path: Path) -> dict[str, str]:
    """Pull Date / Policy / Document Type from the first page's text cells.

    The party PDFs have these as labelled key-value pairs near the top of
    page 1, either as separate cells on the same line or as a single cell
    with the key and value separated by runs of spaces.
    """
    in_doc = InputDocument(
        path_or_stream=pdf_path,
        format=InputFormat.PDF,
        backend=DoclingParseDocumentBackend,
    )
    backend = DoclingParseDocumentBackend(in_doc=in_doc, path_or_stream=pdf_path)
    if backend.page_count() == 0:
        return {}

    page = backend.load_page(0)
    cells = page.get_text_cells()

    # Group cells into lines by Y band (same approach as layout clustering)
    lines: dict[int, list[str]] = {}
    for cell in cells:
        text = cell.text.strip()
        if not text:
            continue
        bbox = cell.to_bounding_box()
        y_key = round(bbox.t)
        matched = next((k for k in lines if abs(k - y_key) <= 3), None)
        if matched is None:
            lines[y_key] = []
            matched = y_key
        lines[matched].append(text)

    header: dict[str, str] = {}
    for y_top in sorted(lines.keys()):
        parts = lines[y_top]
        if not parts:
            continue
        first = parts[0]

        if first in KNOWN_HEADER_KEYS and len(parts) >= 2:
            # Two separate cells: "Date" | "February 2026"
            key = first.lower().replace(" ", "_")
            header[key] = " ".join(parts[1:])
        else:
            # Single cell: "Date                February 2026"
            joined = "  ".join(parts)
            m = HEADER_FIELD_RE.match(joined)
            if m:
                key = m.group(1).lower().replace(" ", "_")
                header[key] = m.group(2).strip()

        if len(header) == 3:
            break

    return header


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_all_pdfs_docling() -> list[dict]:
    """Find all PDFs in policy-assets and convert them via docling to staging/.

    Output mirrors the structure of data/policies/ so the two trees can
    be compared directly (e.g. with diff or a tool of your choice).
    """
    if not POLICY_ASSETS_DIR.exists():
        logger.warning("No policy-assets directory found")
        return []

    pdfs = sorted(POLICY_ASSETS_DIR.glob("*.pdf"))
    logger.info("Found %d policy PDFs to convert via docling", len(pdfs))

    results: list[dict] = []
    for pdf_path in pdfs:
        try:
            entry = convert_pdf_docling(pdf_path)
            results.append(entry)
            logger.info(
                "docling converted: %s -> %s", pdf_path.name, entry["output_file"]
            )
        except Exception as e:
            logger.error("docling failed for %s: %s", pdf_path.name, e)

    # Save combined index under staging/policies/
    index_data = [
        {
            "source_file": r["source_file"],
            "title": r["title"],
            "policy": r["policy"],
            "policy_slug": r["policy_slug"],
            "date": r["date"],
            "document_type": r["document_type"],
            "output_file": r["output_file"],
        }
        for r in results
    ]
    save_content(
        STAGING_DIR / "policies",
        "pdf-index.json",
        json.dumps(index_data, indent=2, ensure_ascii=False),
    )

    return results


def convert_pdf_docling(pdf_path: Path) -> dict:
    """Convert a single policy PDF via docling and save to staging/."""
    converter = _get_converter()
    result = converter.convert(str(pdf_path))
    body_md = result.document.export_to_markdown()

    header = _extract_metadata(pdf_path)
    markdown = _format_markdown(header, body_md, pdf_path)

    policy_slug = _get_policy_slug_from_reference(pdf_path.name) or _slug_from_filename(
        pdf_path.name
    )
    doc_type_slug = _slugify(header.get("document_type", ""))
    output_file = f"pdf-{doc_type_slug}.md" if doc_type_slug else "pdf-default.md"

    policy_dir = STAGING_DIR / "policies" / policy_slug
    save_content(policy_dir, output_file, markdown)

    return {
        "source_file": pdf_path.name,
        "title": header.get("policy", policy_slug),
        "policy": header.get("policy", ""),
        "policy_slug": policy_slug,
        "date": header.get("date", ""),
        "document_type": header.get("document_type", ""),
        "output_file": str(policy_dir / output_file),
    }


def _format_markdown(header: dict, body_md: str, pdf_path: Path) -> str:
    """Prepend a metadata table to the docling-produced markdown body."""
    policy_name = header.get("policy", "")
    doc_type = header.get("document_type", "")
    title = (
        f"{policy_name} — {doc_type}"
        if doc_type and doc_type.lower() != "policy overview"
        else policy_name
    )

    lines = [
        f"# {title}",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    for key, label in [
        ("date", "Date"),
        ("policy", "Policy"),
        ("document_type", "Document Type"),
    ]:
        if header.get(key):
            lines.append(f"| {label} | {header[key]} |")
    lines.append(f"| Source | `{pdf_path.name}` |")
    lines.append("")
    lines.append(body_md)

    return "\n".join(lines) + "\n"
