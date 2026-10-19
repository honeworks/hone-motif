# 0003: Brand tokens: an asset drawn in a channel's own colours and fonts

## Status

`accepted (approved by the maintainer 2026-10-19)` and implemented the same day. Asked for while
building hone-youtube-preparation (its decision D-012: "a full brand token set needs a hone-motif design
change, proposed there separately"); approved with "do it. make the changes. push". Two details changed
while building it, marked below: the golden posters are named `brand`, and the contrast warning comes
from `brand_warnings` and the placement check, not from `check_props`.

## Context

Every asset takes `theme` (one of five token sets, design §4.1) and an optional `accent` colour (§2.6).
That fits a video with a mood. It does not fit a channel with a brand: hone-youtube-preparation builds a
brand kit for each channel (a palette of five colours, a display and a text font, a corner mark) and
draws its thumbnails, banner and watermark in it, but its end screen, rendered with hone-motif, can only
take the nearest theme and the accent. On the first real project (2026-10-19) the end screen came out in
the `cinematic` theme's Playfair Display and cream ink while the thumbnails used the channel's own
font and ink, so the two did not look like the same channel. The research behind the brand kit says
recognisable brands come from the same few assets used everywhere (hone-youtube-preparation, research
§7.2).

## Problem

A consumer cannot ask an asset to draw in its own colours and fonts. The only ways around it are worse:
a new theme in `themes.ts` for every channel (a library change per channel, and themes are reviewed per
asset with golden posters), or a copy of each asset per brand (the counting rule of §11 forbids
recolours as new assets).

## Options

1. **Leave it** (today): the nearest theme plus the accent. Cheap; the channel's look is lost in its
   motion assets.
2. **Brand themes in the library**: a project adds `library/brands/<name>.json` and may name it as a
   theme. Every asset would have to list it in `themes` and get a golden poster for it, so every new brand
   touches every asset.
3. **A `brand` prop on every asset** (proposed): an optional object that overrides some of the chosen
   theme's tokens: colours, and fonts from the library's font registry. The theme still gives the motion,
   texture and the tokens the brand leaves out. No asset changes; `themeOf` applies it.
4. **A `palette` prop only** (colours, no fonts): smaller, but the type is half of a brand, and the first
   real case differed in type more than in colour.

## Decision

Option 3.

- **The prop.** Every asset accepts `brand`, optional, beside `theme` and `accent`:

  ```json
  {"theme": "warm",
   "brand": {"bg": "#101114", "ink": "#f4f1ea", "inkSoft": "#c9c4b8", "accent": "#e8a33d",
             "accent2": "#5fb3b3", "muted": "#8a8f98",
             "fonts": {"display": "Montserrat", "body": "Inter"}}}
  ```

  Every field is optional. Colours are `#rrggbb`. Font names must be families in the library's font
  registry (`library/fonts/fonts.json`, SIL OFL 1.1 only, §2.8); a project adds its own fonts there, as
  it adds its own assets (`hone-motif init`).
- **How it applies.** `themeOf(p)` starts from `THEMES[p.theme]`, then the brand, then `accent` (which
  stays the strongest, for compatibility):
  - `bg`, `ink`, `inkSoft`, `accent`, `accent2`, `muted` replace the same tokens;
  - the panel tokens follow from them (`panelInk` = `ink`, `panelInkSoft` = `inkSoft`, `panelAccent` =
    `accent`, `overInk` = `ink`, `particle` = `ink`, `scrim` from `bg`), unless the theme is light and the
    brand's `bg` is dark (or the other way round), in which case the theme's panel tokens are kept and
    only the accents change, so text on footage keeps its contrast;
  - `fonts.display` replaces `display` and `title`; `fonts.body` replaces `body` and `italic`;
    right-to-left fonts (`rtl`, `rtlDisplay`) are kept from the theme unless the brand names them as
    `fonts.rtl`;
  - motion, pace, effects, `upper` and `tracking` stay the theme's.
- **The schema.** `shared/schema.ts`'s `base()` adds `brand` (zod, strict), so every exported
  `props.schema.json` gains it; `check_props` validates it like any prop (unknown keys, colour patterns,
  font names against the registry: a new check in Python, `brand-font-unknown`).
- **Checks.** A brand whose `ink` on `bg` is under 4.5:1 contrast is a warning (`brand-low-contrast`),
  not an error: the consumer decides. *As built:* `check_props` returns only errors, so the warning comes
  from `hone_motif.brand_warnings(props)` and from `check_placements` (a placement warning).
- **Cache.** The brand is part of the props, so it is part of the render key already (§8.4).
- **Gallery.** Each asset gets a "brand" tile per aspect (its first theme with the library's sample
  brand, `shared/brand.ts`, exported to `library/sample-brand.json`), so an author sees an asset survive
  someone else's colours and fonts.
- **Golden posters.** One more golden poster per asset and aspect: its first theme with the sample brand
  (*as built:* named `brand`, `brand@9:16`, …, like the theme posters), so a change that ignores the brand
  is caught by the render tests (§12).

### Guarantees added (design §14)

- An asset rendered with a `brand` draws its text in the brand's display font and its accent in the
  brand's accent (render test: the poster differs from the theme's and matches its golden hash).
- A `brand` with an unknown font is refused by `check_props` with `brand-font-unknown`, naming the
  registry's families; a low-contrast brand gives `brand-low-contrast` as a warning.
- Props without `brand` render exactly as today (every existing golden poster is unchanged).

### Milestone

One: the zod and Python schema, `themeOf`, the two checks, the sample brand, the gallery preview, the
golden posters, the docs. Then hone-youtube-preparation passes its brand kit's palette and fonts in the
end-screen props (its own small follow-up; until then it keeps the nearest theme and the accent).

## Consequences

- A channel's end screen, intros, lower thirds and watermark can match its thumbnails and banner.
- Every asset gains a prop it did not ask for; authors must keep drawing only with theme tokens (§11
  already requires it), or the brand will not reach their asset. The brand golden poster catches it.
- Brands with a light `bg` on a dark theme (or the reverse) keep the theme's panels; a consumer who
  wants a light brand should pick a light theme (`documentary`).
- One more poster per asset in the render suite (about a third longer).

## Migration and compatibility

Additive. Assets, props and records without `brand` behave exactly as before: no default is filled in,
so an absent `brand` is not part of the props, and every existing golden poster matched unchanged. The
render cache re-renders once, because `shared/themes.ts` now imports `shared/brand.ts` and shared code is
part of the key (§8.4, D-026). `props.schema.json` files gain an optional property:
a consumer validating replies against an older export keeps working. Projects that copied the library
with `hone-motif init` get the change by re-running `npm run export` after updating their copy of
`shared/`.
