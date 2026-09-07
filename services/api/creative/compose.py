"""Compose a creative from the brand kit — no image service, no model.

WHY DETERMINISTIC COMPOSITION AND NOT A GENERATED IMAGE
-------------------------------------------------------
Free image endpoints rate-limit unpredictably, produce off-brand output, and
garble Arabic text inside images — which in an application about brand
compliance is a liability rather than a shortcut. More decisively: the persona
panel scores these creatives, and a score is only meaningful if the artefact is
stable under a seed.

So a creative is an SVG built from data/brand/sidra.yaml: the brand's own
palette, its type, its products and its prices, laid out for the slot. It is a
real ad in the brand's colours at real ad dimensions, and it renders identically
every time. Phase C's language model writes the COPY; this composes it.

ARABIC IS COMPOSED, NOT TRANSLATED
----------------------------------
The AR variant carries copy written in Arabic in the brand kit, not a machine
translation of the English. SIDRA's voice rules say the specific thing, and a
translated superlative is still a superlative.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from services.api.brand import Brand, load_brand

#: The three placements a café actually buys, at their real pixel dimensions.
SIZES: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "story": (1080, 1920),
    "landscape": (1200, 628),
}

LANGS = ("en", "ar", "hi")

#: Copy per slot, per language. Written to SIDRA's voice rules — specific times,
#: specific sites, one claim per piece — and deliberately including one variant
#: that breaks them, so the Compliance tab has something real to catch.
COPY: dict[str, dict[str, dict[str, str]]] = {
    "eid-evening": {
        "en": {
            "headline": "Evenings are back on the Walk.",
            "body": "Cardamom cold brew and pistachio knafeh, from 17:00. Marina Walk only. Contains pistachio, dairy and gluten.",
            "cta": "Find your table",
        },
        "ar": {
            "headline": "المساء عاد إلى المرسى.",
            "body": "قهوة باردة بالهيل وكنافة بالفستق، من الساعة 5 مساءً. في مرسى دبي فقط. يحتوي على الفستق والحليب والغلوتين.",
            "cta": "احجز طاولتك",
        },
        "hi": {
            "headline": "शामें फिर से मरीना की हैं।",
            "body": "इलायची कोल्ड ब्रू और पिस्ता कनाफे, शाम 5 बजे से। सिर्फ़ मरीना वॉक पर। इसमें पिस्ता, डेयरी और ग्लूटेन शामिल है।",
            "cta": "अपनी मेज़ चुनें",
        },
    },
    "morning-deira": {
        "en": {
            "headline": "Open at six, like always.",
            "body": "Za'atar saj and a flat white before the market fills. Deira, from 06:00. Contains gluten and sesame.",
            "cta": "See the counter",
        },
        "ar": {
            "headline": "نفتح السادسة، كالعادة.",
            "body": "صاج بالزعتر وقهوة قبل أن يزدحم السوق. ديرة، من الساعة 6 صباحاً. يحتوي على الغلوتين والسمسم.",
            "cta": "شاهد القائمة",
        },
        "hi": {
            "headline": "हमेशा की तरह, छह बजे।",
            "body": "बाज़ार भरने से पहले ज़ातर साज और फ़्लैट व्हाइट। देरा, सुबह 6 बजे से। इसमें ग्लूटेन और तिल शामिल है।",
            "cta": "काउंटर देखें",
        },
    },
    # This one breaks the rules on purpose. A compliance tab that never catches
    # anything is decoration, and a gold set needs a positive case.
    "summer-detox": {
        "en": {
            "headline": "Dubai's finest sugar-free detox latte.",
            "body": "Clinically proven to boost immunity. 100% natural. 30% off this weekend.",
            "cta": "Order now",
        },
        "ar": {
            "headline": "أفضل لاتيه خالٍ من السكر في دبي.",
            "body": "يعالج ويعزز المناعة. طبيعي 100٪. خصم هذا الأسبوع.",
            "cta": "اطلب الآن",
        },
        "hi": {
            "headline": "दुबई का बेहतरीन शुगर-फ्री डिटॉक्स लाटे।",
            "body": "इम्युनिटी बढ़ाने के लिए clinically proven। 100% natural।",
            "cta": "अभी ऑर्डर करें",
        },
    },
}

SLOT_META: dict[str, dict[str, str]] = {
    "eid-evening": {"zone": "DXB-MAR", "daypart": "evening", "product": "pistachio-knafeh"},
    "morning-deira": {"zone": "DXB-DEI", "daypart": "morning", "product": "saj-zaatar"},
    "summer-detox": {"zone": "DXB-DTN", "daypart": "midday", "product": "date-syrup-latte"},
}


@dataclass(frozen=True)
class Creative:
    slot: str
    lang: str
    size: str
    width: int
    height: int
    headline: str
    body: str
    cta: str
    zone: str
    daypart: str
    product: str
    svg: str
    seed: str

    @property
    def text(self) -> str:
        """Everything a reader would see, for the compliance check."""
        return f"{self.headline} {self.body} {self.cta}"


def _seed(slot: str, lang: str, size: str) -> str:
    return hashlib.sha256(f"{slot}|{lang}|{size}|sidra".encode()).hexdigest()[:12]


def _svg(brand: Brand, slot: str, lang: str, size: str, copy: dict[str, str]) -> str:
    w, h = SIZES[size]
    p = brand.palette
    rtl = lang == "ar"
    seed = _seed(slot, lang, size)

    # The angle of the wash is derived from the seed, so a slot's three sizes
    # are visibly the same campaign without being identical crops.
    angle = int(seed[:2], 16) % 60 + 15
    scale = h / 1080

    anchor = "end" if rtl else "start"
    x = w - int(w * 0.08) if rtl else int(w * 0.08)
    head_size = int(72 * scale * (0.82 if size == "landscape" else 1))
    body_size = int(34 * scale * (0.9 if size == "landscape" else 1))

    font = (
        "Noto Naskh Arabic, serif"
        if rtl
        else "Noto Sans Devanagari, sans-serif"
        if lang == "hi"
        else "Marcellus, Georgia, serif"
    )
    body_font = (
        "Noto Naskh Arabic, serif"
        if rtl
        else "Noto Sans Devanagari, sans-serif"
        if lang == "hi"
        else "Karla, sans-serif"
    )

    lines = _wrap(copy["headline"], 22 if size != "landscape" else 30)
    body_lines = _wrap(copy["body"], 40 if size != "landscape" else 52)

    # Headline lines are set at head_size * 1.12 apart, so the body has to clear
    # the whole block — not a fraction of one line. The earlier arithmetic used
    # 0.28 of a line height and the two ran straight through each other.
    head_leading = head_size * 1.12
    body_leading = body_size * 1.35
    block_h = head_leading * len(lines) + body_leading * len(body_lines)

    # Lay the whole text block out from a common baseline so a two-line headline
    # and a three-line body do not push the CTA off the artboard.
    top = int(h * (0.40 if size == "story" else 0.34))
    max_top = int(h * 0.80) - block_h
    head_y = int(min(top, max(int(h * 0.22), max_top)))
    body_y = head_y + head_leading * len(lines) + body_size * 0.4

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{_esc(copy["headline"])}">
  <defs>
    <linearGradient id="g{seed}" gradientTransform="rotate({angle})">
      <stop offset="0%" stop-color="{p["semolina"]}"/>
      <stop offset="62%" stop-color="{p["paper"]}"/>
      <stop offset="100%" stop-color="{p["date"]}" stop-opacity="0.30"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#g{seed})"/>
  <rect x="0" y="0" width="{w}" height="{int(h * 0.012)}" fill="{p["saffron"]}"/>
  <text x="{x}" y="{int(h * 0.12)}" text-anchor="{anchor}" font-family="{font}" font-size="{int(30 * scale)}" letter-spacing="{int(6 * scale)}" fill="{p["date"]}">SIDRA</text>
{chr(10).join(f'  <text x="{x}" y="{head_y + i * int(head_size * 1.12)}" text-anchor="{anchor}" font-family="{font}" font-size="{head_size}" fill="{p["ink"]}">{_esc(line)}</text>' for i, line in enumerate(lines))}
{chr(10).join(f'  <text x="{x}" y="{int(body_y) + i * int(body_size * 1.35)}" text-anchor="{anchor}" font-family="{body_font}" font-size="{body_size}" fill="{p["date"]}">{_esc(line)}</text>' for i, line in enumerate(body_lines))}
  <rect x="{x - (int(w * 0.30) if rtl else 0)}" y="{int(h * 0.86)}" width="{int(w * 0.30)}" height="{int(64 * scale)}" rx="{int(4 * scale)}" fill="{p["ink"]}"/>
  <text x="{x - (int(w * 0.15) if rtl else -int(w * 0.15))}" y="{int(h * 0.86) + int(42 * scale)}" text-anchor="middle" font-family="{body_font}" font-size="{int(26 * scale)}" letter-spacing="{int(2 * scale)}" fill="{p["semolina"]}">{_esc(copy["cta"])}</text>
</svg>"""


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        if len(cur) + len(word) + 1 > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines[:4]


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def compose(slot: str, lang: str = "en", size: str = "square") -> Creative:
    brand = load_brand()
    if slot not in COPY:
        raise KeyError(f"no slot {slot!r}; have {sorted(COPY)}")
    copy = COPY[slot][lang]
    meta = SLOT_META[slot]
    w, h = SIZES[size]
    return Creative(
        slot=slot,
        lang=lang,
        size=size,
        width=w,
        height=h,
        headline=copy["headline"],
        body=copy["body"],
        cta=copy["cta"],
        zone=meta["zone"],
        daypart=meta["daypart"],
        product=meta["product"],
        svg=_svg(brand, slot, lang, size, copy),
        seed=_seed(slot, lang, size),
    )


def all_creatives(size: str = "square") -> list[Creative]:
    return [compose(slot, lang, size) for slot in COPY for lang in LANGS]
