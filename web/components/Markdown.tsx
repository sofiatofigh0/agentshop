"use client";

/**
 * A deliberately tiny markdown renderer — headings, bold, bullets, paragraphs.
 * Enough for a resume or cover letter, and no dependency to audit.
 *
 * It escapes HTML before doing anything else, so cached or model-produced text
 * can never inject markup into the page.
 */

function escapeHtml(raw: string) {
  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function renderMarkdown(src: string): string {
  const lines = escapeHtml(src).split("\n");
  const out: string[] = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      closeList();
      continue;
    }
    const inline = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    if (t.startsWith("### ")) {
      closeList();
      out.push(`<h3>${inline.slice(4)}</h3>`);
    } else if (t.startsWith("## ")) {
      closeList();
      out.push(`<h2>${inline.slice(3)}</h2>`);
    } else if (t.startsWith("# ")) {
      closeList();
      out.push(`<h1>${inline.slice(2)}</h1>`);
    } else if (t.startsWith("- ")) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline.slice(2)}</li>`);
    } else if (/^[A-Za-z].*·/.test(t) && t.length < 90) {
      closeList();
      out.push(`<p class="meta">${inline}</p>`);
    } else {
      closeList();
      out.push(`<p>${inline}</p>`);
    }
  }
  closeList();
  return out.join("\n");
}

export default function Markdown({ source }: { source: string }) {
  return <div dangerouslySetInnerHTML={{ __html: renderMarkdown(source) }} />;
}
