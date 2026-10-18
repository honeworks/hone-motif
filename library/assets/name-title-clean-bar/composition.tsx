// Name and title, clean bar: a panel opens from its edge with an accent bar on the reading side; the
// name and the role rise into it one after the other, and everything leaves the way it came. The panel has a
// fixed size per aspect (its region in asset.json), the text shrinks to fit it, and it sits on the
// title-safe margin of whichever anchor `corner` names.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useLayout} from '../../shared/layout.ts';
import {envelope, enter, useClock} from '../../shared/motion.ts';
import {Run, isRtl, scriptType, typeStyle} from '../../shared/text.tsx';
import {themeOf} from '../../shared/themes.ts';
import type {Props} from './schema.ts';

const EDGE = 0.05; // the title-safe margin, as a fraction of the frame
const HEIGHT = 20; // the panel's height in layout units (u)

/** The panel's box in px: `width` fixed per aspect, placed on the anchor's edges (or centred). */
const panelBox = (corner: Props['corner'], width: number, height: number, frameW: number, frameH: number) => {
  const [v, h] = corner === 'center' ? ['center', 'center'] : corner.split('-');
  const horizontal = h ?? 'center';
  const left = horizontal === 'left' ? EDGE * frameW : horizontal === 'right' ? (1 - EDGE) * frameW - width : (frameW - width) / 2;
  const top = v === 'top' ? EDGE * frameH : v === 'bottom' ? (1 - EDGE) * frameH - height : (frameH - height) / 2;
  return {left, top, fromLeft: horizontal !== 'right'};
};

export const Component: React.FC<Props> = (p) => {
  const t = themeOf(p);
  const {f, D} = useClock();
  const {width: W, height: H, portrait, aspect, u} = useLayout();
  const width = (aspect === '16:9' ? 0.4 : 0.8) * W;
  const height = HEIGHT * u;
  const box = panelBox(p.corner, width, height, W, H);
  const rtl = isRtl(p.name);
  const show = envelope(f, 0, D, 14 * t.pace, 12);
  const hidden = `${(1 - show) * 100}%`;
  const clip = box.fromLeft ? `inset(0 ${hidden} 0 0)` : `inset(0 0 0 ${hidden})`;
  const pad = 2.4 * u;
  const bar = 0.7 * u;
  const room = width - 2 * pad - bar - 1.6 * u;
  const name = scriptType(t, p.name, 'title', (portrait ? 6.4 : 6) * u);
  const role = scriptType(t, p.role, 'body', 3 * u);
  const nameIn = enter(f, 6, t);
  const roleIn = enter(f, 12, t);
  return (
    <AbsoluteFill>
      <div
        dir={rtl ? 'rtl' : 'ltr'}
        style={{
          position: 'absolute', left: box.left, top: box.top, width, height, boxSizing: 'border-box',
          display: 'flex', alignItems: 'stretch', gap: 1.6 * u, padding: pad, opacity: show,
          clipPath: clip, background: t.panel, border: `1px solid ${t.panelBorder}`, borderRadius: 0.8 * u,
          overflow: 'hidden',
        }}
      >
        <div style={{width: bar, flex: 'none', background: t.panelAccent, transform: `scaleY(${nameIn})`}} />
        <div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.8 * u, minWidth: 0}}>
          <Run
            text={p.name}
            style={{...typeStyle(p.name, name.type, room), color: t.panelInk, lineHeight: name.lineHeight ?? 1.2, opacity: nameIn, transform: `translateY(${(1 - nameIn) * 2 * u}px)`}}
          />
          {p.role && (
            <Run
              text={p.role}
              style={{...typeStyle(p.role, role.type, room), color: t.panelInkSoft, lineHeight: role.lineHeight ?? 1.3, opacity: roleIn, transform: `translateY(${(1 - roleIn) * 2 * u}px)`}}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
