# OCR fixtures

`thai-policy-scan.pdf` is a synthetic, high-contrast image-only PDF with Thai and English text.
`thai-policy-scan.txt` is its manually specified expected transcription. It contains no customer data.

The bitmap was rendered using macOS AppKit with the system Thonburi font and placed in a PDF as
an image, without a searchable text layer. No font files are distributed. This is a clean regression
fixture, not a representative benchmark of photographed, skewed, low-resolution or handwritten documents.

OCR is checked with the actual Poppler/Tesseract installation in the backend image. The tests preserve
page provenance, require key policy phrases and the amount, and compare character error rate after
Unicode NFC normalization and removing whitespace. A small CER allowance captures the observed stray
characters without silently deleting output from real user documents.
