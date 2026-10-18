// The five themes as token sets (design §4.1). An asset takes `theme` (and an optional `accent`) as props
// and draws only with these tokens, so a theme changes palette, type, motion and texture, never the layout.
// scripts/export.ts writes them to themes.json for Python and the gallery.

export const THEME_NAMES = ['cinematic', 'dark', 'documentary', 'warm', 'pop'] as const;
export type ThemeName = (typeof THEME_NAMES)[number];

export type Theme = {
  name: ThemeName;
  label: string;
  // scenes draw their own backdrop: `bg` behind `ink` text
  bg: string;
  ink: string;
  inkSoft: string;
  // overlays sit on footage: `panel` (a CSS background) behind `panelInk` text; `scrim` darkens footage behind text
  panel: string;
  panelBorder: string;
  panelInk: string;
  panelInkSoft: string;
  panelAccent: string; // the accent as text or line on a panel
  overInk: string; // text straight on footage, with `shadow`
  scrim: string; // an "r,g,b" triple behind panelInk text on footage, used as rgba(scrim, alpha)
  titleFill: string; // a CSS background clipped to big titles
  accent: string; // the main accent (gold in cinematic); the `accent` prop overrides it
  accent2: string; // a second accent (ember, teal, peach, ...)
  cta: string; // the colour of a call-to-action button (Subscribe)
  muted: string;
  particle: string; // colour of dust and motes
  shadow: string; // text shadow over footage
  fonts: {
    display: string; // big titles
    title: string; // names, headings
    body: string; // labels and buttons
    italic: string; // the soft line under a title (rendered italic)
    rtl: string; // right-to-left text (Arabic script)
    rtlDisplay: string; // right-to-left titles
  };
  weights: {display: number; title: number; body: number; rtl: number; rtlDisplay: number};
  upper: boolean; // titles in capitals
  tracking: number; // extra letter spacing for titles, in px at 1080p
  motion: 'soft' | 'linear' | 'spring';
  pace: number; // > 1 is slower
  fx: {particles: number; glow: number; smoke: number; rays: number; grain: number}; // 0..1 each
};

export const THEMES: Record<ThemeName, Theme> = {
  cinematic: {
    name: 'cinematic', label: 'Cinematic and epic',
    bg: '#0b0907', ink: '#f6eedd', inkSoft: '#d9cdb6',
    panel: 'linear-gradient(180deg, rgba(22,18,14,0.62) 0%, rgba(10,8,6,0.72) 100%)', panelBorder: 'rgba(240,220,170,0.18)',
    panelInk: '#f3ead9', panelInkSoft: '#bfae8a', panelAccent: '#d2b06a', overInk: '#f3ead9', scrim: '5,4,3',
    titleFill: 'linear-gradient(180deg, #fff3d0 10%, #d2b06a 55%, #8a6a32 100%)',
    accent: '#d2b06a', accent2: '#e0662e', cta: '#a8231d', muted: '#bfae8a', particle: '#f0dcaa',
    shadow: '0 2px 14px rgba(0,0,0,0.65)',
    fonts: {display: 'Playfair Display', title: 'Playfair Display', body: 'Inter', italic: 'EB Garamond', rtl: 'Noto Naskh Arabic', rtlDisplay: 'Noto Naskh Arabic'},
    weights: {display: 500, title: 500, body: 500, rtl: 500, rtlDisplay: 700},
    upper: true, tracking: 12, motion: 'soft', pace: 1,
    fx: {particles: 1, glow: 1, smoke: 1, rays: 1, grain: 0.2},
  },
  dark: {
    name: 'dark', label: 'Dark and moody',
    bg: '#07090b', ink: '#e4e9ec', inkSoft: '#9aa6ae',
    panel: 'linear-gradient(180deg, rgba(12,16,19,0.78) 0%, rgba(6,8,10,0.86) 100%)', panelBorder: 'rgba(150,175,190,0.22)',
    panelInk: '#e4e9ec', panelInkSoft: '#8d9aa3', panelAccent: '#e0525b', overInk: '#e4e9ec', scrim: '4,6,8',
    titleFill: 'linear-gradient(180deg, #ffffff 0%, #c9d2d8 55%, #7d8a94 100%)',
    accent: '#c0303a', accent2: '#4f9aa3', cta: '#b3202a', muted: '#7d8a94', particle: '#aebfc9',
    shadow: '0 2px 16px rgba(0,0,0,0.8)',
    fonts: {display: 'Bebas Neue', title: 'Bebas Neue', body: 'Inter', italic: 'Inter', rtl: 'Noto Naskh Arabic', rtlDisplay: 'Noto Naskh Arabic'},
    weights: {display: 400, title: 400, body: 400, rtl: 400, rtlDisplay: 600},
    upper: true, tracking: 10, motion: 'soft', pace: 1.25,
    fx: {particles: 0.45, glow: 0.3, smoke: 0.6, rays: 0, grain: 1},
  },
  documentary: {
    name: 'documentary', label: 'Documentary and clean',
    bg: '#f3f3f1', ink: '#16181b', inkSoft: '#4f555d',
    panel: 'rgba(250,250,248,0.94)', panelBorder: 'rgba(22,24,27,0.10)',
    panelInk: '#16181b', panelInkSoft: '#5b626b', panelAccent: '#d9462b', overInk: '#ffffff', scrim: '250,250,248',
    titleFill: 'linear-gradient(180deg, #16181b 0%, #16181b 100%)',
    accent: '#d9462b', accent2: '#2d6fd6', cta: '#d9462b', muted: '#8a9099', particle: '#ffffff',
    shadow: '0 1px 8px rgba(0,0,0,0.45)',
    fonts: {display: 'Inter', title: 'Inter', body: 'Inter', italic: 'Inter', rtl: 'Noto Naskh Arabic', rtlDisplay: 'Noto Naskh Arabic'},
    weights: {display: 700, title: 600, body: 500, rtl: 600, rtlDisplay: 700},
    upper: false, tracking: 0, motion: 'linear', pace: 0.9,
    fx: {particles: 0, glow: 0, smoke: 0, rays: 0, grain: 0},
  },
  warm: {
    name: 'warm', label: 'Warm and romantic',
    bg: '#2a1714', ink: '#fbefe4', inkSoft: '#e9cdbd',
    panel: 'linear-gradient(180deg, rgba(251,239,228,0.93) 0%, rgba(246,224,210,0.93) 100%)', panelBorder: 'rgba(201,119,111,0.35)',
    panelInk: '#4a2c2a', panelInkSoft: '#8a5d55', panelAccent: '#b4584c', overInk: '#fff3ea', scrim: '251,239,228',
    titleFill: 'linear-gradient(180deg, #fff6ec 0%, #f6cdb9 55%, #e39a86 100%)',
    accent: '#e39a86', accent2: '#f0c27b', cta: '#c9776f', muted: '#c9a598', particle: '#ffd9b8',
    shadow: '0 2px 18px rgba(60,20,15,0.55)',
    fonts: {display: 'Playfair Display', title: 'Playfair Display', body: 'Montserrat', italic: 'Playfair Display', rtl: 'Noto Naskh Arabic', rtlDisplay: 'Noto Naskh Arabic'},
    weights: {display: 400, title: 400, body: 500, rtl: 400, rtlDisplay: 400},
    upper: false, tracking: 2, motion: 'soft', pace: 1.15,
    fx: {particles: 0.7, glow: 1, smoke: 0, rays: 0.5, grain: 0.15},
  },
  pop: {
    name: 'pop', label: 'Energetic and pop',
    bg: '#1d0b4a', ink: '#ffffff', inkSoft: '#d9d2ff',
    panel: 'linear-gradient(135deg, #ff3d7f 0%, #7a3dff 100%)', panelBorder: 'rgba(255,255,255,0.35)',
    panelInk: '#ffffff', panelInkSoft: '#ffe9f2', panelAccent: '#ffd400', overInk: '#ffffff', scrim: '29,11,74',
    titleFill: 'linear-gradient(180deg, #fff27a 0%, #ffd400 50%, #ff9a00 100%)',
    accent: '#ffd400', accent2: '#00d1ff', cta: '#1d0b4a', muted: '#b8a9ff', particle: '#ffd400',
    shadow: '0 4px 0 rgba(0,0,0,0.25)',
    fonts: {display: 'Montserrat', title: 'Montserrat', body: 'Montserrat', italic: 'Montserrat', rtl: 'Noto Naskh Arabic', rtlDisplay: 'Noto Naskh Arabic'},
    weights: {display: 900, title: 800, body: 700, rtl: 700, rtlDisplay: 700},
    upper: true, tracking: 2, motion: 'spring', pace: 0.8,
    fx: {particles: 0.6, glow: 0.4, smoke: 0, rays: 0, grain: 0},
  },
};

/** The theme an asset draws with: the named theme, with the `accent` prop replacing its accent colour. */
export const themeOf = (p: {theme: ThemeName; accent?: string | undefined}): Theme => {
  const t = THEMES[p.theme];
  return p.accent ? {...t, accent: p.accent, panelAccent: p.accent} : t;
};

/** [r, g, b] in 0..255 from #rrggbb. */
const rgb255 = (hex: string): number[] => {
  const n = parseInt(hex.slice(1, 7), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

/** A colour with an alpha, from #rrggbb. */
export const alpha = (hex: string, a: number): string => `rgba(${rgb255(hex).join(',')},${a})`;

/** [r, g, b] in 0..1 from #rrggbb (for SVG colour matrices and WebGL). */
export const rgbUnit = (hex: string): number[] => rgb255(hex).map((c) => c / 255);

/** True when the colour #rrggbb is light: its luma (Rec. 601) is over half, so dark text reads on it. */
export const isLightColour = (hex: string): boolean => {
  const [r, g, b] = rgb255(hex);
  return 0.299 * r + 0.587 * g + 0.114 * b > 128;
};

/** True for the light theme (documentary): it veils with white where the others darken. */
export const isLightTheme = (t: {name: ThemeName}): boolean => t.name === 'documentary';
