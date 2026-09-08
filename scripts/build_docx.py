"""Render the report markdown into a submission-grade Word document.

WHY A RENDERER AND NOT A SECOND AUTHORING PATH
----------------------------------------------
The obvious way to make a handsome .docx is to write the document again in
python-docx. That gives you two documents to keep in step, and the one nobody
regenerates goes stale — which is precisely the failure this project spends its
tests preventing. So `build_report.py` remains the single source of content, and
this module is a RENDERER: it parses that markdown and lays it out. Anything
that appears here and not there is styling.

The light theme is deliberate and is a switch away from the application's dark
Almanac register. The app is read on a screen in a dark room; this is read on
paper, or in Word's white page, by someone who will print it.

python-docx rather than docx-js, for one archival reason: python-docx is in
`uv.lock`, so this document regenerates from a downloaded zip with no network
and no npm. A generator that needs a package listed in no manifest is a
generator that stops working the moment it matters.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# A cool slate, taken from the application's own signal hue (218) rather than
# invented, so the document and the product are recognisably the same project.
INK = RGBColor(0x1B, 0x2A, 0x3A)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x5A, 0x6B, 0x7B)
RULE = "D6DEE6"
HEAD_FILL = "EEF3F7"

BODY_FONT = "Georgia"
HEAD_FONT = "Arial"


def _field(paragraph, instruction: str, placeholder: str = "") -> None:
    """Insert a Word field, which is computed by Word rather than by us.

    Used for the table of contents and for page numbers. A hand-typed contents
    page is wrong the first time a section moves, and a hand-typed page number
    is wrong immediately.
    """
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, sep):
        run._r.append(node)
    if placeholder:
        run._r.append(OxmlElement("w:t"))
        run._r[-1].text = placeholder
    run._r.append(end)


def _shade(cell, hex_fill: str) -> None:
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")  # never "solid" — it renders black
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hex_fill)
    cell._tc.get_or_add_tcPr().append(el)


def _borders(table) -> None:
    """Horizontal rules only. A full grid makes a small table look like a form."""
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:color"), RULE)
        borders.append(el)
    for edge in ("left", "right", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def _style(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.18

    for name, size, colour, before in (
        ("Heading 1", 17, ACCENT, 20),
        ("Heading 2", 13, ACCENT, 15),
        ("Heading 3", 11, INK, 12),
    ):
        st = doc.styles[name]
        st.font.name = HEAD_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = colour
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(5)
        st.paragraph_format.keep_with_next = True


def _inline(paragraph, text: str) -> None:
    """Bold **spans** and monospace `spans`. Everything else is plain."""
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = MUTED
        else:
            paragraph.add_run(part)


def _cover(doc: Document, meta: dict) -> None:
    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(meta["title"])
    r.font.name = HEAD_FONT
    r.font.size = Pt(34)
    r.font.bold = True
    r.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(meta["tagline"])
    r.font.size = Pt(12.5)
    r.font.italic = True
    r.font.color.rgb = MUTED

    doc.add_paragraph()
    for line, size, bold in (
        (meta["subject"], 12, True),
        (meta["author"], 11.5, False),
        (meta["school"], 11.5, False),
        (meta["date"], 10.5, False),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = INK if bold else MUTED

    for _ in range(6):
        doc.add_paragraph()

    # The disclaimer belongs on the cover, not in a footnote. A reader who sees
    # only the first page must still know the brand is invented.
    box = doc.add_table(rows=1, cols=1)
    box.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = box.rows[0].cells[0]
    cell.width = Cm(15)
    _shade(cell, HEAD_FILL)
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cell.paragraphs[0].add_run(meta["disclaimer"])
    r.font.size = Pt(9.5)
    r.font.color.rgb = MUTED
    _borders(box)

    doc.add_page_break()


def _contents(doc: Document) -> None:
    h = doc.add_paragraph()
    r = h.add_run("Contents")
    r.font.name = HEAD_FONT
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = ACCENT
    doc.add_paragraph()
    p = doc.add_paragraph()
    _field(
        p,
        r'TOC \o "1-2" \h \z \u',
        "Right-click and choose Update Field to build the contents.",
    )
    doc.add_page_break()


def _chrome(doc: Document, meta: dict) -> None:
    """Running header and page numbers, absent from the cover."""
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)

    header = section.header
    header.is_linked_to_previous = False
    p = header.paragraphs[0]
    p.paragraph_format.tab_stops.add_tab_stop(
        section.page_width - section.left_margin - section.right_margin,
        WD_TAB_ALIGNMENT.RIGHT,
    )
    run = p.add_run(f"{meta['title']}\t{meta['subject']}")
    run.font.name = HEAD_FONT
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "6")
    bottom.set(qn("w:color"), RULE)
    pbdr.append(bottom)
    p._p.get_or_add_pPr().append(pbdr)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _field(fp, "PAGE", "1")
    for run in fp.runs:
        run.font.name = HEAD_FONT
        run.font.size = Pt(9)
        run.font.color.rgb = MUTED


def _table(doc: Document, rows: list[list[str]], aligns: list[str]) -> None:
    head, *body = rows
    table = doc.add_table(rows=1, cols=len(head))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Word's autofit silently overrides cell widths, so a long first column
    # bleeds into the second and the table stops looking like a table. The fix
    # is to turn autofit off and state the width in THREE places — the grid, the
    # column, and every cell — because a width given in only one of them is a
    # width Word feels free to ignore.
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)

    usable = Cm(16.0)
    # A leading label column earns more room than the columns of figures beside
    # it; equal thirds put "Compliance catches violations in three languages" on
    # four lines next to a number on one.
    if len(head) == 2:
        widths = [int(usable * 0.42), int(usable * 0.58)]
    elif len(head) >= 3:
        first = int(usable * 0.40)
        widths = [first] + [int((usable - first) / (len(head) - 1))] * (len(head) - 1)
    else:
        widths = [int(usable)]

    for i, col in enumerate(table.columns):
        col.width = widths[i]

    for i, text in enumerate(head):
        cell = table.rows[0].cells[i]
        cell.width = widths[i]
        _shade(cell, HEAD_FILL)
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(2)
        run = para.add_run(text)
        run.font.name = HEAD_FONT
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.color.rgb = ACCENT

    for line in body:
        cells = table.add_row().cells
        for i, text in enumerate(line[: len(head)]):
            cell = cells[i]
            cell.width = widths[i]
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(2)
            if aligns[i] == "right":
                para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            _inline(para, text)
            for run in para.runs:
                run.font.size = Pt(9)
    _borders(table)
    doc.add_paragraph()


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render(markdown: str, out_path: Path, meta: dict) -> Path:
    doc = Document()
    _style(doc)
    _chrome(doc, meta)
    _cover(doc, meta)
    _contents(doc)

    lines = markdown.splitlines()

    # Everything before the first "## " is the markdown's own front matter:
    # title, byline, generation stamp and the fictional-brand notice. The cover
    # page carries all of it, so rendering it again put the byline and the
    # disclaimer on the page directly under Contents.
    first_section = next((n for n, ln in enumerate(lines) if ln.startswith("## ")), 0)
    lines = lines[first_section:]

    i = 0
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if buffer:
            _inline(doc.add_paragraph(), " ".join(buffer))
            buffer = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and set(lines[i + 1].strip()) <= set("|-: ")
        ):
            flush()
            header = _split_row(line)
            aligns = [
                "right" if c.strip().endswith(":") else "left" for c in _split_row(lines[i + 1])
            ]
            i += 2
            rows = [header]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            _table(doc, rows, aligns)
            continue

        if set(stripped) == {"-"} and len(stripped) >= 3:
            # A markdown rule. Drawn as a paragraph border, never as three
            # hyphens and never as a one-row table — a table used as a line
            # picks up table styling in Word and stops being a line.
            flush()
            rule = doc.add_paragraph()
            rule.paragraph_format.space_before = Pt(2)
            rule.paragraph_format.space_after = Pt(8)
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), RULE)
            pbdr.append(bottom)
            rule._p.get_or_add_pPr().append(pbdr)
            i += 1
            continue

        if stripped.startswith("#"):
            flush()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if level == 1:
                # The markdown's H1 is the document title, already on the cover.
                i += 1
                continue
            doc.add_heading(text, level=min(level - 1, 3))
        elif stripped.startswith(("- ", "* ")):
            flush()
            para = doc.add_paragraph(style="List Bullet")
            para.paragraph_format.space_after = Pt(3)
            _inline(para, stripped[2:])
        elif stripped.startswith(">"):
            flush()
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.8)
            _inline(para, stripped.lstrip("> "))
            for run in para.runs:
                run.font.italic = True
                run.font.color.rgb = MUTED
        elif not stripped:
            flush()
        else:
            buffer.append(stripped)
        i += 1

    flush()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path
