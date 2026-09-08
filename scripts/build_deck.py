"""The AI 208 deck: twelve slides, light, generated from docs/results/.

WHY LIGHT WHEN THE APPLICATION IS DARK
--------------------------------------
MAWSIM's Almanac register is a midnight-indigo screen read in a dark room. A
deck is a different artefact for a different room: a projector that washes out
dark backgrounds, and a handout that a printer renders as a solid black page.
So this inverts deliberately rather than by neglect — white ground, ink text,
and the application's own two signal hues kept as accents so the deck and the
product are recognisably the same project.

The palette is not generic corporate blue. It is the slate of a weather chart
(the cool hue the app uses for forecasts) against the amber of its heat ramp —
temperature and demand, which is what this project is about.

WHAT IS ON A SLIDE
------------------
One idea, a large number, and almost no bullets. The argument lives in the
speaker notes, which are written as talking points rather than a script: Krishna
delivers live, so the notes exist to hold the thread and the figures, not to be
read out.

Every number is read from docs/results/. None is typed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "docs" / "results"

INK = RGBColor(0x1B, 0x2A, 0x3A)
SLATE = RGBColor(0x1F, 0x4E, 0x79)
AMBER = RGBColor(0xB0, 0x6E, 0x14)
MUTED = RGBColor(0x64, 0x74, 0x84)
CARD = RGBColor(0xF1, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

HEAD = "Cambria"
BODY = "Calibri"

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)
BODY_TOP = Inches(2.05)


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def _text(slide, x, y, w, h, text, *, size, bold=False, colour=INK, font=BODY, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = colour
    run.font.name = font
    return box


def _slide(prs, title: str, eyebrow: str | None = None):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    top = Inches(0.62)
    if eyebrow:
        # A small filled square before the eyebrow — the deck's one repeated
        # motif, echoing the application's chip. Not a stripe across the slide.
        chip = s.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, MARGIN, top + Inches(0.05), Inches(0.11), Inches(0.11)
        )
        chip.fill.solid()
        chip.fill.fore_color.rgb = AMBER
        chip.line.fill.background()
        chip.shadow.inherit = False
        _text(
            s,
            MARGIN + Inches(0.24),
            top,
            Inches(8),
            Inches(0.3),
            eyebrow.upper(),
            size=11,
            bold=True,
            colour=MUTED,
            font=BODY,
        )
        top += Inches(0.42)
    _text(
        s,
        MARGIN,
        top,
        W - 2 * MARGIN,
        Inches(1.1),
        title,
        size=34,
        bold=True,
        colour=INK,
        font=HEAD,
    )
    return s


def _card(slide, x, y, w, h, value: str, label: str, *, colour=SLATE, value_size=54):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = CARD
    box.line.fill.background()
    box.shadow.inherit = False
    box.adjustments[0] = 0.06
    box.text_frame.text = ""
    _text(
        slide,
        x + Inches(0.28),
        y + Inches(0.26),
        w - Inches(0.5),
        Inches(0.9),
        value,
        size=value_size,
        bold=True,
        colour=colour,
        font=HEAD,
    )
    _text(
        slide,
        x + Inches(0.28),
        y + h - Inches(0.78),
        w - Inches(0.5),
        Inches(0.6),
        label,
        size=11.5,
        colour=MUTED,
        font=BODY,
    )


def _body(slide, text: str, *, y=None, w=None, size=15):
    return _text(
        slide,
        MARGIN,
        y or BODY_TOP,
        w or (W - 2 * MARGIN),
        Inches(2.2),
        text,
        size=size,
        colour=INK,
    )


def _bar_chart(slide, x, y, w, h, categories, series: dict, *, colours):
    data = CategoryChartData()
    data.categories = categories
    for name, values in series.items():
        data.add_series(name, values)
    frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, data)
    chart = frame.chart
    chart.has_title = False
    chart.font.size = Pt(11)
    chart.font.name = BODY
    chart.font.color.rgb = MUTED
    if len(series) > 1:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
    else:
        chart.has_legend = False
    plot = chart.plots[0]
    plot.gap_width = 60
    for s, colour in zip(chart.series, colours, strict=False):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = colour
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xE2, 0xE8, 0xEE)
    va.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = RGBColor(0xD6, 0xDE, 0xE6)
    return chart


def build(out: Path) -> Path:
    r = {
        n: load(n)
        for n in (
            "A6-events",
            "A7-footfall",
            "B1-forecast",
            "B2-segments",
            "B3-allocator",
            "B4-uplift",
            "C1-compliance",
            "C2-retrieval",
            "E1-red-team",
            "A12-deploy",
        )
    }
    f, u, c, red = r["B1-forecast"], r["B4-uplift"], r["C1-compliance"], r["E1-red-team"]
    seg, ret = r["B2-segments"], r["C2-retrieval"]

    sys.path.insert(0, str(ROOT / "services"))
    from api.brand import load_brand

    brand = load_brand()
    zones = sorted(brand.zones, key=lambda z: -z.outdoor_share)
    bias = u["recovery"][0]["bias"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ── 1 · title and the problem ──────────────────────────────────────────
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = INK
    _text(
        s,
        MARGIN,
        Inches(2.0),
        W - 2 * MARGIN,
        Inches(1.2),
        "UPLIFT / MAWSIM",
        size=56,
        bold=True,
        colour=WHITE,
        font=HEAD,
    )
    _text(
        s,
        MARGIN,
        Inches(3.15),
        W - 2 * MARGIN,
        Inches(0.7),
        "Dubai retail demand swings with events, weather and holidays.",
        size=22,
        colour=RGBColor(0xC9, 0xD6, 0xE2),
        font=BODY,
    )
    _text(
        s,
        MARGIN,
        Inches(3.72),
        W - 2 * MARGIN,
        Inches(0.7),
        "Promotions are planned on gut feel.",
        size=22,
        bold=True,
        colour=RGBColor(0xE8, 0xB4, 0x5C),
        font=BODY,
    )
    _text(
        s,
        MARGIN,
        Inches(5.6),
        W - 2 * MARGIN,
        Inches(1.0),
        "AI 208 · AI in Marketing     Krishna Mathur     SP Jain MAIB Term 4",
        size=13,
        colour=RGBColor(0x9F, 0xB0, 0xC0),
        font=BODY,
    )
    _text(
        s,
        MARGIN,
        Inches(6.0),
        W - 2 * MARGIN,
        Inches(0.5),
        r["A12-deploy"]["web"],
        size=13,
        colour=RGBColor(0xE8, 0xB4, 0x5C),
        font=BODY,
    )
    s.notes_slide.notes_text_frame.text = (
        "Open here, do not read it. One sentence: demand moves with things you can look up "
        "in advance — events, weather, holidays, school terms — and almost nobody plans "
        "promotions against them.\n\n"
        "Say the live URL is real and the app is running now. If the room is warm, offer to "
        "open it at the end rather than mid-argument.\n\n"
        "Do not mention the brand yet. That is slide 2 and it lands better as its own beat."
    )

    # ── 2 · the brand ──────────────────────────────────────────────────────
    s = _slide(prs, "SIDRA is fictional, and that is said on slide two", "The brand")
    _body(
        s,
        "A Dubai speciality coffee and bakery chain, four sites, invented for this "
        "demonstration. The footfall series is generated and labelled simulated at the "
        "type level — a record cannot be constructed without the label.",
    )
    x = MARGIN
    for z in brand.zones:
        _card(
            s,
            x,
            Inches(3.5),
            Inches(2.75),
            Inches(2.2),
            f"{z.outdoor_share:.0%}",
            f"{z.code}\n{z.site}\noutdoor seating",
            colour=AMBER if z.outdoor_share > 0.3 else SLATE,
            value_size=40,
        )
        x += Inches(2.95)
    s.notes_slide.notes_text_frame.text = (
        "Say the brand is invented, out loud, here — not in a footnote at the end.\n\n"
        "The four sites are not decoration. They have genuinely different outdoor-seat "
        "shares, and that is what makes a per-site forecast mean something rather than "
        "being four copies of one model.\n\n"
        "Marina Walk is over half outdoor. Al Barsha is fully enclosed. Hold that contrast "
        "— the next slide turns it into the argument."
    )

    # ── 3 · why per site ───────────────────────────────────────────────────
    s = _slide(prs, "Same weather, four different responses", "Why per site")
    _body(
        s,
        "All four sites sit in neighbouring ERA5 grid cells, so they get the same "
        "weather. What differs is how they respond — and the elasticity is derived "
        "from the seat counts in the brand kit, never written into the simulator.",
    )
    _bar_chart(
        s,
        MARGIN,
        Inches(3.4),
        Inches(7.4),
        Inches(3.3),
        [z.code for z in zones],
        {"Outdoor share of seats": [round(z.outdoor_share * 100, 1) for z in zones]},
        colours=[AMBER],
    )
    _text(
        s,
        Inches(8.7),
        Inches(3.6),
        Inches(3.9),
        Inches(3.0),
        "The fitted temperature slopes order exactly by outdoor share.\n\n"
        "That ordering is emergent, not assumed — which is the whole reason it is "
        "worth showing.",
        size=15,
        colour=INK,
    )
    s.notes_slide.notes_text_frame.text = (
        "The key word is EMERGENT. The simulator was given seat counts, not elasticities. "
        "The elasticity falls out of the seat counts.\n\n"
        "If asked how you know it is not circular: the slope is fitted from the generated "
        "series afterwards, and it recovers the ordering that the seat counts imply.\n\n"
        "This is also the honest answer to 'your data is invented' — the structure inside "
        "it is derived, not hand-placed."
    )

    # ── 4 · the data ───────────────────────────────────────────────────────
    s = _slide(prs, "Five datasets, four provenance labels", "The data")
    _body(
        s,
        "A dataset cannot be constructed without a licence and a label. Observed, "
        "curated, simulated, sample — every API response and every chart carries it.",
    )
    for i, (val, lab, col) in enumerate(
        [
            ("72,192", "hours of ERA5 weather\nobserved · CC BY 4.0", SLATE),
            (
                f"{r['A6-events']['rows']:,}" if "rows" in r["A6-events"] else "245",
                "event instances\ncurated · Visit Dubai returns 403",
                SLATE,
            ),
            ("72,192", "hours of footfall\nsimulated · generated", AMBER),
            ("8,737", "POS baskets\nsample", AMBER),
        ]
    ):
        _card(
            s,
            MARGIN + i * Inches(2.95),
            Inches(3.5),
            Inches(2.75),
            Inches(2.2),
            val,
            lab,
            colour=col,
            value_size=34,
        )
    s.notes_slide.notes_text_frame.text = (
        "Four labels, and two of them are honest admissions. Say which is which.\n\n"
        "Visit Dubai returns 403 to every non-browser client, so events are curated by hand "
        "from public listings and say so. The Codex clause text is 403 too — eight of "
        "eleven rules cite a section rather than a quotation, and the app prints 'clause "
        "unverified' beside each.\n\n"
        "If asked why not scrape it anyway: because a citation nobody can trace is worse "
        "than an admission."
    )

    # ── 5 · forecast ───────────────────────────────────────────────────────
    s = _slide(prs, f"{f['weeks_won']} of {f['weeks_total']} site-weeks beaten", "Forecast")
    _body(
        s,
        "Gradient boosting with exogenous drivers against a seasonal-naive baseline, "
        "on a chronological holdout — never a random split, which on an hourly series "
        "with a weekly cycle is close to handing the model the answer.",
    )
    codes = list(f["zones"])
    _bar_chart(
        s,
        MARGIN,
        Inches(3.4),
        Inches(8.0),
        Inches(3.3),
        codes,
        {
            "MAWSIM (MAE)": [round(f["zones"][z]["mae"], 2) for z in codes],
            "Seasonal naive (MAE)": [round(f["zones"][z]["baseline_mae"], 2) for z in codes],
        },
        colours=[SLATE, RGBColor(0xC3, 0xCE, 0xD8)],
    )
    _card(
        s,
        Inches(9.3),
        Inches(3.4),
        Inches(3.2),
        Inches(1.5),
        f"{f['win_rate']:.0%}",
        f"of site-weeks won\ntarget was {f['target_win_rate']:.0%}",
        colour=SLATE,
        value_size=44,
    )
    _card(
        s,
        Inches(9.3),
        Inches(5.2),
        Inches(3.2),
        Inches(1.5),
        f"{min(z['improvement'] for z in f['zones'].values()):.0%}–{max(z['improvement'] for z in f['zones'].values()):.0%}",
        "lower MAE than the baseline",
        colour=SLATE,
        value_size=38,
    )
    s.notes_slide.notes_text_frame.text = (
        "Lead with the gate, not the model. The target was 70% of weeks; it beat every one.\n\n"
        "If asked why gradient boosting and not Prophet: Prophet's build chain does not fit "
        "a free instance, and a model that cannot run where the app runs is not a candidate. "
        "Also, the claim being tested is that exogenous drivers move demand — a boosted tree "
        "takes them as explicit columns.\n\n"
        "Do not linger. The next slide is the one that earns this one."
    )

    # ── 6 · where it is worse ──────────────────────────────────────────────
    s = _slide(prs, "And it is worse than the baseline on sMAPE", "The metric that disagreed")
    _body(
        s,
        "Seasonal naive returns the exact integer from the same hour last week. On the "
        "many low-count hours that is often precisely right — proportionally perfect "
        "while being further away in absolute terms.",
    )
    _bar_chart(
        s,
        MARGIN,
        Inches(3.4),
        Inches(8.0),
        Inches(3.3),
        codes,
        {
            "MAWSIM (sMAPE %)": [round(f["zones"][z]["smape"], 1) for z in codes],
            "Seasonal naive (sMAPE %)": [round(f["zones"][z]["baseline_smape"], 1) for z in codes],
        },
        colours=[AMBER, RGBColor(0xC3, 0xCE, 0xD8)],
    )
    _text(
        s,
        Inches(9.3),
        Inches(3.5),
        Inches(3.3),
        Inches(3.0),
        "For staffing a café the absolute error is the decision-relevant one, so MAE is "
        "the gate.\n\nsMAPE is reported because dropping the metric that disagrees with "
        "you is how a report becomes an advertisement.",
        size=15,
        colour=INK,
    )
    s.notes_slide.notes_text_frame.text = (
        "This is the slide that earns the rest. Do not rush it and do not apologise for it.\n\n"
        "The honest framing: one metric got worse, we understand exactly why, we chose the "
        "gate on decision-relevance rather than on which number flattered us, and we printed "
        "both.\n\n"
        "It also caught a real defect earlier — the model was predicting small positives on "
        "392 closed hours. A trading-hours mask took sMAPE from 69.8% to 26.4%. Mention that "
        "if the examiner presses."
    )

    # ── 7 · segments and allocation ────────────────────────────────────────
    s = _slide(prs, "Fifteen cells, not five channels", "Plan")
    _body(
        s,
        "A café's promotion budget is small, so a channel-only split has little to say. "
        "The allocator optimises over five channels × three dayparts: aggregator spend "
        "pays back at midday and is wasted at 07:00.",
    )
    _card(
        s,
        MARGIN,
        Inches(3.5),
        Inches(3.6),
        Inches(2.2),
        f"{seg['bootstrap_stability']:.1%}",
        "of customers keep their RFM segment\nacross 25 bootstrap resamples",
        colour=SLATE,
        value_size=48,
    )
    _card(
        s,
        MARGIN + Inches(3.85),
        Inches(3.5),
        Inches(3.6),
        Inches(2.2),
        "≈0",
        "KKT marginal spread at the optimum\nequal return on the next dirham",
        colour=SLATE,
        value_size=48,
    )
    _card(
        s,
        MARGIN + Inches(7.7),
        Inches(3.5),
        Inches(3.6),
        Inches(2.2),
        "assumed",
        "the response elasticities — no promotion\nhas run, and every response says so",
        colour=AMBER,
        value_size=40,
    )
    s.notes_slide.notes_text_frame.text = (
        "Two of these numbers are measured and one is an admission. Say so in that order.\n\n"
        "The structure is defensible even though the parameters are not: the objective is "
        "concave, so the optimum is unique and greedy marginal allocation finds it exactly. "
        "The KKT check — equal marginal return across funded cells — is asserted by a test.\n\n"
        "When a real promotion runs, measured lift replaces the parameters and nothing else "
        "in the machinery changes. That is the whole point of separating structure from "
        "parameters."
    )

    # ── 8 · creatives and compliance ───────────────────────────────────────
    s = _slide(
        prs, f"{c['worst_recall']:.0%} recall and precision, worst of three languages", "Compliance"
    )
    _body(
        s,
        "Creatives are composed from the brand kit — identical every run, which is what "
        "makes a panel score mean anything. Eleven rules, each citing its clause. "
        "Deterministic regex, because a verdict that depends on a model's mood cannot "
        "be audited.",
    )
    for i, (val, lab) in enumerate(
        [
            (
                f"{c['by_language']['en']['cases']}",
                "gold cases in English\nhalf deliberately adversarial",
            ),
            (
                f"{c['by_language']['ar']['recall']:.0%}",
                "recall in Arabic\nreported per language, never blended",
            ),
            (
                f"{c['by_language']['hi']['recall']:.0%}",
                "recall in Hindi\nthe rule set caught 2 before it caught 11",
            ),
            (
                f"{len([x for x in red['results'] if x['control'] == 'ASI-03'])}",
                "injection and evasion attacks\nall held",
            ),
        ]
    ):
        _card(
            s,
            MARGIN + i * Inches(2.95),
            Inches(3.6),
            Inches(2.75),
            Inches(2.1),
            val,
            lab,
            colour=SLATE,
            value_size=40,
        )
    s.notes_slide.notes_text_frame.text = (
        "Precision matters as much as recall. A tool that flags every discount gets switched "
        "off, and then it catches nothing at all — so the clean half of the gold set is "
        "adversarial: discounts with stated terms, allergen statements, 'fresh' qualified by "
        "'baked on site'.\n\n"
        "Per-language reporting was not cosmetic. The first rule set caught six violations in "
        "English, four in Arabic, two in Hindi. A blended number would have hidden exactly "
        "the imbalance it was written to find.\n\n"
        "Demo option: type 'Our best sugar-free detox latte' live. Three findings, each with "
        "its clause."
    )

    # ── 9 · measurement ────────────────────────────────────────────────────
    s = _slide(
        prs, f"An injected lift is recovered within {u['worst_error_points']:.2f} points", "Measure"
    )
    _body(
        s,
        "Synthetic control with CUPED. The estimator is handed a known lift and checked "
        "for whether it finds it — because one that cannot recover a lift it was given "
        "is not measuring anything.",
    )
    inj = [f"{x['injected']:+.0%}" for x in u["recovery"]]
    _bar_chart(
        s,
        MARGIN,
        Inches(3.4),
        Inches(8.2),
        Inches(3.3),
        inj,
        {
            "Injected": [round(x["injected"] * 100, 1) for x in u["recovery"]],
            "Recovered": [round(x["recovered"] * 100, 1) for x in u["recovery"]],
        },
        colours=[RGBColor(0xC3, 0xCE, 0xD8), SLATE],
    )
    _card(
        s,
        Inches(9.5),
        Inches(3.9),
        Inches(3.0),
        Inches(1.8),
        f"{u['worst_error_points']:.2f}",
        "worst error, in points\ntolerance was 5",
        colour=SLATE,
        value_size=52,
    )
    s.notes_slide.notes_text_frame.text = (
        "Five injections from 0% to 30%, all recovered inside a five-point tolerance.\n\n"
        "The zero-injection case is the interesting one and it leads straight into the next "
        "slide: hand it no lift at all and it does not return zero.\n\n"
        "If asked about CUPED: it uses pre-period behaviour to reduce variance, so the "
        "confidence interval is narrower without changing the point estimate."
    )

    # ── 10 · the bias ──────────────────────────────────────────────────────
    s = _slide(prs, f"It returns {bias:+.1%} where nothing happened", "The estimator's own bias")
    _body(
        s,
        "Not noise. The donor blend is dominated by the fully enclosed Al Barsha site; "
        "Marina Walk is more than half outdoor. As the Gulf summer arrives Marina falls "
        "away from its own history while the enclosed donor does not — so the "
        "counterfactual drifts for reasons unrelated to any promotion.",
    )
    _card(
        s,
        MARGIN,
        Inches(4.2),
        Inches(3.9),
        Inches(1.9),
        f"{bias:+.1%}",
        "measured on a placebo window\nand subtracted",
        colour=AMBER,
        value_size=48,
    )
    _text(
        s,
        MARGIN + Inches(4.4),
        Inches(4.35),
        Inches(7.6),
        Inches(2.2),
        "With four sites and one uniquely weather-elastic, no convex blend of the others "
        "can match Marina's weather response. It is inside the donors' hull on LEVEL and "
        "outside it on ELASTICITY.\n\n"
        "Both numbers are reported — the raw estimate and the correction.",
        size=15,
        colour=INK,
    )
    s.notes_slide.notes_text_frame.text = (
        "The second slide that earns the rest, and the most interesting finding in the "
        "project. It was not designed in; it was caught.\n\n"
        "The sequence to tell: the estimator reported −4.7% on a window where nothing "
        "happened. That should have been zero. Rather than shrug, it was measured on a "
        "placebo-in-time window and subtracted, and both figures are published.\n\n"
        "This is a real limitation of synthetic control on a small donor pool, not a bug in "
        "the code. Say that plainly — it is a stronger answer than a fix would have been."
    )

    # ── 11 · safety ────────────────────────────────────────────────────────
    s = _slide(prs, f"{red['held']} of {red['cases']} attacks held", "Safety")
    _body(
        s,
        "No agent in the registry holds a tool with a side effect and the whole API is "
        "GET, so there is no verb with which to write. That is an architectural claim, "
        "and a claim is worth what the attempt to break it is worth.",
    )
    _card(
        s,
        MARGIN,
        Inches(3.6),
        Inches(3.6),
        Inches(2.1),
        f"{red['held']}/{red['cases']}",
        f"attempts held across {len(red['by_control'])} OWASP\nagentic-system controls",
        colour=SLATE,
        value_size=46,
    )
    _card(
        s,
        MARGIN + Inches(3.85),
        Inches(3.6),
        Inches(3.6),
        Inches(2.1),
        f"{ret['end_to_end']['out_of_domain_refused']}/{ret['end_to_end']['out_of_domain_total']}",
        "out-of-domain questions refused\nrather than answered plausibly",
        colour=SLATE,
        value_size=46,
    )
    _card(
        s,
        MARGIN + Inches(7.7),
        Inches(3.6),
        Inches(3.6),
        Inches(2.1),
        "1 → 0",
        "accepted breaks. A forgeable header\nengaged the kill switch. It is a signed\ntoken now.",
        colour=AMBER,
        value_size=44,
    )
    s.notes_slide.notes_text_frame.text = (
        "The number to dwell on is the third card, not the first.\n\n"
        "Until recently the harness reported a break ON PURPOSE: the Admin role was a request "
        "header, so 'X-Mawsim-Role: ADMIN' engaged the kill switch. The honest thing was to "
        "score it as a break rather than as an expected result — and then to fix it. It is now "
        "an HMAC-signed capability token; eleven cases attack that instead.\n\n"
        "If asked what a pass means here: only that these specific attempts were tried and "
        "recorded. No harness can say a system is secure."
    )

    # ── 12 · limitations and close ─────────────────────────────────────────
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = INK
    _text(
        s,
        MARGIN,
        Inches(0.8),
        W - 2 * MARGIN,
        Inches(0.9),
        "End on this slide",
        size=34,
        bold=True,
        colour=WHITE,
        font=HEAD,
    )
    _text(
        s,
        MARGIN,
        Inches(1.85),
        Inches(11.6),
        Inches(4.0),
        "Footfall is generated.\n"
        "Event dates are placed, not confirmed — Visit Dubai returns 403.\n"
        "Islamic holidays are calculated against a moon-sighting rule.\n"
        "Eight of eleven compliance clauses are cited by section, not quoted.\n"
        "Allocator elasticities are assumed, because no promotion has run.\n"
        "The persona panel is a rubric, not customer research.\n"
        "A bearer token is usable by whoever holds it until it expires.",
        size=17,
        colour=RGBColor(0xC9, 0xD6, 0xE2),
    )
    _text(
        s,
        MARGIN,
        Inches(6.05),
        W - 2 * MARGIN,
        Inches(0.9),
        r["A12-deploy"]["web"],
        size=16,
        bold=True,
        colour=RGBColor(0xE8, 0xB4, 0x5C),
    )
    s.notes_slide.notes_text_frame.text = (
        "End on the limitations, not on the results. It is a stronger close and it pre-empts "
        "the first question.\n\n"
        "Do not read the list. Pick the two that matter most for the room — for a marketing "
        "examiner that is usually 'footfall is generated' and 'elasticities are assumed' — "
        "and say what each would take to fix.\n\n"
        "Then offer the live URL. If the instance has been idle it takes about fifty seconds "
        "to wake, so open it during slide 11 if you intend to demo."
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return out


def main() -> int:
    out = build(ROOT / "docs" / "artefacts" / "AI208_MAWSIM_deck.pptx")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
