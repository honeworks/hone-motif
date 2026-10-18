// The Remotion renderer's entry (design §8.2): `node scripts/render.ts <job.json>`. hone-motif's Python
// adapter writes the job; this script renders the layers it asks for and the poster into job.out_dir and
// prints {"layers": {...}, "poster": ...}. Rendering runs on the CPU (SwiftShader), needs no network, and
// reuses one bundle per library version (job.bundle_dir).
import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition, type Codec} from '@remotion/renderer';

type Format = 'webm' | 'h264' | 'prores';
type Job = {
  format_version: string; asset: string; kind: string; props: Record<string, unknown>; aspect: string; base: [number, number];
  fps: number; width: number; height: number; frames: number; poster_frame: number;
  layers: Record<string, Format>; out_dir: string; bundle_dir: string; concurrency: number;
  inputs: Record<string, string>;
};

const ROOT = path.resolve(import.meta.dirname, '..');
const chromiumOptions = {gl: 'swangle' as const};
const ENCODINGS: Record<Format, {codec: Codec; ext: string; imageFormat: 'png' | 'jpeg'; pixelFormat: string}> = {
  webm: {codec: 'vp9', ext: 'webm', imageFormat: 'png', pixelFormat: 'yuva420p'},
  h264: {codec: 'h264', ext: 'mp4', imageFormat: 'jpeg', pixelFormat: 'yuv420p'},
  prores: {codec: 'prores', ext: 'mov', imageFormat: 'png', pixelFormat: 'yuva444p10le'},
};
const MIME: Record<string, string> = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'};

/** The bundle for this library version: built once into a temporary folder, then renamed into place. */
const serveUrl = async (dir: string): Promise<string> => {
  if (fs.existsSync(path.join(dir, 'index.html'))) return dir;
  const tmp = `${dir}.tmp-${process.pid}`;
  await bundle({entryPoint: path.join(ROOT, 'src', 'index.ts'), outDir: tmp, publicDir: path.join(ROOT, 'fonts')});
  fs.mkdirSync(path.dirname(dir), {recursive: true});
  try {
    fs.renameSync(tmp, dir);
  } catch {
    fs.rmSync(tmp, {recursive: true, force: true}); // another process finished first: use its bundle
  }
  return dir;
};

/** File inputs (an image) travel as data URLs, so the bundle never needs the consumer's files. */
const withInputs = (job: Job): Record<string, unknown> => {
  const props = {...job.props};
  for (const [prop, file] of Object.entries(job.inputs)) {
    const mime = MIME[path.extname(file).toLowerCase()] ?? 'application/octet-stream';
    props[prop] = `data:${mime};base64,${fs.readFileSync(file).toString('base64')}`;
  }
  return props;
};

const composition = async (url: string, id: string, job: Job, inputProps: Record<string, unknown>) => {
  const c = await selectComposition({serveUrl: url, id, inputProps, chromiumOptions});
  // the asset lays itself out at the aspect's base size (useVideoConfig); scale takes it to the job's size
  return {...c, fps: job.fps, durationInFrames: job.frames, width: job.base[0], height: job.base[1]};
};

const threads = ({args}: {args: string[]}) => [...args.slice(0, -1), '-threads', '4', ...args.slice(-1)];

const renderLayer = async (url: string, job: Job, layer: string, format: Format, inputProps: Record<string, unknown>) => {
  const id = layer === 'matte' ? `${job.asset}--matte` : job.asset;
  const comp = await composition(url, id, job, inputProps);
  const enc = ENCODINGS[format];
  const file = `${layer}.${enc.ext}`;
  await renderMedia({
    serveUrl: url, composition: comp, inputProps, codec: enc.codec, outputLocation: path.join(job.out_dir, file),
    imageFormat: enc.imageFormat, pixelFormat: enc.pixelFormat as 'yuv420p', scale: job.width / comp.width,
    concurrency: job.concurrency, chromiumOptions, ffmpegOverride: threads, timeoutInMilliseconds: 120000,
    ...(format === 'prores' ? {proResProfile: '4444' as const} : {crf: format === 'webm' ? 30 : 18}),
  });
  return file;
};

const main = async () => {
  const job: Job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const url = await serveUrl(job.bundle_dir);
  const inputProps = withInputs(job);
  const layers: Record<string, string> = {};
  for (const [layer, format] of Object.entries(job.layers)) layers[layer] = await renderLayer(url, job, layer, format, inputProps);
  const poster = await composition(url, `${job.asset}--poster`, job, inputProps);
  await renderStill({serveUrl: url, composition: poster, inputProps, frame: job.poster_frame, output: path.join(job.out_dir, 'poster.jpg'),
    imageFormat: 'jpeg', jpegQuality: 88, scale: job.width / poster.width, chromiumOptions, timeoutInMilliseconds: 120000});
  console.log(JSON.stringify({layers, poster: 'poster.jpg'}));
};

await main();
