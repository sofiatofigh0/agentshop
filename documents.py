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

import re

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

# --------------------------------------------------------------------------
# Resume — two-column template
#
# Geometry and colour sampled from the supplied template PDF: Letter, 0.6in
# margins, header rule at 1.38in, sidebar/main divider at 2.77in (a 30/70
# split), accent #ae1800, text #201e1d, secondary #696767, rules #d8d7d7 on a
# #f3f2f2 ground.
#
# Everything is in em so the whole sheet still scales from one number, which is
# what lets fit_pdf() land it on one page without cutting content.
# --------------------------------------------------------------------------

ACCENT, INK, MUTED, RULE, GROUND = "#ae1800", "#201e1d", "#696767", "#d8d7d7", "#f3f2f2"

# Which sections live in the narrow left column. Everything else goes right.
SIDEBAR_SECTIONS = {"profile", "summary", "skills", "education", "recognition",
                    "languages", "certifications", "awards"}


def DOCUMENT_CSS(pt, margin):
    """Resume styling at a given body size."""
    return f"""
@page {{ size: Letter; margin: {margin}; background: {GROUND}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: {GROUND}; color: {INK};
       font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
       font-size: {pt}pt; line-height: 1.4; }}
a {{ color: {ACCENT}; text-decoration: none; }}
strong {{ font-weight: 700; }}

/* ---- header ---- */
.head {{ display: table; width: 100%; }}
.head .who, .head .contact {{ display: table-cell; vertical-align: bottom; }}
.head .who {{ width: 48%; }}
.head .contact {{ text-align: right; font-size: 0.84em; color: {MUTED}; line-height: 1.55; }}
.name {{ font-size: 2.5em; font-weight: 700; letter-spacing: -0.015em;
        margin: 0; color: {INK}; white-space: nowrap; }}
.title {{ font-size: 1.02em; font-weight: 600; color: {ACCENT}; margin: 0.15em 0 0; }}
.rule {{ border-bottom: 1.1pt solid {INK}; margin: 0.75em 0 1.1em; }}

/* ---- two columns ---- */
.body {{ display: table; width: 100%; }}
.side, .main {{ display: table-cell; vertical-align: top; }}
.side {{ width: 30%; padding-right: 0.9em; }}
.main {{ border-left: 0.7pt solid {RULE}; padding-left: 1.15em; }}

/* ---- section headings ---- */
h2 {{ font-size: 0.79em; font-weight: 700; letter-spacing: 0.14em;
     text-transform: uppercase; color: {ACCENT};
     margin: 0 0 0.55em; page-break-after: avoid; }}
.side section, .main section {{ margin-bottom: 1.35em; }}
.side section:last-child, .main section:last-child {{ margin-bottom: 0; }}

/* ---- job entries ---- */
.job {{ margin-bottom: 0.95em; page-break-inside: avoid; }}
.job + .job {{ border-top: 0.7pt solid {RULE}; padding-top: 0.85em; }}
.jobhead {{ display: table; width: 100%; margin-bottom: 0.4em; }}
.jobtitle, .jobdate {{ display: table-cell; vertical-align: baseline; }}
.jobtitle {{ font-size: 1.06em; font-weight: 700; color: {INK}; line-height: 1.3; }}
.jobdate {{ text-align: right; white-space: nowrap; color: {MUTED};
           font-size: 0.88em; padding-left: 0.6em; }}
.jobnote {{ color: {MUTED}; font-size: 0.88em; margin: -0.2em 0 0.35em; }}

/* ---- text ---- */
p {{ margin: 0 0 0.5em; }}
p:last-child {{ margin-bottom: 0; }}
ul {{ margin: 0; padding-left: 1.05em; list-style-type: disc; }}
li {{ margin-bottom: 0.34em; padding-left: 0.15em; }}
li:last-child {{ margin-bottom: 0; }}
li::marker {{ color: {INK}; }}
.side li {{ margin-bottom: 0.28em; }}
.side p {{ color: {INK}; }}
.muted {{ color: {MUTED}; }}
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


# --------------------------------------------------------------------------
# Resume markdown -> two-column HTML
#
# The model writes a flat document; the template is two columns. Rather than
# ask the model to emit HTML or guess at layout, it writes a known set of
# sections and this router decides which column each one belongs in. Layout
# stays a decision made once, in code.
# --------------------------------------------------------------------------

def _inline(text: str) -> str:
    """Escape, then honour **bold** and [label](href)."""
    out = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def _parse_resume(md: str) -> dict:
    """Pull the resume apart into a header and a list of sections."""
    doc = {"name": "", "title": "", "contact": "", "sections": []}
    section = None
    job = None

    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("# "):
            doc["name"] = line[2:].strip()
            continue

        if line.startswith("## "):
            section = {"heading": line[3:].strip(), "blocks": []}
            doc["sections"].append(section)
            job = None
            continue

        # Before the first section: the title line, then the contact line.
        if section is None:
            stripped = line.strip("*")
            if line.startswith("**") and not doc["title"]:
                doc["title"] = stripped
            elif not doc["contact"]:
                doc["contact"] = line
            continue

        if line.startswith("### "):
            head = line[4:].strip()
            title, _, dates = head.rpartition("|")
            job = {"kind": "job", "title": (title or head).strip(),
                   "dates": dates.strip() if title else "", "note": "", "items": []}
            section["blocks"].append(job)
            continue

        if line.startswith(("- ", "* ")):
            item = line[2:].strip()
            if job is not None:
                job["items"].append(item)
            else:
                if not section["blocks"] or section["blocks"][-1]["kind"] != "list":
                    section["blocks"].append({"kind": "list", "items": []})
                section["blocks"][-1]["items"].append(item)
            continue

        # Plain prose. Directly under a job head it is that role's one-liner.
        if job is not None and not job["items"] and not job["note"]:
            job["note"] = line
        else:
            section["blocks"].append({"kind": "para", "text": line})

    return doc


def _render_blocks(blocks: list) -> str:
    html = []
    for block in blocks:
        if block["kind"] == "job":
            head = (f'<div class="jobhead"><span class="jobtitle">{_inline(block["title"])}</span>'
                    f'<span class="jobdate">{_inline(block["dates"])}</span></div>')
            note = f'<p class="jobnote">{_inline(block["note"])}</p>' if block["note"] else ""
            items = ("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in block["items"]) + "</ul>"
                     if block["items"] else "")
            html.append(f'<div class="job">{head}{note}{items}</div>')
        elif block["kind"] == "list":
            html.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in block["items"]) + "</ul>")
        else:
            html.append(f"<p>{_inline(block['text'])}</p>")
    return "".join(html)


def render_resume_html(md: str) -> str:
    """Build the two-column resume page."""
    doc = _parse_resume(md)

    side, main = [], []
    for section in doc["sections"]:
        target = side if section["heading"].strip().lower() in SIDEBAR_SECTIONS else main
        target.append(f'<section><h2>{_inline(section["heading"])}</h2>'
                      f'{_render_blocks(section["blocks"])}</section>')

    title = f'<p class="title">{_inline(doc["title"])}</p>' if doc["title"] else ""
    contact = f'<div class="contact">{_inline(doc["contact"])}</div>' if doc["contact"] else ""

    return (
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        f'<div class="head"><div class="who"><h1 class="name">{_inline(doc["name"])}</h1>'
        f'{title}</div>{contact}</div><div class="rule"></div>'
        f'<div class="body"><div class="side">{"".join(side)}</div>'
        f'<div class="main">{"".join(main)}</div></div>'
        "</body></html>"
    )


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
    html = render_resume_html(markdown_text) if style == "resume" else _html(markdown_text)
    ladder, build = LADDERS[style], BUILDERS[style]
    for pt, margin in ladder:
        HTML(string=html).write_pdf(path, stylesheets=[CSS(string=build(pt, margin))])
        if page_count(path) <= max_pages:
            return page_count(path), pt
    return page_count(path), ladder[-1][0]

def page_count(path: str) -> int:
    """How many pages a rendered PDF actually came to."""
    return len(PdfReader(path).pages)
