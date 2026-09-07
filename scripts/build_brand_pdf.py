"""Generate the SIDRA brand guidelines from data/brand/sidra.yaml.

WHY GENERATE IT RATHER THAN WRITE IT
------------------------------------
The Compliance agent enforces `claims_to_avoid` out of the YAML, and a reviewer
reads the PDF. If those were two documents they would drift, and the drift
would be invisible — the agent would enforce one rule set while the guidelines
a reader checks it against said something else. Generating the PDF from the
same file makes that impossible by construction.

The output is BYTE-IDENTICAL across runs. reportlab stamps a creation date and
a document id by default, which would make every rebuild a diff and make "the
PDF is current" unverifiable. `rl_config.invariant` turns both off.

ARABIC IS DEliberATELY ABSENT FROM THIS PDF
-------------------------------------------
reportlab does not do Arabic shaping or bidirectional layout, so Arabic set
here renders as disconnected letterforms in the wrong order. That is worse than
omitting it. The Arabic identity lives in the YAML and is rendered properly by
the web application, which has a text engine that can do it. The PDF says so
rather than leaving a reader to wonder.
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab import rl_config

# Must be set before anything builds a canvas.
rl_config.invariant = 1  # fixed timestamps and document ids -> reproducible bytes

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from services.api.brand import Brand, load_brand  # noqa: E402

OUT = ROOT / "docs" / "brand" / "SIDRA-brand-guidelines.pdf"

MARGIN = 22 * mm


def hexc(brand: Brand, name: str) -> colors.Color:
    return colors.HexColor(brand.palette[name])


class Swatch(Flowable):
    """A palette chip that prints its own hex and its contrast against ink."""

    def __init__(self, name: str, value: str, ratio_vs_ink: float, width=52 * mm, height=16 * mm):
        super().__init__()
        self.name, self.value, self.ratio = name, value, ratio_vs_ink
        self.width, self.height = width, height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor(self.value))
        c.setStrokeColor(colors.HexColor("#00000022"))
        c.rect(0, 0, self.width, self.height, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#1C1714") if self.ratio < 4.5 else colors.white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(3 * mm, self.height - 6 * mm, self.name.upper())
        c.setFont("Helvetica", 7)
        c.drawString(3 * mm, self.height - 10 * mm, self.value)
        c.drawString(3 * mm, 3 * mm, f"{self.ratio:.1f}:1 vs ink")


def styles(brand: Brand) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    ink = hexc(brand, "ink")
    date = hexc(brand, "date")
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Times-Roman",
            fontSize=40,
            leading=42,
            textColor=ink,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=date,
            spaceAfter=8 * mm,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Times-Roman",
            fontSize=19,
            leading=23,
            textColor=ink,
            spaceBefore=9 * mm,
            spaceAfter=3 * mm,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=date,
            spaceBefore=5 * mm,
            spaceAfter=1.5 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14.5,
            textColor=ink,
            spaceAfter=2.5 * mm,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=11,
            textColor=date,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=13,
            textColor=date,
            borderPadding=3,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
        ),
    }


def build(brand: Brand, out: Path) -> Path:
    st = styles(brand)
    ink, date_c, semolina = hexc(brand, "ink"), hexc(brand, "date"), hexc(brand, "semolina")
    story: list = []

    def rule(space_before=2 * mm):
        story.append(Spacer(1, space_before))
        t = Table([[""]], colWidths=[A4[0] - 2 * MARGIN], rowHeights=[0.4])
        t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.5, date_c)]))
        story.append(t)
        story.append(Spacer(1, 2 * mm))

    # ── cover ───────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 26 * mm),
        Paragraph("SIDRA", st["title"]),
        Paragraph("Brand guidelines · edition one", st["sub"]),
        Paragraph(
            f"<b>{brand.raw['identity']['category']}</b> · founded "
            f"{brand.raw['identity']['founded']} · four sites in Dubai",
            st["body"],
        ),
        Paragraph(brand.raw["identity"]["positioning"], st["body"]),
        Spacer(1, 6 * mm),
    ]
    story.append(
        Paragraph(
            f"<b>This brand is fictional.</b> {brand.disclaimer}",
            ParagraphStyle(
                "disc",
                parent=st["body"],
                backColor=semolina,
                borderPadding=6,
                borderColor=date_c,
                borderWidth=0.6,
            ),
        )
    )
    story += [
        Spacer(1, 4 * mm),
        Paragraph(
            "Generated from <font face='Courier'>data/brand/sidra.yaml</font> by "
            "<font face='Courier'>scripts/build_brand_pdf.py</font>. The compliance rules in "
            "section five are enforced by the application from that same file, so this document "
            "and the running rule set cannot disagree. Regenerate rather than edit.",
            st["small"],
        ),
        PageBreak(),
    ]

    # ── 1. the name ─────────────────────────────────────────────────────────
    story += [
        Paragraph("One — the name", st["h1"]),
        Paragraph(brand.raw["identity"]["etymology"], st["body"]),
        Paragraph(brand.raw["identity"]["founder_story"], st["body"]),
        Paragraph(brand.raw["identity"]["proposition"], st["body"]),
        Paragraph(
            "The Arabic and Hindi forms of the name are held in the source file and are set "
            "correctly by the web application. They are omitted from this PDF: the generator has "
            "no Arabic shaping or bidirectional layout, and unshaped Arabic printed left-to-right "
            "is worse than no Arabic at all.",
            st["note"],
        ),
    ]

    # ── 2. sites ────────────────────────────────────────────────────────────
    story.append(Paragraph("Two — the four sites", st["h1"]))
    story.append(
        Paragraph(
            "The estate is deliberately heterogeneous. Al Barsha is fully enclosed and Marina "
            "Walk is more than half outdoors, so the same weather moves them in opposite "
            "directions. That is why demand is forecast per site rather than per brand.",
            st["body"],
        )
    )
    rows = [["Code", "Site", "Seats", "Outdoor", "Hours", "Character"]]
    for z in brand.zones:
        rows.append(
            [
                z.code,
                z.name,
                str(z.seats),
                str(z.outdoor_seats),
                f"{z.opens}–{z.closes}",
                z.character,
            ]
        )
    t = Table(rows, colWidths=[20 * mm, 26 * mm, 13 * mm, 16 * mm, 24 * mm, 67 * mm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("TEXTCOLOR", (0, 0), (-1, 0), date_c),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, date_c),
                ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#00000018")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t)

    # ── 3. voice ────────────────────────────────────────────────────────────
    story.append(Paragraph("Three — voice", st["h1"]))
    for principle in brand.voice["principles"]:
        story.append(Paragraph(f"— {principle}", st["body"]))
    story.append(Paragraph("Do", st["h2"]))
    for d in brand.voice["do"]:
        story.append(Paragraph(f"• {d}", st["body"]))
    story.append(Paragraph("Do not", st["h2"]))
    for d in brand.voice["dont"]:
        story.append(Paragraph(f"• {d}", st["body"]))

    story.append(PageBreak())

    # ── 4. colour and type ──────────────────────────────────────────────────
    story.append(Paragraph("Four — colour and type", st["h1"]))
    story.append(
        Paragraph(
            "Every chip below prints its measured contrast against ink. The rule that ink must "
            "never be set on date is not a matter of taste — it is 3.1:1 and fails WCAG AA.",
            st["body"],
        )
    )
    chips = [Swatch(n, v, brand.contrast("ink", n)) for n, v in brand.palette.items()]
    grid = [chips[i : i + 3] for i in range(0, len(chips), 3)]
    for row in grid:
        while len(row) < 3:
            row.append(Spacer(52 * mm, 16 * mm))
    ct = Table(grid, colWidths=[56 * mm] * 3)
    ct.setStyle(
        TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
    )
    story.append(ct)
    story.append(Paragraph("Colour rules", st["h2"]))
    for r in brand.raw["palette"]["rules"]:
        story.append(Paragraph(f"• {r}", st["body"]))
    story.append(Paragraph("Type rules", st["h2"]))
    ty = brand.raw["typography"]
    story.append(
        Paragraph(
            f"Display <b>{ty['display']}</b> · body <b>{ty['body']}</b> · "
            f"Arabic <b>{ty['arabic']}</b> · Devanagari <b>{ty['devanagari']}</b>",
            st["body"],
        )
    )
    for r in ty["rules"]:
        story.append(Paragraph(f"• {r}", st["body"]))

    story.append(PageBreak())

    # ── 5. claims ───────────────────────────────────────────────────────────
    story.append(Paragraph("Five — claims to avoid", st["h1"]))
    story.append(
        Paragraph(
            "These are enforced by the application, not merely stated here. Each rule names the "
            "document it comes from. Where a clause is marked <b>unverified</b>, the source "
            "document's identity has been checked by fetching it, but the specific clause has "
            "not yet been read verbatim — the corpus ingestion supplies the quote and flips the "
            "flag. A rule set that cited clauses nobody had read would be exactly the failure "
            "this application exists to catch.",
            st["body"],
        )
    )
    for r in brand.claims_to_avoid:
        src = brand.sources[r.source]
        pat = ", ".join(f"<font face='Courier'>{p}</font>" for p in r.patterns) or "—"
        verified = (
            f"verified · “{r.clause_quote.strip()}”" if r.clause_verified else "clause unverified"
        )
        block = [
            Paragraph(f"{r.id} · {r.family} · {r.severity}", st["h2"]),
            Paragraph(r.why.strip(), st["body"]),
            Paragraph(f"<b>Triggers</b> {pat}", st["small"]),
            Paragraph(f"<b>Source</b> {src.citation()} — {r.clause} · {verified}", st["small"]),
            Spacer(1, 3 * mm),
        ]
        story.append(KeepTogether(block))

    story.append(Paragraph("Six — offers", st["h1"]))
    for r in brand.raw["offer_rules"]:
        story.append(Paragraph(f"• {r}", st["body"]))

    # ── render ──────────────────────────────────────────────────────────────
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="SIDRA brand guidelines (fictional brand)",
        author="Generated by scripts/build_brand_pdf.py",
        subject="Fictional brand created for SP Jain MAIB AI 208 coursework",
    )
    frame = Frame(MARGIN, MARGIN, A4[0] - 2 * MARGIN, A4[1] - 2 * MARGIN, id="body")

    def decorate(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(date_c)
        canvas.drawString(
            MARGIN, 12 * mm, "SIDRA · fictional brand · generated from data/brand/sidra.yaml"
        )
        canvas.drawRightString(A4[0] - MARGIN, 12 * mm, str(canvas.getPageNumber()))
        canvas.setStrokeColor(ink)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 15 * mm, A4[0] - MARGIN, 15 * mm)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])
    doc.build(story)
    return out


def main() -> int:
    brand = load_brand()
    path = build(brand, OUT)
    size = path.stat().st_size
    print(f"wrote {path.relative_to(ROOT)} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
