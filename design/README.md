# Why hone-motif exists

> Ask for "an end screen for a dark, tragic music video, 16:9" and get a short list of finished,
> tested assets that fit, each with the props a model may fill and the rules for where it may go. Let a
> model place them across the whole video in one call, check every placement in code, and render each
> asset once.

## The problem

Every finished video needs the same small pieces around its main footage: an intro title, a "like and
subscribe" nudge, a now-playing lower third, chapter cards, transitions between scenes, credits, an outro
and an end screen. Today these pieces are a mess for a generative pipeline:

- **Templates live in editors.** After Effects or CapCut templates need a person at a timeline. A
  pipeline can't search them, fill their text safely or render them unattended.
- **Generated video can't do graphics.** Image and video models can't set crisp text, keep a channel
  colour exact, or place a button inside YouTube's end-screen frame; they draw something that looks
  almost right.
- **One look doesn't fit every video.** A gold-and-ember title made for an epic suits neither a cooking
  channel nor a love song. Each project ends up drawing its own, so nothing is reused.
- **Placement is the hard part, and it is unchecked.** Where an overlay may go (not over a sung line, not
  in the end-screen area, not twice in a minute), how long a title may be, which transitions fit a mood:
  this lives in someone's head. A model asked to place assets one at a time loses the whole video, and
  nothing catches a title that overflows or an end screen in a 20-second video.
- **Right-to-left text breaks.** Many caption and motion tools split text into single characters for
  their animations, which tears Arabic and other joined letters apart, or lay lines out left to right, which
  reverses the word order.

## The core ideas

1. **Assets are code.** Each asset is a small Remotion composition with a typed props schema, so it
   renders the same every time, takes text and colours as data, and can be reviewed and versioned like
   any other code. Hundreds of them, in seventeen categories.
2. **Metadata a model can act on.** Every asset says what it is (category, kind, tags, themes, moods),
   where it can go (slot, screen region, time window, repeat limits, quiet passages only), what it
   accepts (props with maximum text lengths, scripts and languages, aspect ratios, duration) and where it
   came from (licence, fonts, sources). The metadata is plain JSON and needs no Remotion to read.
3. **Themes, not one look.** Each category comes in several themes (cinematic and epic, dark and moody,
   documentary and clean, warm and romantic, energetic and pop), so a project picks assets that match its
   style and mood.
4. **One placement call, checked by code.** A consumer gives a model the video's facts and a filtered
   catalogue, gets back every placement at once (`asset`, `start_ms`, `props`), and hone-motif checks
   each one against the asset's schema and rules before anything renders.
5. **Render once.** A render is keyed by its inputs and cached; media is never committed. Rendering goes
   through a renderer port, so another renderer could replace Remotion without touching the metadata,
   the search or the checks.

## Non-goals

Generating images or video with AI models, editing on a timeline, compositing a whole video (consumers
lay the rendered assets over their own footage), hosting or streaming media, a template marketplace,
platform logos or brand assets (the assets use generic buttons and icons), and AI calls of its own in
0.1 (the consumer makes the placement call).
