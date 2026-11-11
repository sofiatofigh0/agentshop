"""
PDF rendering.

The model writes markdown; this turns it into the finished document. Keeping
those separate matters — the writing prompts stay about content, and how a
resume looks is a styling decision made once here rather than negotiated with a
model on every run.

The resume is rendered once, by ATS_CSS: tailored_resume.pdf — one column, no
tables, bullets as text. A screening system reads a page as one stream, and
this layout is that stream.

Plus LETTER_CSS for the cover letter, and REPORT_CSS for the internal working
documents — evidence map, strategy, ATS report — which are
denser and allowed wide tables.
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

def ATS_CSS(pt, margin):
    """The upload copy: one column, in document order, nothing a parser can
    misread.

    Every rule here is about what survives text extraction. No tables, no
    floats and no columns, so the reading order is the visual order. Bullets
    are text rather than list markers, because a marker is drawn separately
    from its line and extracts as a stray character somewhere else on the
    page. Headings keep the case they were written in. Contact details sit in
    the body — nothing uses the page margins, which some parsers skip.
    Ligatures are off: with them, "fi" in an email address or a URL can be
    drawn as one glyph and extract as U+FB01, and a parser no longer
    recognises the address.
    """
    return f"""
@page {{ size: Letter; margin: {margin}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #111111;
       font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
       font-size: {pt}pt; line-height: 1.38;
       font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0; }}
a {{ color: inherit; text-decoration: none; }}
strong {{ font-weight: 700; }}

.name {{ font-size: 2.1em; font-weight: 700; margin: 0; }}
.title {{ font-size: 1.12em; font-weight: 700; margin: 0.1em 0 0.15em; }}
.contact {{ margin: 0 0 0.3em; }}

h2 {{ font-size: 1.05em; font-weight: 700; margin: 0.95em 0 0.4em;
     padding-bottom: 0.15em; border-bottom: 0.8pt solid #111111;
     page-break-after: avoid; }}

.job {{ margin-bottom: 0.7em; page-break-inside: avoid; }}
.jobhead {{ margin: 0 0 0.2em; }}
.jobdate {{ font-weight: 400; }}
.jobnote {{ font-style: italic; margin: 0 0 0.2em; }}

p {{ margin: 0 0 0.35em; }}
ul {{ list-style: none; margin: 0; padding: 0; }}
li {{ margin: 0 0 0.22em; padding-left: 1em; text-indent: -0.75em; }}
"""


def LETTER_CSS(pt, margin):
    """Cover letter styling at a given body size."""
    return BASE + f"""
@page {{ size: Letter; margin: {margin}; }}
body {{ font-family: Georgia, "Times New Roman", serif;
       font-size: {pt}pt; line-height: 1.58;
       font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0; }}
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
_RESUME_LADDER = [(9.6, "0.55in 0.6in"), (9.3, "0.5in 0.55in"), (9.0, "0.5in 0.5in"),
                  (8.7, "0.45in 0.5in"), (8.4, "0.42in 0.45in"), (8.1, "0.4in 0.45in"),
                  (7.8, "0.38in 0.42in"), (7.5, "0.35in 0.4in")]

LADDERS = {
    "resume": _RESUME_LADDER,
    "letter": [(10.8, "0.9in 0.95in"), (10.5, "0.85in 0.9in"), (10.2, "0.8in 0.85in"),
               (9.9, "0.75in 0.8in"), (9.6, "0.7in 0.75in"), (9.3, "0.65in 0.7in"),
               (9.0, "0.6in 0.7in")],
}
BUILDERS = {"resume": ATS_CSS, "letter": LETTER_CSS}


# --------------------------------------------------------------------------
# Resume markdown -> parsed sections
#
# The model writes a flat document with a known set of sections. It is parsed
# here so layout stays a decision made once, in code.
# --------------------------------------------------------------------------

def _visible_url(href: str) -> str:
    """A URL as a reader would type it: no scheme, no trailing slash."""
    return re.sub(r"^https?://(www\.)?", "", href).rstrip("/")


def _inline(text: str, show_urls: bool = False) -> str:
    """Escape, then honour **bold** and [label](href).

    With `show_urls`, a link's visible text is its address rather than its
    label. A parser reads the text, not the link behind it, so a portfolio
    link labelled "portfolio" gives it nothing to store.
    """
    out = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    if show_urls:
        out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                     lambda m: f'<a href="{m.group(2)}">{_visible_url(m.group(2))}</a>', out)
    else:
        out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def _parse_resume(md: str) -> dict:
    """Pull the resume apart into a header and a list of sections."""
    doc = {"name": "", "title": "", "contact": "", "contact_lines": [], "sections": []}
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

        # Before the first section: the title line, then the contact lines.
        # Every one is kept; a second contact line used to be dropped here.
        if section is None:
            stripped = line.strip("*")
            if line.startswith("**") and not doc["title"]:
                doc["title"] = stripped
            else:
                doc["contact_lines"].append(line)
                doc["contact"] = doc["contact"] or line
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


# --------------------------------------------------------------------------
# Resume markdown -> single column, for upload
# --------------------------------------------------------------------------

# Sections whose list is a list of terms rather than of achievements. In one
# column a term per line wastes the page, and a comma-separated line is also
# the form skills parsers split most reliably.
INLINE_LIST_SECTIONS = {"skills", "technical skills", "core skills", "key skills"}


def _ats_blocks(blocks: list, inline_lists: bool) -> str:
    html = []
    for block in blocks:
        if block["kind"] == "job":
            dates = (f'<span class="jobdate"> | {_ats_inline(block["dates"])}</span>'
                     if block["dates"] else "")
            head = f'<p class="jobhead"><strong>{_ats_inline(block["title"])}</strong>{dates}</p>'
            note = f'<p class="jobnote">{_ats_inline(block["note"])}</p>' if block["note"] else ""
            items = "".join(f"<li>\u2022 {_ats_inline(i)}</li>" for i in block["items"])
            html.append(f'<div class="job">{head}{note}'
                        + (f"<ul>{items}</ul>" if items else "") + "</div>")
        elif block["kind"] == "list" and inline_lists:
            html.append(f"<p>{', '.join(_ats_inline(i) for i in block['items'])}</p>")
        elif block["kind"] == "list":
            html.append("<ul>" + "".join(f"<li>\u2022 {_ats_inline(i)}</li>"
                                         for i in block["items"]) + "</ul>")
        else:
            html.append(f"<p>{_ats_inline(block['text'])}</p>")
    return "".join(html)


def _ats_inline(text: str) -> str:
    return _inline(text, show_urls=True)


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_WEB = re.compile(r"(?<![@\w.])(?:https?://)?(?:www\.)?"
                  r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|app|io|dev|me|net|org|co|ai)"
                  r"(?:/[^\s|()]*)?", re.I)


def _contact_html(line: str) -> str:
    """One contact line, with each email, phone and URL a real link.

    The visible text stays exactly as written, which is what a parser reads.
    The link behind it is a second copy some systems read as well: Ashby and
    others take a LinkedIn profile from the PDF's link annotations.
    """
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: _visible_url(m.group(2)), line)
    spans = []
    for pattern, href in ((_EMAIL, lambda t: "mailto:" + t),
                          (_PHONE, lambda t: "tel:" + re.sub(r"[^\d+]", "", t)),
                          (_WEB, lambda t: t if t.lower().startswith("http") else "https://" + t)):
        for m in pattern.finditer(line):
            if not any(m.start() < e and s < m.end() for s, e, _ in spans):
                spans.append((m.start(), m.end(), href(m.group(0))))
    out, at = [], 0
    for start, end, href in sorted(spans):
        out.append(_escape(line[at:start]))
        out.append(f'<a href="{_escape(href)}">{_escape(line[start:end])}</a>')
        at = end
    out.append(_escape(line[at:]))
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", "".join(out))


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_resume_ats_html(md: str) -> str:
    """Build the single-column page, sections in the order they were written."""
    doc = _parse_resume(md)
    sections = "".join(
        f'<h2>{_ats_inline(s["heading"])}</h2>'
        + _ats_blocks(s["blocks"], s["heading"].strip().lower() in INLINE_LIST_SECTIONS)
        for s in doc["sections"]
    )
    title = f'<p class="title">{_ats_inline(doc["title"])}</p>' if doc["title"] else ""
    contact = "".join(f'<p class="contact">{_contact_html(line)}</p>'
                      for line in doc["contact_lines"])
    return (
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        f'<h1 class="name">{_ats_inline(doc["name"])}</h1>{title}{contact}{sections}'
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
    builders = {"resume": render_resume_ats_html}
    html = builders.get(style, _html)(markdown_text)
    ladder, build = LADDERS[style], BUILDERS[style]
    for pt, margin in ladder:
        HTML(string=html).write_pdf(path, stylesheets=[CSS(string=build(pt, margin))])
        if page_count(path) <= max_pages:
            return page_count(path), pt
    return page_count(path), ladder[-1][0]

def page_count(path: str) -> int:
    """How many pages a rendered PDF actually came to."""
    return len(PdfReader(path).pages)
