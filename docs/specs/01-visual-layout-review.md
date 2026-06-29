# TongTong Slice #01 Visual Layout Review

Status: manual rendered-layout QA artifact.

Date: 2026-06-26.

Representative document:
`.visual-qa/psych-bfi-report/psych-bfi-report.docx`

Source workflow:

- Public R `psych`/Rdatasets `bfi` fixture.
- CSV import.
- Reverse-code `A1` on the 1-6 scale.
- Compose Agreeableness from `A1_R, A2, A3, A4, A5`.
- Reliability analysis.
- Welch two-group comparison by `gender`.
- Korean APA report generation.

## Renderer path

The bundled LibreOffice-based `render_docx.py` path was attempted first, but
LibreOffice/`soffice` was not available on PATH in this Windows environment.

Fallback renderer used:

1. Microsoft Word COM automation exported the generated docx to:
   `.visual-qa/psych-bfi-report/psych-bfi-report-word.pdf`
2. `pypdfium2` rendered that PDF to page PNGs:
   - `.visual-qa/psych-bfi-report/word-rendered/page-1.png`
   - `.visual-qa/psych-bfi-report/word-rendered/page-2.png`

## Visual inspection result

Page count: 2.

Page 1:

- Title and prose render inside page margins.
- Korean and Greek symbols render correctly.
- Reliability and comparison tables are readable.
- No visible clipping, overlap, broken rows, or missing glyphs.

Page 2:

- Reliability figure renders within page bounds.
- Comparison figure renders within page bounds.
- Axis labels and tick labels are readable.
- No visible clipping, overlap, broken image embedding, or missing glyphs.

## Limitations

This review verifies rendered layout defects for the representative Slice #01
APA report. It is not a full visual-design redesign. The current document uses
a simple Word-style APA report layout; that is acceptable for Slice #01 because
the slice spec explicitly keeps broader visual design out of scope.

## Conclusion

The representative generated docx passed page-level rendered-layout QA using
the Word-to-PDF-to-PNG fallback renderer in this environment.
