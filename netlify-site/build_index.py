#!/usr/bin/env python3
"""Generates index.html from docs — run from repo: python3 build_index.py"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DOCS = ROOT / "docs"


def prefix_css_block(css: str, pid: str) -> str:
    lines = css.split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if s.startswith("@keyframes"):
            depth = 0
            while i < n:
                ln = lines[i]
                out.append(ln)
                depth += ln.count("{") - ln.count("}")
                i += 1
                if depth <= 0:
                    break
            continue
        if s.startswith(":root"):
            depth = 0
            while i < n:
                ln = lines[i]
                out.append(ln)
                depth += ln.count("{") - ln.count("}")
                i += 1
                if depth <= 0:
                    break
            continue
        if not s:
            out.append(line)
            i += 1
            continue
        if s.endswith("{"):
            if s.startswith("@media"):
                out.append(line)
                i += 1
                continue
            if s == "* {":
                out.append(line.replace("* {", f"{pid} * {{"))
                i += 1
                continue
            if s == "body {":
                out.append(line.replace("body {", f"{pid} {{"))
                i += 1
                continue
            if s == "html {":
                out.append(line.replace("html {", f"{pid} {{"))
                i += 1
                continue
            if s.startswith("defs "):
                out.append("    " + pid + " " + s)
                i += 1
                continue
            sel = s[:-1].strip()
            if "," in sel:
                parts = [p.strip() for p in sel.split(",")]
                fixed = ", ".join(pid + " " + p for p in parts)
                indent = line[: len(line) - len(line.lstrip())]
                out.append(indent + fixed + " {")
            else:
                out.append(line.replace(sel + " {", pid + " " + sel + " {", 1))
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def terms_to_glossary_html(md: str) -> str:
    first = md.find("## GitHub")
    if first > 0:
        md = md[first:]
    sections = re.split(r"^##\s+", md, flags=re.MULTILINE)[1:]
    html_parts = []

    def fmt_inline(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
        return s

    for block in sections:
        lines = block.strip().split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:])
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        entries = re.split(r"\n###\s+", body)
        intro = entries[0].strip()
        entry_html = []
        for ent in entries[1:]:
            elines = ent.split("\n", 1)
            term_title = elines[0].strip()
            term_title = re.sub(r"\*\*(.+?)\*\*", r"\1", term_title)
            term_body = elines[1] if len(elines) > 1 else ""
            paras = re.split(r"\n---\s*\n", term_body)
            inner = []
            for p in paras:
                p = p.strip()
                if not p:
                    continue
                inner.append("<p>" + fmt_inline(p).replace("\n\n", "</p><p>") + "</p>")
            tid = re.sub(r"[^a-z0-9\s]", "", term_title.lower())
            entry_html.append(
                f'<article class="glossary-term" data-term="{tid}" data-cat="{slug}">'
                f'<h4 class="glossary-term-title">{fmt_inline(term_title)}</h4>'
                f'<div class="glossary-term-body">{"".join(inner)}</div></article>'
            )
        intro_html = ""
        if intro and not intro.startswith("|"):
            intro_html = '<p class="glossary-cat-intro">' + fmt_inline(intro) + "</p>"
        html_parts.append(
            f'<section class="glossary-category" id="cat-{slug}" data-category="{title}">'
            f'<h3 class="glossary-cat-title">{title}</h3>{intro_html}'
            f'<div class="glossary-terms">{"".join(entry_html)}</div></section>'
        )
    return "\n".join(html_parts)


def guide_md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    i = 0
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        r = ""
        if in_ul:
            r += "</ul>"
            in_ul = False
        if in_ol:
            r += "</ol>"
            in_ol = False
        return r

    def fmt_inline(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        return s

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and "|" in line[1:]:
            out.append(close_lists())
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) < 2:
                continue

            def parse_row(r):
                return [c.strip() for c in r.split("|")[1:-1]]

            header = rows[0]
            hcells = parse_row(header)
            out.append('<div class="guide-table-wrap"><table class="guide-table"><thead><tr>')
            for c in hcells:
                out.append(f"<th>{fmt_inline(c)}</th>")
            out.append("</tr></thead><tbody>")
            for r in rows[2:]:
                if re.match(r"^\|[\s\-:|]+\|$", r):
                    continue
                cells = parse_row(r)
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{fmt_inline(c)}</td>")
                out.append("</tr>")
            out.append("</tbody></table></div>")
            continue
        if line.strip() == "---":
            out.append(close_lists() + '<hr class="guide-hr" />')
            i += 1
            continue
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            out.append(close_lists() + f'<h2 class="guide-h2">{fmt_inline(m.group(1))}</h2>')
            i += 1
            continue
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            out.append(close_lists() + f'<h3 class="guide-h3">{fmt_inline(m.group(1))}</h3>')
            i += 1
            continue
        if line.startswith(">"):
            out.append(close_lists())
            qlines = []
            while i < len(lines) and lines[i].startswith(">"):
                qlines.append(lines[i][1:].lstrip())
                i += 1
            out.append('<blockquote class="guide-bq">' + fmt_inline(" ".join(qlines)) + "</blockquote>")
            continue
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            if not in_ol:
                out.append(close_lists())
                out.append('<ol class="guide-ol">')
                in_ol = True
            out.append(f"<li>{fmt_inline(m.group(2))}</li>")
            i += 1
            continue
        else:
            if in_ol:
                out.append("</ol>")
                in_ol = False
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            if not in_ul:
                out.append(close_lists())
                out.append('<ul class="guide-ul">')
                in_ul = True
            out.append(f"<li>{fmt_inline(m.group(1))}</li>")
            i += 1
            continue
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
        if line.strip() == "":
            i += 1
            continue
        out.append(close_lists())
        paras = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith("|") and not lines[i].startswith(">") and not re.match(r"^(\d+)\.", lines[i]) and not re.match(r"^[-*]\s", lines[i]) and lines[i].strip() != "---":
            paras.append(lines[i])
            i += 1
        ptext = " ".join(paras)
        out.append('<p class="guide-p">' + fmt_inline(ptext) + "</p>")
    out.append(close_lists())
    html = "\n".join(out)
    html = html.replace(
        '<p class="guide-p"># Usage Guide — AI Code Review Bot</p>',
        '<h1 class="guide-h1">Usage Guide — AI Code Review Bot</h1>',
    )
    html = html.replace('href="./TERMS.md"', 'href="#terms" class="guide-internal-link"')
    return html


def main():
    arch_html = (DOCS / "architecture-diagram.html").read_text()
    flow_html = (DOCS / "flow-diagram.html").read_text()
    arch_css = prefix_css_block(re.search(r"<style>([\s\S]*?)</style>", arch_html).group(1), "#panel-architecture")
    flow_css = prefix_css_block(re.search(r"<style>([\s\S]*?)</style>", flow_html).group(1), "#panel-flow")
    arch_css = re.sub(r"^\s*:root\s*\{[\s\S]*?\n\s*\}\s*\n", "", arch_css, count=1)
    flow_css = re.sub(r"^\s*:root\s*\{[\s\S]*?\n\s*\}\s*\n", "", flow_css, count=1)
    arch_css = arch_css.replace("var(--border)", "var(--border-arch)")
    arch_css = arch_css.replace(
        """defs marker#arrowGreen polyline,
    defs marker#arrowBlue polyline,
    defs marker#arrowPurple polyline,
    #panel-architecture defs marker#arrowOrange polyline""",
        """#panel-architecture defs marker#arrowGreen polyline,
    #panel-architecture defs marker#arrowBlue polyline,
    #panel-architecture defs marker#arrowPurple polyline,
    #panel-architecture defs marker#arrowOrange polyline""",
    )
    flow_css = flow_css.replace('--font-body: "Outfit"', '--font-body: "DM Sans"')
    flow_css = re.sub(
        r"#panel-flow \{\s*scroll-behavior:\s*smooth;\s*\}\s*\n\s*#panel-flow \{",
        "#panel-flow {\n      scroll-behavior: smooth;",
        flow_css,
    )

    start = arch_html.find('<div class="wrap">')
    end = arch_html.find("<script>", start)
    arch_body = arch_html[start:end].rstrip()

    start = flow_html.find('<div class="wrap">')
    end = flow_html.find("<script>", start)
    flow_body = flow_html[start:end].rstrip()

    glossary = terms_to_glossary_html((DOCS / "TERMS.md").read_text())
    guide = guide_md_to_html((DOCS / "USAGE_GUIDE.md").read_text())

    arch_script = re.search(r"<script>([\s\S]*?)</script>", arch_html).group(1)
    flow_script = re.search(r"<script>([\s\S]*?)</script>", flow_html).group(1)

    merged_root = """
    :root {
      --bg-deep: #070a12;
      --bg-panel: #0d121f;
      --bg-card: #12192a;
      --border-arch: rgba(148, 163, 184, 0.12);
      --border: rgba(255, 255, 255, 0.08);
      --text-main: #e8edf7;
      --muted-arch: #94a3b8;
      --accent: #38bdf8;
      --github: #22c55e;
      --github-dim: rgba(34, 197, 94, 0.15);
      --ai: #a855f7;
      --ai-dim: rgba(168, 85, 247, 0.15);
      --infra: #3b82f6;
      --infra-dim: rgba(59, 130, 246, 0.15);
      --frontend: #f97316;
      --frontend-dim: rgba(249, 115, 22, 0.15);
      --glow-github: rgba(34, 197, 94, 0.45);
      --glow-ai: rgba(168, 85, 247, 0.45);
      --glow-infra: rgba(59, 130, 246, 0.45);
      --glow-frontend: rgba(249, 115, 22, 0.45);
      --bg: #07080d;
      --bg-elevated: #0f1118;
      --border: rgba(255, 255, 255, 0.08);
      --text: #e8eaef;
      --muted: #8b92a8;
      --blue: #3b8cff;
      --blue-dim: rgba(59, 140, 255, 0.15);
      --purple: #b366ff;
      --purple-dim: rgba(179, 102, 255, 0.15);
      --green: #34d399;
      --green-dim: rgba(52, 211, 153, 0.15);
      --orange: #fb923c;
      --orange-dim: rgba(251, 146, 60, 0.15);
      --teal: #2dd4bf;
      --teal-dim: rgba(45, 212, 191, 0.15);
      --danger: #f87171;
      --diamond: #94a3b8;
      --line: rgba(148, 163, 184, 0.45);
      --pulse-glow: rgba(59, 140, 255, 0.55);
      --font-display: "Syne", system-ui, sans-serif;
      --font-body: "DM Sans", system-ui, sans-serif;
      --nav-h: 64px;
    }
"""

    site_css = r"""
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--font-body);
      background: var(--bg-deep);
      color: var(--text-main);
      line-height: 1.5;
      overflow-x: hidden;
    }
    .site-noise {
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.035;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
      z-index: 0;
    }
    .site-shell { position: relative; z-index: 1; }
    .site-nav {
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      gap: 0.35rem;
      padding: 0.65rem clamp(0.75rem, 2vw, 1.5rem);
      background: rgba(7, 10, 18, 0.82);
      backdrop-filter: blur(16px) saturate(1.2);
      border-bottom: 1px solid rgba(148, 163, 184, 0.1);
      box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    .site-nav button {
      font-family: var(--font-body);
      font-size: 0.8125rem;
      font-weight: 600;
      padding: 0.5rem 0.95rem;
      border-radius: 999px;
      border: 1px solid transparent;
      background: transparent;
      color: var(--muted-arch);
      cursor: pointer;
      transition: color 0.2s, background 0.2s, transform 0.15s, box-shadow 0.2s;
    }
    .site-nav button:hover {
      color: #e2e8f0;
      background: rgba(56, 189, 248, 0.08);
    }
    .site-nav button.is-active {
      color: #f8fafc;
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(168, 85, 247, 0.18));
      border-color: rgba(56, 189, 248, 0.35);
      box-shadow: 0 0 24px rgba(56, 189, 248, 0.15);
    }
    .site-main { min-height: calc(100vh - var(--nav-h)); }
    .tab-panel {
      display: none;
      animation: tabEnter 0.45s ease forwards;
    }
    .tab-panel.is-active { display: block; }
    @keyframes tabEnter {
      from { opacity: 0; transform: translateY(14px); }
      to { opacity: 1; transform: translateY(0); }
    }
    #panel-architecture .noise, #panel-flow .noise { display: none !important; }

    /* Overview */
    .overview-inner {
      max-width: 1120px;
      margin: 0 auto;
      padding: clamp(1.5rem, 4vw, 3.5rem) clamp(1rem, 3vw, 2rem) 4rem;
    }
    .hero {
      text-align: center;
      margin-bottom: 2.75rem;
    }
    .hero-badge {
      display: inline-block;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #7dd3fc;
      margin-bottom: 1rem;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      border: 1px solid rgba(56, 189, 248, 0.25);
      background: rgba(56, 189, 248, 0.08);
    }
    .hero-title {
      font-family: var(--font-display);
      font-weight: 800;
      font-size: clamp(2.1rem, 6vw, 3.35rem);
      letter-spacing: -0.04em;
      line-height: 1.05;
      margin: 0 0 1rem;
      background: linear-gradient(120deg, #f8fafc 0%, #94a3b8 35%, #38bdf8 55%, #a855f7 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .hero-tagline {
      font-size: clamp(1rem, 2.2vw, 1.2rem);
      color: var(--muted-arch);
      max-width: 42rem;
      margin: 0 auto 2rem;
    }
    .hero-stats {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 0.75rem 1.25rem;
    }
    .hero-stat {
      padding: 0.65rem 1.1rem;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid rgba(148, 163, 184, 0.12);
      font-size: 0.85rem;
    }
    .hero-stat strong { color: #7dd3fc; font-weight: 700; }
    .feature-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 2.5rem;
    }
    .feature-card {
      padding: 1.35rem 1.25rem;
      border-radius: 16px;
      background: linear-gradient(155deg, rgba(15,23,42,0.9), rgba(7,10,18,0.95));
      border: 1px solid rgba(148, 163, 184, 0.1);
      transition: transform 0.25s ease, border-color 0.25s, box-shadow 0.3s;
    }
    .feature-card:hover {
      transform: translateY(-4px);
      border-color: rgba(56, 189, 248, 0.35);
      box-shadow: 0 20px 50px rgba(0,0,0,0.4), 0 0 40px rgba(56, 189, 248, 0.08);
    }
    .feature-card h3 {
      font-family: var(--font-display);
      font-size: 1.05rem;
      font-weight: 700;
      margin: 0 0 0.5rem;
      color: #f1f5f9;
    }
    .feature-card p {
      margin: 0;
      font-size: 0.88rem;
      color: var(--muted-arch);
    }
    .feature-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: grid;
      place-items: center;
      margin-bottom: 0.85rem;
      font-size: 1.15rem;
    }
    .feature-card:nth-child(1) .feature-icon { background: rgba(168, 85, 247, 0.2); }
    .feature-card:nth-child(2) .feature-icon { background: rgba(56, 189, 248, 0.2); }
    .feature-card:nth-child(3) .feature-icon { background: rgba(34, 197, 94, 0.2); }
    .feature-card:nth-child(4) .feature-icon { background: rgba(249, 115, 22, 0.2); }
    .stack-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 0.5rem;
      margin-bottom: 2.75rem;
    }
    .stack-badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.4rem 0.85rem;
      border-radius: 8px;
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(148, 163, 184, 0.15);
      color: #cbd5e1;
    }
    .how-section h2 {
      font-family: var(--font-display);
      text-align: center;
      font-size: 1.35rem;
      font-weight: 800;
      margin: 0 0 1.75rem;
      color: #e2e8f0;
    }
    .how-steps {
      display: flex;
      flex-wrap: wrap;
      align-items: stretch;
      justify-content: center;
      gap: 1rem;
      max-width: 900px;
      margin: 0 auto;
    }
    .how-step {
      flex: 1 1 200px;
      max-width: 280px;
      padding: 1.25rem 1.1rem;
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid rgba(56, 189, 248, 0.15);
      text-align: center;
      position: relative;
    }
    .how-step-num {
      font-family: var(--font-display);
      font-weight: 800;
      font-size: 0.75rem;
      color: #38bdf8;
      letter-spacing: 0.08em;
      margin-bottom: 0.5rem;
    }
    .how-step h4 {
      margin: 0 0 0.35rem;
      font-size: 1rem;
      font-weight: 700;
    }
    .how-step p {
      margin: 0;
      font-size: 0.82rem;
      color: var(--muted-arch);
    }
    .how-connector {
      display: none;
      color: #64748b;
      font-size: 1.5rem;
      align-self: center;
    }
    @media (min-width: 900px) {
      .how-steps { flex-wrap: nowrap; }
      .how-connector { display: block; }
    }

    /* Terms */
    #panel-terms .terms-inner { max-width: 900px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
    .glossary-head { text-align: center; margin-bottom: 2rem; }
    .glossary-head h1 {
      font-family: var(--font-display);
      font-weight: 800;
      font-size: clamp(1.75rem, 4vw, 2.25rem);
      margin: 0 0 0.5rem;
      background: linear-gradient(135deg, #f8fafc, #7dd3fc);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .glossary-head p { color: var(--muted-arch); margin: 0; font-size: 0.95rem; }
    .glossary-controls {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .glossary-search-wrap { position: relative; }
    .glossary-search-wrap input {
      width: 100%;
      padding: 0.85rem 1rem 0.85rem 2.75rem;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.2);
      background: rgba(15, 23, 42, 0.6);
      color: #f1f5f9;
      font-family: var(--font-body);
      font-size: 0.95rem;
    }
    .glossary-search-wrap input::placeholder { color: #64748b; }
    .glossary-search-wrap input:focus {
      outline: none;
      border-color: rgba(56, 189, 248, 0.5);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.12);
    }
    .glossary-search-wrap::before {
      content: "⌕";
      position: absolute;
      left: 1rem;
      top: 50%;
      transform: translateY(-50%);
      color: #64748b;
      font-size: 1.1rem;
    }
    .glossary-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      justify-content: center;
    }
    .glossary-filters button {
      font-family: var(--font-body);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.4rem 0.75rem;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.2);
      background: rgba(15, 23, 42, 0.5);
      color: var(--muted-arch);
      cursor: pointer;
      transition: all 0.2s;
    }
    .glossary-filters button.is-on {
      border-color: rgba(168, 85, 247, 0.45);
      background: rgba(168, 85, 247, 0.12);
      color: #e9d5ff;
    }
    .glossary-category { margin-bottom: 2.5rem; scroll-margin-top: calc(var(--nav-h) + 12px); }
    .glossary-cat-title {
      font-family: var(--font-display);
      font-size: 1.1rem;
      font-weight: 800;
      color: #a5b4fc;
      margin: 0 0 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    }
    .glossary-cat-intro { color: var(--muted-arch); font-size: 0.9rem; margin-bottom: 1rem; }
    .glossary-term {
      padding: 1rem 1.1rem;
      margin-bottom: 0.75rem;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(148, 163, 184, 0.08);
    }
    .glossary-term.is-hidden { display: none !important; }
    .glossary-term-title {
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 700;
      margin: 0 0 0.5rem;
      color: #f1f5f9;
    }
    .glossary-term-body { font-size: 0.88rem; color: var(--muted-arch); }
    .glossary-term-body p { margin: 0 0 0.65rem; }
    .glossary-term-body p:last-child { margin-bottom: 0; }
    .glossary-term-body code { font-size: 0.85em; background: rgba(0,0,0,0.35); padding: 0.1rem 0.35rem; border-radius: 4px; color: #7dd3fc; }

    /* Guide */
    #panel-guide .guide-inner {
      max-width: 820px;
      margin: 0 auto;
      padding: 2rem 1.25rem 4rem;
    }
    .guide-h1 {
      font-family: var(--font-display);
      font-weight: 800;
      font-size: clamp(1.75rem, 4vw, 2.15rem);
      margin: 0 0 1rem;
      background: linear-gradient(135deg, #f8fafc, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .guide-h2 {
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 800;
      margin: 2.25rem 0 1rem;
      color: #e2e8f0;
      padding-top: 0.5rem;
      border-top: 1px solid rgba(148, 163, 184, 0.12);
    }
    .guide-inner .guide-h2:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
    .guide-h3 {
      font-size: 1.05rem;
      font-weight: 700;
      margin: 1.5rem 0 0.75rem;
      color: #cbd5e1;
    }
    .guide-p { margin: 0 0 1rem; color: var(--muted-arch); font-size: 0.95rem; }
    .guide-p strong, .guide-bq strong { color: #e2e8f0; }
    .guide-ul, .guide-ol { margin: 0 0 1rem; padding-left: 1.35rem; color: var(--muted-arch); font-size: 0.92rem; }
    .guide-ul li, .guide-ol li { margin-bottom: 0.4rem; }
    .guide-bq {
      margin: 1rem 0;
      padding: 1rem 1.15rem;
      border-left: 3px solid rgba(56, 189, 248, 0.45);
      background: rgba(56, 189, 248, 0.06);
      border-radius: 0 10px 10px 0;
      font-size: 0.9rem;
      color: #94a3b8;
    }
    .guide-hr { border: none; height: 1px; background: rgba(148, 163, 184, 0.12); margin: 2rem 0; }
    .guide-table-wrap { overflow-x: auto; margin: 1rem 0 1.5rem; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.12); }
    .guide-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .guide-table th, .guide-table td {
      padding: 0.65rem 0.85rem;
      text-align: left;
      border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }
    .guide-table th {
      background: rgba(15, 23, 42, 0.8);
      color: #cbd5e1;
      font-family: var(--font-display);
      font-weight: 700;
      font-size: 0.78rem;
    }
    .guide-table tr:last-child td { border-bottom: none; }
    .guide-table td { color: var(--muted-arch); }
    .guide-table code { font-size: 0.8em; }
    .guide-internal-link { color: #7dd3fc; text-decoration: none; border-bottom: 1px solid rgba(56, 189, 248, 0.35); }
    .guide-internal-link:hover { color: #bae6fd; }
"""

    overview_html = r"""
    <div class="overview-inner">
      <header class="hero">
        <span class="hero-badge">Portfolio · Open architecture</span>
        <h1 class="hero-title">AI Code Review Bot</h1>
        <p class="hero-tagline">Automated pull-request reviews with parallel Claude agents, structured findings, and a real-time dashboard—wired natively into GitHub.</p>
        <div class="hero-stats" role="list">
          <div class="hero-stat" role="listitem"><strong>4</strong> specialized AI agents</div>
          <div class="hero-stat" role="listitem"><strong>Real-time</strong> dashboard &amp; SSE</div>
          <div class="hero-stat" role="listitem"><strong>GitHub</strong> webhooks &amp; inline comments</div>
        </div>
      </header>
      <div class="feature-grid">
        <article class="feature-card">
          <div class="feature-icon" aria-hidden="true">◆</div>
          <h3>4 AI Agents</h3>
          <p>Color &amp; constants, logic &amp; bugs, best practices, and OWASP-style security—run in parallel for fast wall-clock reviews.</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon" aria-hidden="true">⚡</div>
          <h3>Real-time Reviews</h3>
          <p>Celery workers process PRs asynchronously; Redis pub/sub and SSE keep the dashboard in sync as reviews complete.</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon" aria-hidden="true">✎</div>
          <h3>Fix Prompts</h3>
          <p>Each finding ships with an actionable fix prompt you can paste into Claude or Copilot to implement changes faster.</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon" aria-hidden="true">⎇</div>
          <h3>GitHub Native</h3>
          <p>Batch inline review comments via the GitHub API—feedback appears exactly where developers work, in the Files changed view.</p>
        </article>
      </div>
      <div class="stack-row" aria-label="Tech stack">
        <span class="stack-badge">FastAPI</span>
        <span class="stack-badge">Celery</span>
        <span class="stack-badge">Claude AI</span>
        <span class="stack-badge">PostgreSQL</span>
        <span class="stack-badge">Redis</span>
        <span class="stack-badge">Next.js</span>
      </div>
      <section class="how-section" aria-labelledby="how-heading">
        <h2 id="how-heading">How it works</h2>
        <div class="how-steps">
          <div class="how-step">
            <div class="how-step-num">Step 1</div>
            <h4>PR opened</h4>
            <p>GitHub sends a signed webhook; FastAPI verifies HMAC, checks idempotency, and acknowledges in milliseconds.</p>
          </div>
          <span class="how-connector" aria-hidden="true">→</span>
          <div class="how-step">
            <div class="how-step-num">Step 2</div>
            <h4>AI reviews</h4>
            <p>Workers fetch the diff; four Claude agents analyze in parallel, then the aggregator dedupes and ranks by severity.</p>
          </div>
          <span class="how-connector" aria-hidden="true">→</span>
          <div class="how-step">
            <div class="how-step-num">Step 3</div>
            <h4>Comments posted</h4>
            <p>Inline review comments land on the PR; PostgreSQL stores history and Redis notifies the dashboard in real time.</p>
          </div>
        </div>
      </section>
    </div>
"""

    terms_controls = """
    <div class="glossary-controls">
      <div class="glossary-search-wrap">
        <label for="glossarySearch" class="visually-hidden">Search glossary</label>
        <input type="search" id="glossarySearch" placeholder="Search terms, definitions, code…" autocomplete="off" />
      </div>
      <div class="glossary-filters" id="glossaryFilters" role="group" aria-label="Filter by category"></div>
    </div>
"""

    site_js = r"""
(function () {
  var tabs = ["overview", "architecture", "flow", "terms", "guide"];
  function showTab(name, opts) {
    opts = opts || {};
    document.querySelectorAll(".tab-panel").forEach(function (p) {
      p.classList.toggle("is-active", p.id === "panel-" + name);
    });
    document.querySelectorAll(".site-nav button").forEach(function (b) {
      b.classList.toggle("is-active", b.getAttribute("data-tab") === name);
      b.setAttribute("aria-selected", b.getAttribute("data-tab") === name ? "true" : "false");
    });
    if (!opts.noScroll) window.scrollTo({ top: 0, behavior: "smooth" });
    if (history.replaceState) history.replaceState(null, "", "#" + name);
  }
  document.querySelectorAll(".site-nav button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showTab(btn.getAttribute("data-tab"));
    });
  });
  var hash = (location.hash || "").replace(/^#/, "");
  if (tabs.indexOf(hash) >= 0) showTab(hash, { noScroll: true });
  else showTab("overview", { noScroll: true });
  window.addEventListener("hashchange", function () {
    var h = (location.hash || "").replace(/^#/, "");
    if (tabs.indexOf(h) >= 0) showTab(h, { noScroll: true });
  });
  document.querySelectorAll('a[href="#terms"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      showTab("terms");
    });
  });

  /* Glossary */
  var gSearch = document.getElementById("glossarySearch");
  var gSections = document.querySelectorAll(".glossary-category");
  var gTerms = document.querySelectorAll(".glossary-term");
  var filterWrap = document.getElementById("glossaryFilters");
  var activeCat = "all";
  if (filterWrap) {
    var cats = [{ slug: "all", label: "All" }];
    gSections.forEach(function (sec) {
      cats.push({ slug: sec.id.replace("cat-", ""), label: sec.getAttribute("data-category") || "" });
    });
    cats.forEach(function (c) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = c.label;
      b.setAttribute("data-cat", c.slug);
      if (c.slug === "all") b.classList.add("is-on");
      b.addEventListener("click", function () {
        activeCat = c.slug;
        filterWrap.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("is-on", x.getAttribute("data-cat") === activeCat);
        });
        applyGlossaryFilter();
      });
      filterWrap.appendChild(b);
    });
  }
  function applyGlossaryFilter() {
    var q = (gSearch && gSearch.value || "").toLowerCase().trim();
    gTerms.forEach(function (t) {
      var text = t.textContent.toLowerCase();
      var cat = t.getAttribute("data-cat") || "";
      var catOk = activeCat === "all" || cat === activeCat;
      var qOk = !q || text.indexOf(q) !== -1;
      t.classList.toggle("is-hidden", !(catOk && qOk));
    });
    gSections.forEach(function (sec) {
      var visible = sec.querySelectorAll(".glossary-term:not(.is-hidden)").length;
      sec.style.display = visible === 0 ? "none" : "";
    });
  }
  if (gSearch) {
    gSearch.addEventListener("input", applyGlossaryFilter);
  }
})();
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="AI Code Review Bot — architecture, request flow, glossary, and usage guide." />
  <title>AI Code Review Bot — Architecture &amp; Docs</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
  <style>
{merged_root}
{site_css}
{arch_css}
{flow_css}
    .visually-hidden {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0,0,0,0);
      border: 0;
    }}
  </style>
</head>
<body>
  <div class="site-noise" aria-hidden="true"></div>
  <div class="site-shell">
    <nav class="site-nav" role="navigation" aria-label="Primary">
      <button type="button" data-tab="overview" aria-selected="true">Overview</button>
      <button type="button" data-tab="architecture" aria-selected="false">Architecture</button>
      <button type="button" data-tab="flow" aria-selected="false">Flow</button>
      <button type="button" data-tab="terms" aria-selected="false">Terms</button>
      <button type="button" data-tab="guide" aria-selected="false">Guide</button>
    </nav>
    <main class="site-main">
      <section id="panel-overview" class="tab-panel is-active" aria-label="Overview">
{overview_html}
      </section>
      <section id="panel-architecture" class="tab-panel" aria-label="Architecture diagram">
{arch_body}
      </section>
      <section id="panel-flow" class="tab-panel" aria-label="Request flow">
{flow_body}
      </section>
      <section id="panel-terms" class="tab-panel" aria-label="Glossary">
        <div class="terms-inner">
          <header class="glossary-head">
            <h1>Glossary</h1>
            <p>Technical terms used across the AI Code Review Bot — searchable and grouped by category.</p>
          </header>
{terms_controls}
          <div id="glossaryMount">
{glossary}
          </div>
        </div>
      </section>
      <section id="panel-guide" class="tab-panel" aria-label="Usage guide">
        <article class="guide-inner doc-content">
{guide}
        </article>
      </section>
    </main>
  </div>
  <script>
{arch_script}
  </script>
  <script>
{flow_script}
  </script>
  <script>
{site_js}
  </script>
</body>
</html>
"""
    (BASE / "index.html").write_text(html)
    print("Wrote", BASE / "index.html", "bytes", len(html))


if __name__ == "__main__":
    main()
