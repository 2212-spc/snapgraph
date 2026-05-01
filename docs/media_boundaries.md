# Media Boundaries

SnapGraph v0.1 is source-schema first, not media-pipeline first.

## Stable

- Markdown: `.md`, `.markdown`
- Plain text: `.txt`

These files are decoded as UTF-8, copied into `raw/notes`, summarized, written to source pages, and added to graph/SQLite.

## Experimental

- Images/screenshots: `.png`, `.jpg`, `.jpeg`, `.webp`

MockLLM produces a placeholder image description. Real vision provider behavior is not part of the stable baseline and should be evaluated separately.

## Unsupported In Stable v0.1

- PDF files
- Office files
- Video/audio
- OCR-only scanned documents

PDF ingestion should fail clearly instead of pretending nearby notes answered the PDF question.

## Evaluation Rule

MockLLM proves that the ingestion and graph schema can carry a screenshot-like source. It does not prove visual understanding.

Real LLM or a dedicated parser must be used before claiming OCR, visual QA, or PDF reading capability.
