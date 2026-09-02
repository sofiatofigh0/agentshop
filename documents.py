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
from weasyprint import CSS, HTML

# --------------------------------------------------------------------------
# Shared page setup
# --------------------------------------------------------------------------

BASE = """
@page { size: Letter; margin: 0.55in 0.6in; }
* { box-sizing: border-box; }
body { margin: 0; color: #16181d; }
a { color: inherit; text-decoration: none; }
strong { font-weight: 600; }
hr { display: none; }
"""

# --------------------------------------------------------------------------
# Resume and cover letter
# --------------------------------------------------------------------------

DOCUMENT_CSS = BASE + """
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 9.6pt;
  line-height: 1.42;
}

/* Name */
h1 {
  font-size: 21pt;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin: 0 0 3pt;
  color: #0d0f13;
}

/* The contact line directly under the name */
h1 + p {
  font-size: 8.6pt;
  color: #55595f;
  letter-spacing: 0.015em;
  margin: 0 0 13pt;
  padding-bottom: 9pt;
  border-bottom: 0.6pt solid #cfd3d8;
}

/* Section headings */
h2 {
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6a6f76;
  margin: 13pt 0 6pt;
  padding-bottom: 3pt;
  border-bottom: 0.6pt solid #dfe3e7;
  page-break-after: avoid;
}

/* Employer / role line */
h3 {
  font-size: 10.4pt;
  font-weight: 600;
  margin: 9pt 0 1pt;
  color: #0d0f13;
  page-break-after: avoid;
}

/* The meta line under a role: location, dates, title history. */
em { font-style: normal; color: #5c6169; font-size: 8.5pt; letter-spacing: 0.01em; }
h3 + p { margin: 0 0 4pt; line-height: 1.35; }

/* A one-line description of the employer, set quieter than the bullets. */
h3 + p + p { font-size: 8.9pt; color: #4a4f56; margin: 0 0 5pt; }

p { margin: 0 0 5pt; }
ul { margin: 3pt 0 8pt; padding-left: 11pt; list-style-type: disc; }
li { margin-bottom: 3.4pt; padding-left: 2pt; }
li::marker { color: #9aa0a8; }

/* Keep a role and its first bullets together */
h3, h3 + p, h3 + p + ul { page-break-inside: avoid; }
"""

# The cover letter wants prose typography, not resume density.
LETTER_CSS = BASE + """
body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 10.6pt;
  line-height: 1.62;
}
h1 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
     font-size: 17pt; font-weight: 600; letter-spacing: 0.01em; margin: 0 0 3pt; }
h1 + p { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
         font-size: 8.6pt; color: #55595f; margin: 0 0 20pt;
         padding-bottom: 10pt; border-bottom: 0.6pt solid #cfd3d8; }
p { margin: 0 0 11pt; text-align: left; }
p:last-child { margin-top: 4pt; }
"""

# --------------------------------------------------------------------------
# Internal working documents
# --------------------------------------------------------------------------

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

STYLES = {"resume": DOCUMENT_CSS, "letter": LETTER_CSS, "report": REPORT_CSS}


def write_pdf(markdown_text: str, path: str, style: str = "report") -> None:
    """Render markdown to a styled PDF.

    `style` picks the stylesheet: "resume", "letter", or "report".
    """
    body = markdown.markdown(
        markdown_text,
        # nl2br keeps a role's location/date line and its title-history line on
        # separate lines instead of collapsing them into one paragraph.
        extensions=["tables", "sane_lists", "nl2br"],
    )
    html = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"
    HTML(string=html).write_pdf(path, stylesheets=[CSS(string=STYLES[style])])
