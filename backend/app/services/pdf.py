"""B2B 트렌드 리포트 Markdown → PDF 변환 서비스.

의존성 설치:
    uv add markdown weasyprint
"""

from __future__ import annotations

import asyncio
from functools import partial

import markdown

_PDF_CSS = """
@page {
    size: A4;
    margin: 20mm 15mm;
    background-color: #ffffff;
    @bottom-center {
        content: counter(page);
        font-size: 8pt;
        color: #718096;
    }
}

*, *::before, *::after {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
}

body {
    font-family: "Noto Sans KR", "Malgun Gothic", "Apple SD Gothic Neo",
        Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #2d3748;
    background-color: #ffffff;
}

h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    page-break-inside: avoid;
    color: #1a365d;
    font-weight: 700;
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
}

h1 {
    font-size: 20pt;
    color: #1a365d;
    border-bottom: 2px solid #2b6cb0;
    padding-bottom: 0.3em;
    margin-top: 0;
}

h2 {
    font-size: 14pt;
    color: #1a365d;
    border-bottom: 1px solid #bee3f8;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 12pt;
    color: #2b6cb0;
}

p {
    margin: 0 0 0.75em 0;
    orphans: 3;
    widows: 3;
}

ul, ol {
    margin: 0 0 0.75em 0;
    padding-left: 1.5em;
}

li {
    margin-bottom: 0.25em;
}

blockquote {
    margin: 0.75em 0;
    padding: 0.5em 1em;
    border-left: 3px solid #2b6cb0;
    background-color: #f7fafc;
    color: #4a5568;
}

code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
    background-color: #edf2f7;
    padding: 0.1em 0.3em;
    border-radius: 2px;
}

pre {
    page-break-inside: avoid;
    background-color: #1a202c;
    color: #e2e8f0;
    padding: 0.75em 1em;
    border-radius: 4px;
    overflow: hidden;
    margin: 0.75em 0;
}

pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
    font-size: 8.5pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    margin: 0.75em 0 1em 0;
    page-break-inside: auto;
}

thead {
    display: table-header-group;
}

tr {
    page-break-inside: avoid;
    page-break-after: auto;
}

th, td {
    border: 1px solid #e2e8f0;
    padding: 0.45em 0.65em;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #1a365d;
    color: #ffffff;
    font-weight: 600;
}

tbody tr:nth-child(even) {
    background-color: #f7fafc;
}

tbody tr:nth-child(odd) {
    background-color: #ffffff;
}

hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.5em 0;
}

strong {
    color: #1a365d;
}

a {
    color: #2b6cb0;
    text-decoration: none;
}
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <title>B2B Trend Report</title>
    <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def _build_full_html(body_html: str) -> str:
    return _HTML_TEMPLATE.format(css=_PDF_CSS, body=body_html)


def convert_markdown_to_pdf(markdown_text: str) -> bytes:
    """Markdown 텍스트를 B2B 보고서 PDF 바이너리로 변환한다 (동기)."""
    from weasyprint import HTML  # lazy import - requires GTK system libraries

    body_html = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )
    full_html = _build_full_html(body_html)
    return HTML(string=full_html).write_pdf()


async def convert_markdown_to_pdf_async(markdown_text: str) -> bytes:
    """Markdown → PDF 변환을 스레드 풀에서 실행하여 이벤트 루프를 차단하지 않는다."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(convert_markdown_to_pdf, markdown_text),
    )
