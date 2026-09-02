"""
PDF rendering.

The model writes markdown; this turns it into the finished document. Keeping
those separate matters — the writing prompts stay about content, and how a
resume looks is a styling decision made once here rather than negotiated with a
model on every run.

Two stylesheets:

    DOCUMENT_CSS  resume and cover letter — the things an employer receives.
                  Typeset to look like a professional document, not a rendered
                  README.
    REPORT_CSS    evidence map, factuality review, strategy — internal working
                  documents. Denser, tables allowed to be wide.
"""

import markdown
from pypdf import PdfReader
from weasyprint import CSS, HTML

# --------------------------------------------------------------------------
# Shared page setup
# --------------------------------------------------------------------------

BASE = """
@page { size: Letter; margin: 0.5in 0.55in; }
* { box-sizing: border-box; }
body { margin: 0; color: #16181d; }
a { color: inherit; text-decoration: none; }
strong { font-weight: 600; }
hr { display: none; }
"""

# --------------------------------------------------------------------------
# Resume and cover letter
# --------------------------------------------------------------------------

def DOCUMENT_CSS(pt, margin):
    """Resume styling at a given body size.

    Every dimension is expressed in em so the whole document scales from one
    number. That is what lets fit_pdf() shrink a resume onto one page without
    removing a single word.
    """
    return BASE + f"""
@page {{ size: Letter; margin: {margin}; }}
body {{
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: {pt}pt;
  line-height: 1.38;
}}
h1 {{ font-size: 2.05em; font-weight: 600; letter-spacing: 0.02em;
     margin: 0 0 0.3em; color: #0d0f13; }}
h1 + p {{ font-size: 0.9em; color: #55595f; letter-spacing: 0.015em;
         margin: 0 0 1.3em; padding-bottom: 0.9em;
         border-bottom: 0.6pt solid #cfd3d8; }}
h2 {{ font-size: 0.84em; font-weight: 700; letter-spacing: 0.14em;
     text-transform: uppercase; color: #6a6f76; margin: 1.15em 0 0.5em;
     padding-bottom: 0.25em; border-bottom: 0.6pt solid #dfe3e7;
     page-break-after: avoid; }}
h3 {{ font-size: 1.11em; font-weight: 600; margin: 0.85em 0 0.1em;
     color: #0d0f13; page-break-after: avoid; }}
em {{ font-style: normal; color: #5c6169; font-size: 0.9em; letter-spacing: 0.01em; }}
h3 + p {{ margin: 0 0 0.4em; line-height: 1.32; }}
h3 + p + p {{ font-size: 0.95em; color: #4a4f56; margin: 0 0 0.5em; }}
p {{ margin: 0 0 0.5em; }}
ul {{ margin: 0.25em 0 0.62em; padding-left: 1.15em; list-style-type: disc; }}
li {{ margin-bottom: 0.3em; padding-left: 0.2em; }}
li::marker {{ color: #9aa0a8; }}
h3, h3 + p, h3 + p + ul {{ page-break-inside: avoid; }}
"""


def LETTER_CSS(pt, margin):
    """Cover letter styling at a given body size."""
    return BASE + f"""
@page {{ size: Letter; margin: {margin}; }}
body {{ font-family: Georgia, "Times New Roman", serif;
       font-size: {pt}pt; line-height: 1.58; }}
h1 {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
     font-size: 1.6em; font-weight: 600; letter-spacing: 0.01em; margin: 0 0 0.25em; }}
h1 + p {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
         font-size: 0.81em; color: #55595f; margin: 0 0 1.7em;
         padding-bottom: 0.85em; border-bottom: 0.6pt solid #cfd3d8; }}
p {{ margin: 0 0 0.95em; text-align: left; }}
p:last-child {{ margin-top: 0.35em; }}
"""


REPORT_CSS = BASE + """
@page { size: Letter landscape; margin: 0.45in; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
       font-size: 8.4pt; line-height: 1.42; }
h1 { font-size: 15pt; font-weight: 600; margin: 0 0 8pt; }
h2 { font-size: 9.5pt; font-weight: 700; letter-spacing: 0.09em;
     text-transform: uppercase; color: #6a6f76; margin: 12pt 0 5pt;
     padding-bottom: 3pt; border-bottom: 0.6pt solid #dfe3e7; page-break-after: avoid; }
h3 { font-size: 9.4pt; font-weight: 600; margin: 8pt 0 3pt; }
p { margin: 0 0 5pt; }
ul { margin: 3pt 0 6pt; padding-left: 13pt; }
li { margin-bottom: 2.6pt; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 9pt;
        font-size: 7.5pt; page-break-inside: auto; }
th { background: #f2f4f6; text-align: left; font-size: 6.8pt; font-weight: 700;
     letter-spacing: 0.07em; text-transform: uppercase; color: #55595f;
     padding: 4pt 5pt; border: 0.5pt solid #d8dce1; }
td { padding: 4pt 5pt; border: 0.5pt solid #e3e7eb; vertical-align: top; }
tr { page-break-inside: avoid; }
code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 7.4pt; }
"""

# Density ladders, loosest first. fit_pdf walks down until the document lands
# on one page. It never removes content — it only tightens the setting.
LADDERS = {
    "resume": [(9.6, "0.55in 0.6in"), (9.3, "0.5in 0.55in"), (9.0, "0.5in 0.5in"),
               (8.7, "0.45in 0.5in"), (8.4, "0.42in 0.45in"), (8.1, "0.4in 0.45in"),
               (7.8, "0.38in 0.42in"), (7.5, "0.35in 0.4in")],
    "letter": [(10.8, "0.9in 0.95in"), (10.5, "0.85in 0.9in"), (10.2, "0.8in 0.85in"),
               (9.9, "0.75in 0.8in"), (9.6, "0.7in 0.75in"), (9.3, "0.65in 0.7in"),
               (9.0, "0.6in 0.7in")],
}
BUILDERS = {"resume": DOCUMENT_CSS, "letter": LETTER_CSS}


def _html(markdown_text: str) -> str:
    body = markdown.markdown(
        markdown_text,
        # nl2br keeps a role's location/date line and its title-history line on
        # separate lines instead of collapsing them into one paragraph.
        extensions=["tables", "sane_lists", "nl2br"],
    )
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"


def write_pdf(markdown_text, path, style="report"):
    """Render an internal report. No length constraint."""
    HTML(string=_html(markdown_text)).write_pdf(path, stylesheets=[CSS(string=REPORT_CSS)])


def fit_pdf(markdown_text, path, style, max_pages=1):
    """Render a document, tightening the typography until it fits.

    Returns (pages, body_pt). Content is never altered — if even the tightest
    setting overruns, the document is left there and the caller is told.
    """
    html = _html(markdown_text)
    ladder, build = LADDERS[style], BUILDERS[style]
    for pt, margin in ladder:
        HTML(string=html).write_pdf(path, stylesheets=[CSS(string=build(pt, margin))])
        if page_count(path) <= max_pages:
            return page_count(path), pt
    return page_count(path), ladder[-1][0]

def page_count(path: str) -> int:
    """How many pages a rendered PDF actually came to."""
    return len(PdfReader(path).pages)
