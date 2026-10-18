// Big title, clean rise: on the theme's backdrop a short accent rule draws out, the title rises into
// place over it and a subtitle fades in underneath; at the end everything fades back to the backdrop. Both
// lines shrink to fit 80% of the frame's width, inside the title-safe area.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useLayout} from '../../shared/layout.ts';
import {enter, envelope, useClock} from '../../shared/motion.ts';
import {Run, scriptType, typeStyle} from '../../shared/text.tsx';
import {themeOf} from '../../shared/themes.ts';
import type {Props} from './schema.ts';

export const Component: React.FC<Props> = (p) => {
  const t = themeOf(p);
  const {f, D} = useClock();
  const {width, portrait, u} = useLayout();
  const room = 0.8 * width;
  const out = envelope(f, 0, D, 1, 12);
  const rule = enter(f, 2, t);
  const titleIn = enter(f, 8, t);
  const subIn = enter(f, 18, t);
  const title = scriptType(t, p.title, 'display', (portrait ? 9 : 11) * u);
  const sub = scriptType(t, p.subtitle, 'italic', (portrait ? 3.6 : 3.4) * u);
  return (
    <AbsoluteFill style={{background: t.bg, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.4 * u, opacity: out}}>
        <div style={{width: 12 * u, height: 0.5 * u, background: t.accent, transform: `scaleX(${rule})`}} />
        <Run
          text={p.title}
          style={{...typeStyle(p.title, title.type, room), color: t.ink, lineHeight: title.lineHeight ?? 1.1, opacity: titleIn, transform: `translateY(${(1 - titleIn) * 3 * u}px)`}}
        />
        {p.subtitle && (
          <Run
            text={p.subtitle}
            style={{...typeStyle(p.subtitle, sub.type, room), color: t.inkSoft, lineHeight: sub.lineHeight ?? 1.3, opacity: subIn}}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};
