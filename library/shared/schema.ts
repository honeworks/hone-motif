// Building blocks for the assets' zod props schemas (decision D-002). Every asset takes `theme` (one of the
// themes it supports) and an optional `accent`; text props carry their maximum length (design §2.6).
import {z} from 'zod';
import {THEME_NAMES, type ThemeName} from './themes.ts';

export const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/).describe('a colour as #rrggbb');

/** The props every asset accepts: `theme` (defaults to the first supported one) and an optional `accent`. */
export const base = (themes: readonly ThemeName[] = THEME_NAMES) => ({
  theme: z.enum(themes as [ThemeName, ...ThemeName[]]).default(themes[0]).describe('the look (design §4.1)'),
  accent: hex.optional().describe("replaces the theme's accent colour"),
});

/** A text prop of at most `max` characters. */
export const text = (max: number, what: string) => z.string().max(max).describe(what);

export const corner = z.enum(['top-left', 'top-right', 'bottom-left', 'bottom-right']);
export type Corner = z.infer<typeof corner>;

/** The nine anchors of the vocabulary: a `corner` prop may take any of them (decision D-028). */
export const anchor = z.enum(['top-left', 'top-center', 'top-right', 'center-left', 'center', 'center-right', 'bottom-left', 'bottom-center', 'bottom-right']);
export type Anchor = z.infer<typeof anchor>;

/** Timed text for caption assets, in milliseconds relative to the placement's start (design §2.6). */
export const word = z.object({text: z.string().min(1).max(40), start_ms: z.int().min(0), end_ms: z.int().min(0)});
export const captionLine = z.object({
  start_ms: z.int().min(0), end_ms: z.int().min(0), text: z.string().max(90).describe('the whole line'),
  words: z.array(word).min(1).max(24).describe('every word of the line in reading order'),
});
export type Word = z.infer<typeof word>;
export type CaptionLine = z.infer<typeof captionLine>;
