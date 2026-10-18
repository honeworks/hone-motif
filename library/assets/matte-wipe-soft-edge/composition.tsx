// Matte wipe, soft edge: a feathered edge crosses the frame on a slant; a thin line in the theme's accent
// rides the middle of the edge. The matte (white where the incoming shot shows) is black on the first frame
// and white on the last; the cut lies at the middle, when the edge crosses the centre (design §2.7).
import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {Layer} from '../../shared/frame.tsx';
import {ramp, smooth, useClock} from '../../shared/motion.ts';
import {alpha, themeOf} from '../../shared/themes.ts';
import type {Props} from './schema.ts';

const FEATHER = 22; // the soft edge, in % of the gradient line

export const Component: React.FC<Props & {layer?: Layer}> = (p) => {
  const t = themeOf(p);
  const {f, D} = useClock();
  const q = ramp(f, [4, D - 6], [0, 1], smooth);
  const angle = p.direction === 'ltr' ? 110 : 250;
  const edge = q * (100 + FEATHER); // where the black begins; white runs FEATHER % behind it
  if (p.layer === 'matte') {
    return <AbsoluteFill style={{background: `linear-gradient(${angle}deg, #fff ${edge - FEATHER}%, #000 ${edge}%)`}} />;
  }
  const mid = edge - FEATHER / 2;
  const glow = Math.sin(Math.PI * q); // the line shows while the edge is on screen
  const halo = alpha(t.accent, 0.35);
  return (
    <AbsoluteFill
      style={{
        opacity: glow,
        background: `linear-gradient(${angle}deg, transparent ${mid - 6}%, ${halo} ${mid - 0.8}%, ${t.accent} ${mid}%, ${halo} ${mid + 0.8}%, transparent ${mid + 6}%)`,
      }}
    />
  );
};
