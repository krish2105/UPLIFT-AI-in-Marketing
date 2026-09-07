# Design directions

Three complete visual directions were built — not sketched — so the choice
could be made against running code rather than against a description. Each is a
full token system in OKLCH with a dark and a light register, and all three
render the *same* components through the *same* stylesheet, so what differs on
screen is the token system and nothing else.

Every ratio quoted anywhere in this project is measured by
`apps/web/scripts/check-contrast.mjs` and published to
[`docs/results/A2-contrast.json`](results/A2-contrast.json). At the time of
writing that is **102 pairs across three directions and both registers**, all
passing: body text at or above 4.5:1, borders and non-text indicators at or
above 3:1, and no colour outside the sRGB gamut.

Each direction commits to **one chroma rule** — a single statement of what
colour is allowed to mean — and everything else in the interface is neutral.
That constraint is the reason none of them reads as a generic dashboard.

## Almanac — "the weather station that sells coffee"

**Colour is temperature.** One thermal ramp, plus one violet that means a human
planned a promotion here. Ground is the slate-teal of the Gulf sky forty
minutes before dawn, which is when SIDRA's morning daypart actually begins;
the light register is cool plotting paper. Both are cold on purpose, so the
heat ramp is the only warmth on screen and reads as information immediately.

*Signature:* the **station strip** — the day's conditions in real meteorological
notation, including the prediction interval drawn as a bracket rather than
printed as a number, on every page.

*Type:* Bricolage Grotesque (variable width) · Instrument Sans · Martian Mono ·
Noto Kufi Arabic.

## Night Souk — "the city after dark, lit from within"

**Colour is the gap between expected and observed.** Brass is the forecast,
verdigris is what happened, and the moment they separate is the loudest event
on the screen — which is the whole point of a forecasting tool. Deliberately
*not* gold: this is aged brass on oud-black, a warm purple-black, because
"Dubai" plus "premium" produces gold-on-black in every template ever made.

*Signature:* the **mashrabiya veil** — a carved screen over the forecast where
each aperture's opening is the inverse of that day's prediction interval. A
confident day is a hole you see through; an uncertain one is screened shut.
Most interfaces render uncertainty as a fainter shade, which reads as "less
important" rather than "less known".

*Type:* Marcellus · Karla · DM Mono · Noto Naskh Arabic.

## Daypart — "the interface keeps the café's hours"

**Colour is the time of day.** SIDRA's demand is bimodal and the media
allocator optimises over channel × daypart, so the three hues are not a palette
sitting beside the data model — they *are* the data model. There is no separate
brand colour and no success green: a control that is not about a time of day is
neutral. The theme toggle is not an inversion of one design; it is two hours of
the same day.

*Signature:* the **daypart dial** — 24 hours of forecast demand as a clock,
showing the commuter lobe and the larger evening lobe with the midday trough
between them, and doubling as the filter that scopes every other tab.

*Type:* Archivo (variable width) · Figtree · Geist Mono · Noto Sans Arabic.

## What happens to the two that lose

They are deleted, along with the `/design` route that compares them. Carrying
unused token systems forward would leave three ways to style every future
component and no way to tell which one is current.
