# ADR-007: PDF generation with ReportLab

Status: Proposed

## Context

Results must be downloadable as PDF with title, metadata, summary, tables, charts and warnings. The tool runs mainly on Windows.

## Options Considered

1. **ReportLab**: pure Python, mature, precise layout, no system dependencies.
2. **WeasyPrint** (HTML to PDF): easy templating, but needs native GTK/Pango libraries, painful on Windows.
3. **Headless browser** (print notebook HTML): heavy dependency, unstable layout.
4. **fpdf2**: lightweight, but weaker tables and layout.

## Decision

ReportLab (Platypus). Charts are rendered with matplotlib to PNG. Each notebook provides a section builder that returns generic blocks (heading, paragraph, table, chart, warning); the `PdfRenderer` only renders blocks, so new notebooks need no renderer changes.

## Consequences

- No native dependencies to install.
- Layout is defined in code rather than HTML templates.
- Report code lives in `adapters/reports` behind the `ReportRenderer` port and is unit-testable by inspecting generated PDF text and page count.
