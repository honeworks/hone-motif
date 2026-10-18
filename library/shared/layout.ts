// The frame an asset lays itself out in (design §2.4, decision D-012): 1920x1080 for 16:9, 1080x1920 for
// 9:16, 1080x1080 for 1:1 and 1080x1350 for 4:5, whatever size the render is scaled to. Assets that declare
// more than 16:9 place things with these numbers instead of fixed 1920/1080 coordinates.
import {useVideoConfig} from 'remotion';

export type Aspect = '16:9' | '9:16' | '1:1' | '4:5';

export const aspectOf = (width: number, height: number): Aspect =>
  width > height ? '16:9' : width === height ? '1:1' : height / width > 1.5 ? '9:16' : '4:5';

/** The layout frame: its size, its aspect, and `u`, one hundredth of its shorter side (10.8 px). */
export const useLayout = () => {
  const {width, height} = useVideoConfig();
  const aspect = aspectOf(width, height);
  return {width, height, aspect, portrait: height > width, u: Math.min(width, height) / 100};
};
