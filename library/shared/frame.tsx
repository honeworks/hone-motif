// How every asset is registered (src/Root.tsx is generated from the asset.json files by scripts/export.ts):
// the asset itself, a `--matte` composition for transitions, and a `--poster` composition that lays the
// asset over a neutral stand-in for footage, used for the poster still (design §8.3, §12).
import React from 'react';
import {AbsoluteFill, Composition} from 'remotion';
import type {z} from 'zod';
import {FontGate} from './fonts.tsx';
import {H, W} from './motion.ts';

export type Layer = 'fx' | 'matte';
export type AssetProps = Record<string, unknown> & {layer?: Layer};
type AnyComponent = React.FC<any>; // each asset's component takes its own props type

export type Entry = {
  id: string; kind: string; frames: number; blend: 'normal' | 'screen';
  Component: AnyComponent; schema: z.ZodType; props: Record<string, unknown>;
};

const FPS = 32;

/** A stand-in for footage: a dim, cool gradient (a) or a warmer one (b, the incoming shot of a transition). */
const Backdrop: React.FC<{variant: 'a' | 'b'}> = ({variant}) => (
  <AbsoluteFill style={{background: variant === 'a'
    ? 'radial-gradient(ellipse 60% 50% at 70% 35%, #5b6b80 0%, transparent 70%), linear-gradient(180deg, #34404f 0%, #1d242d 55%, #0f1318 100%)'
    : 'radial-gradient(ellipse 55% 45% at 30% 40%, #b08a62 0%, transparent 70%), linear-gradient(180deg, #6e5a46 0%, #3a2e24 60%, #1c1612 100%)'}} />
);

const Parsed: React.FC<{entry: Entry; props: AssetProps; layer?: Layer}> = ({entry, props, layer}) => {
  const {Component, schema} = entry;
  return <FontGate><Component {...(schema.parse(props) as object)} layer={layer} /></FontGate>;
};

/** A transition over two stand-in shots: outgoing * (1 - matte) + incoming * matte, then the fx layer. */
const TransitionPoster: React.FC<{entry: Entry; props: AssetProps}> = ({entry, props}) => (
  <AbsoluteFill style={{isolation: 'isolate', background: '#000'}}>
    <AbsoluteFill style={{isolation: 'isolate'}}>
      <Backdrop variant="b" />
      <AbsoluteFill style={{mixBlendMode: 'multiply'}}><Parsed entry={entry} props={props} layer="matte" /></AbsoluteFill>
    </AbsoluteFill>
    <AbsoluteFill style={{isolation: 'isolate', mixBlendMode: 'plus-lighter'}}>
      <Backdrop variant="a" />
      <AbsoluteFill style={{mixBlendMode: 'multiply', filter: 'invert(1)'}}><Parsed entry={entry} props={props} layer="matte" /></AbsoluteFill>
    </AbsoluteFill>
    <AbsoluteFill style={{mixBlendMode: entry.blend === 'screen' ? 'screen' : 'normal'}}><Parsed entry={entry} props={props} layer="fx" /></AbsoluteFill>
  </AbsoluteFill>
);

const Poster: React.FC<{entry: Entry; props: AssetProps}> = ({entry, props}) =>
  entry.kind === 'transition' ? <TransitionPoster entry={entry} props={props} /> : (
    <AbsoluteFill><Backdrop variant="a" /><Parsed entry={entry} props={props} /></AbsoluteFill>
  );

/** The compositions of one asset: `<id>`, `<id>--matte` (transitions only) and `<id>--poster`. */
export const Entries: React.FC<{entry: Entry}> = ({entry}) => {
  const common = {durationInFrames: entry.frames, fps: FPS, width: W, height: H, defaultProps: entry.props as AssetProps};
  return (
    <>
      <Composition id={entry.id} component={(p: AssetProps) => <Parsed entry={entry} props={p} layer={entry.kind === 'transition' ? 'fx' : undefined} />} {...common} />
      {entry.kind === 'transition' && <Composition id={`${entry.id}--matte`} component={(p: AssetProps) => <Parsed entry={entry} props={p} layer="matte" />} {...common} />}
      <Composition id={`${entry.id}--poster`} component={(p: AssetProps) => <Poster entry={entry} props={p} />} {...common} />
    </>
  );
};
