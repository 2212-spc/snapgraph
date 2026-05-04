# Media Boundaries

SnapGraph v0.1 is source-schema first, not media-pipeline first.

## Stable

- Markdown: `.md`, `.markdown`
- Plain text: `.txt`
- HTML/webpage exports: `.html`, `.htm`

These files are decoded as UTF-8, copied into `raw/notes`, summarized, written to source pages, and added to graph/SQLite.

## Experimental

- Images/screenshots: `.png`, `.jpg`, `.jpeg`, `.webp`
- GIF/image captures: `.gif`
- PDF files: `.pdf`

MockLLM produces a placeholder image description. Real vision provider behavior is not part of the stable baseline and should be evaluated separately.

PDF capture preserves the original file and user-stated context note. When local `pdftotext` is available, SnapGraph extracts born-digital PDF text for summaries and graph context. If text extraction fails, it says so plainly and keeps the user note as the trusted context.

## Unsupported In Stable v0.1

- Office files
- Video/audio
- OCR-only scanned documents

Scanned PDFs remain unsupported unless an OCR/VLM provider explicitly reads the visual pages. SnapGraph should say when a PDF produced no usable text instead of pretending nearby notes answered the PDF content.

## Evaluation Rule

MockLLM proves that the ingestion and graph schema can carry a screenshot-like source. It does not prove visual understanding.

Real LLM or a dedicated parser must be used before claiming OCR, visual QA, or PDF reading capability.
