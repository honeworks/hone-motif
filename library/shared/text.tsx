// Text that is safe for right-to-left scripts and always fits (design §11). Text is set as whole runs with
// `dir` and isolation; animations reveal whole words, lines or masks over them, never single characters of
// a joining script. Sizes shrink by measurement to fit their box, never overflow.
import React from 'react';
import {interpolate} from 'remotion';
import {measureText} from '@remotion/layout-utils';

const RTL_CHAR = /[֐-ࣿיִ-﷿ﹰ-﻿]/;
const STRONG = /[A-Za-zÀ-ɏͰ-ӿ֐-ࣿיִ-﷿ﹰ-﻿]/;

/** True when the first strong character of `s` belongs to a right-to-left script. */
export const isRtl = (s: string): boolean => {
  const first = s.match(STRONG);
  return first !== null && RTL_CHAR.test(first[0]);
};

export type Type = {family: string; weight: number; size: number; tracking?: number; upper?: boolean; italic?: boolean};

/** The width of `s` set in `t`, in px (as drawn: tracking, capitals and italics included). */
export const widthOf = (s: string, t: Type): number => measureText({
  text: s, fontFamily: t.family, fontSize: t.size, fontWeight: t.weight,
  letterSpacing: `${t.tracking ?? 0}px`, textTransform: t.upper ? 'uppercase' : 'none',
  additionalStyles: t.italic ? {fontStyle: 'italic'} : {},
}).width;

/** The font size at which `s` fits in `maxWidth` px: `t.size`, or smaller when measured wider. */
export const fitSize = (s: string, t: Type, maxWidth: number): number => {
  if (!s) return t.size;
  const width = widthOf(s, t);
  return width > maxWidth ? Math.floor(t.size * (maxWidth / width) * 100) / 100 : t.size;
};

/** CSS for a piece of type, sized to fit `maxWidth` when given. */
export const typeStyle = (s: string, t: Type, maxWidth?: number): React.CSSProperties => {
  // letter spacing would pull the letters of a joining script apart (design §11)
  const tracked = isRtl(s) ? {...t, tracking: 0} : t;
  const size = maxWidth ? fitSize(s, tracked, maxWidth) : t.size;
  return {
    fontFamily: t.family, fontWeight: t.weight, fontSize: size, letterSpacing: (tracked.tracking ?? 0) * (size / t.size),
    textTransform: t.upper ? 'uppercase' : 'none', fontStyle: t.italic ? 'italic' : 'normal', whiteSpace: 'nowrap',
  };
};

/** One run of text in its own direction, isolated from its neighbours. */
export const Run: React.FC<{text: string; style?: React.CSSProperties}> = ({text, style}) => (
  <div dir={isRtl(text) ? 'rtl' : 'ltr'} style={{unicodeBidi: 'isolate', ...style}}>{text}</div>
);

/**
 * Reveal a block with a soft-edged mask sweeping in reading order, plus blur to sharp. Right-to-left
 * letters can overhang their line box, so for them the mask sits on an outer box with padding and an equal
 * negative margin (both in % of the parent's width, so they cancel in the layout); the inner box takes
 * `style`, its flex-item keys going to the outer one. Latin blocks keep the mask on their own box.
 */
export const MaskReveal: React.FC<{p: number; rtl?: boolean; blur?: boolean; children: React.ReactNode; style?: React.CSSProperties}> = ({p, rtl = false, blur = true, children, style = {}}) => {
  const edge = interpolate(p, [0, 1], [-25, 125]);
  const mask = `linear-gradient(${rtl ? 'to left' : 'to right'}, black ${edge - 25}%, transparent ${edge}%)`;
  const masked = {WebkitMaskImage: mask, maskImage: mask, filter: blur ? `blur(${(1 - p) * 6}px)` : undefined};
  if (!rtl) return <div style={{...masked, ...style}}>{children}</div>;
  const {flex, minWidth, alignSelf, ...inner} = style;
  return (
    <div style={{...masked, padding: '8% 4%', margin: '-8% -4%', flex, minWidth, alignSelf}}>
      <div style={inner}>{children}</div>
    </div>
  );
};

export type Role = 'display' | 'title' | 'body' | 'italic' | 'rtl' | 'rtlDisplay';

/** The theme's type for a role at `size` px (at 1080p); titles take the theme's capitals and tracking. */
export const roleType = (
  t: {fonts: Record<Role, string>; weights: {display: number; title: number; body: number; rtl: number; rtlDisplay: number}; upper: boolean; tracking: number},
  role: Role, size: number, extra: Partial<Type> = {},
): Type => {
  const weight = role === 'italic' ? t.weights.body : t.weights[role];
  const titled = role === 'display' || role === 'title';
  // a stack: text in another script falls back to a shipped font, never to a system one
  const rtl = role === 'rtl' || role === 'rtlDisplay';
  const family = `'${t.fonts[role]}', '${rtl ? t.fonts.body : t.fonts.rtl}'`;
  const type = {family, weight, size, upper: titled && t.upper, tracking: titled ? t.tracking : 0, italic: role === 'italic', ...extra};
  // the heaviest font files go to 900: asked for more (pop's 900 plus an asset's +100), the browser would fall back to 400
  return {...type, weight: Math.min(900, type.weight)};
};

type Fonts = Parameters<typeof roleType>[0];

/** The right-to-left role that stands in for each role when the text is right-to-left. */
const RTL_ROLE: Record<Role, Role> = {display: 'rtlDisplay', title: 'rtlDisplay', body: 'rtl', italic: 'rtl', rtl: 'rtl', rtlDisplay: 'rtlDisplay'};

/**
 * The type for `s` in `role`, and the line height right-to-left text needs. Right-to-left text takes the
 * theme's right-to-left role at the same size, without capitals, tracking or a slant (Arabic-script faces
 * have no italics) and with taller lines (1.45). For Latin text `lineHeight` is undefined: the caller keeps
 * its own (`lineHeight ?? 1.2`).
 */
export const scriptType = (t: Fonts, s: string, role: Role, size: number, extra: Partial<Type> = {}): {type: Type; lineHeight?: number} => {
  if (!isRtl(s)) return {type: roleType(t, role, size, extra)};
  return {type: roleType(t, RTL_ROLE[role], size, {...extra, upper: false, tracking: 0, italic: false}), lineHeight: RTL_LINE_HEIGHT};
};

/** The line height right-to-left text needs (scriptType). */
export const RTL_LINE_HEIGHT = 1.45;
