# 0000: The research behind the first design (October 2026)

Before hone-motif existed, two prototype galleries were built on 2026-10-10 for the YouTube version of a
music video made with hone-music-video, with its footage as the background. Every number below was measured on the reference machine (a laptop with an RTX 4060 8 GB GPU,
not used: everything rendered on the CPU). The owner reviewed both galleries; their choices are the
decisions.

## 1. Sixteen assets in Remotion

Sixteen extras for a 16:9 video, each a Remotion 4.0.534 composition with typed props, rendered at
1920×1080 and 32 fps, composited over the footage:

| Kind | Assets |
|---|---|
| overlays (6) | like & subscribe (a glass pill, a cursor presses Like and Subscribe, the bell swings); notification bell (a gold medallion, a bilingual line); channel watermark (an eight-pointed star with a monogram, a periodic glint, loopable); now playing (equaliser bars, a title in two languages); credits (a side panel, bilingual roles rising); social handles (generic icons, no platform logos) |
| scenes (6) | intro title (god rays, smoke, gold dust; a right-to-left title wipes in right to left); chapter card ("VERSE I" with an eight-pointed star); epigraph (a classical couplet, translation and attribution); outro thanks; end screen (calm frames for YouTube's own elements); next-chapter teaser |
| transitions (4) | light leak (amber and gold blooms, screen blend); film burn; ink wipe; dust fade (to black with drifting gold dust) |

What carried over into the design:

- **Typed props are the contract.** Each asset's props were a zod schema; a small Node script exported
  them as JSON Schema into one `assets.json` with the defaults and placement metadata. That file is the
  seed of `asset.json` and `props.schema.json` (design §2, §5).
- **Placement metadata a planner can use.** Each prototype carried a slot, a "when" sentence ("the first
  instrumental gap after 30–60 s, never over a lyric line"), a screen region ("bottom-left 520×200"), a
  repeat rule ("once per video", "≤ 3 per video") and moods. They became the placement rules of design
  §2.5. Missing in the prototypes, and added: maximum text lengths, scripts, aspect ratios and duration
  ranges.
- **Transitions are two layers and a cut.** Each transition rendered a matte (white where the incoming
  shot shows) and an fx layer; the light leak's fx is opaque on black and laid with a screen blend, the
  others are alpha. The cut sits at the middle (frame 48 of 96 at 32 fps). Design §2.7, §8.3.
- **Render times** (Chrome frames, concurrency 2, SwiftShader; then ffmpeg): 6–14 s of Chrome for 4–7 s
  overlays, 7–32 s for 4–8 s scenes, 71 s for the 20 s end screen, 8–21 s for the two layers of a 3 s
  transition. All sixteen took 278 s of Chrome and 220 s of ffmpeg, about 17 s of Chrome per asset.
- **File sizes.** WebM VP9 with alpha: 0.09–1.3 MB per overlay or scene; a transition's fx layer up to
  2.4 MB and its matte 10–262 KB. ProRes 4444 for the same overlays: 14–371 MB, 100 to 1200 times larger.
  Hence WebM alpha by default and ProRes on request (decision D-005).

## 2. Thirty-four caption styles

A second gallery tried animated lyric captions on a 12–15 s excerpt of the song, mostly in an Arabic-script language: 20
styles written in Remotion (karaoke fill, word pop, slide-in, typewriter, neon, bouncing ball, masked
rise, bilingual, calligraphic drift, …), 6 refinements of the owner's favourite, 3 combinations, and 5 made
with community packages (remotion-subtitle 2.0.0 and pycaps 0.3.0, both MIT). Each took 25–38 s to render.

- **The owner's favourite is the karaoke fill:** each word fills gold, right to left, as it is sung
  (a bold Arabic-script face); refined with a smooth in-word sweep and a soft glow.
- **Right-to-left text in Chrome is correct when words stay whole runs.** Remotion renders in Chrome,
  which shapes Arabic script correctly as long as each word is one run of text. remotion-subtitle's waving
  caption splits text into single characters, and the joined letters came apart. pycaps joined the
  letters but laid the line out left to right, reversing the word order, until a 15-line patch mirrored
  each line. Hence the rule: whole-word runs, never per-character animation for joining scripts (design
  §11), and a golden right-to-left poster for every asset that declares the script (design §14 case 14).
- **Captions in hone-motif.** Caption styles are themed, code-built, rendered by the same machinery with
  the same fonts and right-to-left rules, and wanted by other projects too (oneshot-studio's story songs,
  hone-frame's scenes). What is specific to a music video is the timing, which hone-music-video already
  owns. So caption styles become a kind and a category of hone-motif, and the consumer passes the timed
  words as props (decision D-003).

## 3. YouTube's end screens and brand rules

- End screens run during the last **5–20 s** of a video at least **25 s** long, with up to **four**
  elements on 16:9 (video, playlist, subscribe, channel, link); they are not available on videos made for
  kids. YouTube draws the clickable elements itself; an end-screen asset only leaves calm areas for them.
- YouTube publishes **no pixel safe area**. The prototype used video tiles of 640×360, a subscribe circle
  of 280 px and a practical safe box of **96–1824 × 86–946 px** (on 1920×1080), clear of the title strip
  and the player controls. Watermarks and teasers are hidden while the end screen shows (design
  `clear_frame`).
- YouTube's brand rules forbid altering its icon (colours, stretching, effects, images inside it), and
  broader use needs a brand-use request. The prototypes used no YouTube logo, play-button icon or
  wordmark: the subscribe button is generic, in the channel's colours, and social handles use neutral
  icons (@, globe, note), not platform logos. Design §11.

## 4. Fonts and sources

All fonts were under the SIL Open Font License: Arabic-script faces (Noto Naskh Arabic among them),
Inter, Montserrat, Playfair Display, EB Garamond and Bebas Neue. All visuals were procedural (SVG,
gradients, noise filters, seeded particles); no stock media was used. The design keeps both rules: OFL
fonts only, procedural visuals or CC0 media with its source recorded (design §2.8, §11).

## 5. Remotion's licence

Remotion is source-available under the Remotion License: free for individuals, for-profit organisations
with up to three employees and non-profits; companies with more people need a Company License. The terms
change slightly in Remotion 5.0. The prototypes used 4.0.534. hone-motif is Apache-2.0 and keeps
Remotion behind its renderer port (design §8), states the licence in its README, and pins the version
(decision D-009).
