// Brand tokens (change 0003): an optional `brand` prop that draws an asset in a channel's own colours and
// fonts over the chosen theme. The theme still gives the motion, pace, effects and the tokens the brand
// leaves out; fonts must be families of the font registry (fonts/fonts.json).
import {z} from 'zod';
import type {Theme} from './themes.ts';

const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/).describe('a colour as #rrggbb');
const family = z.string().min(1).max(60).describe('a family of the library font registry (fonts/fonts.json)');

export const brandSchema = z
  .strictObject({
    bg: hex.optional().describe('the backdrop of scenes'),
    ink: hex.optional().describe('text on the backdrop'),
    inkSoft: hex.optional().describe('secondary text'),
    accent: hex.optional().describe('the main accent'),
    accent2: hex.optional().describe('a second accent'),
    muted: hex.optional().describe('quiet lines and labels'),
    fonts: z
      .strictObject({
        display: family.optional().describe('big titles and headings'),
        body: family.optional().describe('labels, buttons and soft lines'),
        rtl: family.optional().describe('right-to-left text (Arabic script)'),
      })
      .optional(),
  })
  .describe("a channel's colours and fonts, laid over the theme (change 0003)");
export type Brand = z.infer<typeof brandSchema>;

/** The sample brand the gallery and the render tests use: far from every theme, so ignoring it shows. */
export const SAMPLE_BRAND: Brand = {
  bg: '#0e2a2f', ink: '#e8fff6', inkSoft: '#9fd6c6', accent: '#ff7a1a', accent2: '#3ad1c4', muted: '#6fa79b',
  fonts: {display: 'Montserrat', body: 'Inter'},
};

const luma = (h: string): number => {
  const n = parseInt(h.slice(1, 7), 16);
  return 0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255);
};
const triple = (h: string): string => {
  const n = parseInt(h.slice(1, 7), 16);
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
};

/** The theme with the brand laid over it (change 0003). */
export const applyBrand = (t: Theme, b: Brand | undefined): Theme => {
  if (!b) return t;
  const out: Theme = {...t, fonts: {...t.fonts}};
  out.bg = b.bg ?? t.bg;
  out.ink = b.ink ?? t.ink;
  out.inkSoft = b.inkSoft ?? t.inkSoft;
  out.accent2 = b.accent2 ?? t.accent2;
  out.muted = b.muted ?? t.muted;
  if (b.accent) {
    out.accent = b.accent;
    out.panelAccent = b.accent;
    out.titleFill = `linear-gradient(180deg, ${out.ink} 0%, ${out.ink} 55%, ${b.accent} 100%)`;
  }
  // panels follow the brand only when its backdrop is as light (or as dark) as the theme's, so text on
  // footage keeps its contrast; otherwise only the accents change
  const sameSide = (luma(out.bg) > 128) === (luma(t.bg) > 128);
  if (sameSide) {
    out.panelInk = out.ink;
    out.panelInkSoft = out.inkSoft;
    out.overInk = out.ink;
    out.particle = out.ink;
    out.scrim = triple(out.bg);
  }
  if (b.fonts?.display) {
    out.fonts.display = b.fonts.display;
    out.fonts.title = b.fonts.display;
  }
  if (b.fonts?.body) {
    out.fonts.body = b.fonts.body;
    out.fonts.italic = b.fonts.body;
  }
  if (b.fonts?.rtl) {
    out.fonts.rtl = b.fonts.rtl;
    out.fonts.rtlDisplay = b.fonts.rtl;
  }
  return out;
};
