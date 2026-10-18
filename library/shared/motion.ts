// Time and easing. Motion is written in ticks of 1/32 s (the prototypes' frame rate), so an asset moves
// the same at any frame rate: useClock() converts the current frame to ticks (design §2.3).
import {Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Theme} from './themes.ts';

export const TICKS = 32; // ticks per second
export const W = 1920; // the frame in px: assets are drawn at 1080p (16:9)
export const H = 1080;
export const TAU = 2 * Math.PI;

/** `v` folded into [0, m) (a modulo that is never negative). */
export const mod = (v: number, m: number): number => ((v % m) + m) % m;

/** Clamp to 0..1 (springs overshoot; opacity and widths must not). */
export const clamp01 = (x: number): number => Math.max(0, Math.min(1, x));

/** The seeded random numbers of item `i`: `r('x')` is a fixed number in [0, 1). */
export const seeded = (seed: string | number, i: number) => (k: string): number => random(`${seed}-${i}-${k}`);

/** Indices 0..n-1, for drawing `n` items. */
export const range = (n: number): number[] => Array.from({length: Math.max(0, Math.round(n))}, (_, i) => i);

/** The current time `f` and the length `D`, in ticks. */
export const useClock = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {f: (frame * TICKS) / fps, D: (durationInFrames * TICKS) / fps};
};

export const EASE = Easing.bezier(0.22, 1, 0.36, 1); // soft "expo out"
export const EASE_IN = Easing.bezier(0.55, 0, 0.75, 0.2);
const LINEAR = (x: number) => x;

/** The theme's easing: soft (expo out), linear (documentary) or a slight overshoot (pop). */
export const easeOf = (t: Theme): ((x: number) => number) =>
  t.motion === 'linear' ? Easing.inOut(Easing.quad) : t.motion === 'spring' ? Easing.out(Easing.back(1.7)) : EASE;

/** Map a tick range to an output range, eased and clamped. */
export const ramp = (f: number, [a, b]: [number, number], [x, y]: [number, number] = [0, 1], ease = EASE) =>
  interpolate(f, [a, b], [x, y], {easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

/** 0 -> 1 -> 0: in over `inF` ticks from `start`, out over `outF` ticks ending at `end`. */
export const envelope = (f: number, start: number, end: number, inF: number, outF: number, ease = EASE) =>
  Math.min(ramp(f, [start, start + inF], [0, 1], ease), 1 - ramp(f, [end - outF, end], [0, 1], EASE_IN));

/** A spring in ticks (deterministic: it depends only on the tick). */
export const pop = (f: number, at: number, damping = 10, stiffness = 170) =>
  spring({frame: f - at, fps: TICKS, config: {damping, stiffness}});

export const linear = LINEAR;
export const smooth = (x: number) => x * x * (3 - 2 * x);

/** An entrance from 0 to 1 starting at tick `at`, in the theme's pace and easing (a spring for pop). */
export const enter = (f: number, at: number, t: Theme, ticks = 22): number =>
  t.motion === 'spring' ? Math.min(1, pop(f, at, 11, 190)) : ramp(f, [at, at + ticks * t.pace], [0, 1], easeOf(t));
