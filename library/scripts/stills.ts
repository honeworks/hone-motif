// Poster stills of assets in every theme and aspect they support and their samples, without rendering
// video (design §11, decision D-027). For authors: `npm run stills -- <out dir> [id or prefix* ...]` writes
// <out>/<id>--<theme or sample>.jpg at half size (960x540 for 16:9; other aspects add @<aspect>, e.g.
// <id>--warm@9:16.jpg); look at every one before committing an asset. The render suite and the gallery use
// it in batch: `--ids-file <file>` (one id per line), `--bundle <dir>` (reuse a bundle instead of building
// one into build/stills-bundle), `--scale <s>`, and HONE_STILLS_CONCURRENCY (default 4) stills at a time
// in one browser.
import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const ROOT = path.resolve(import.meta.dirname, '..');
const TICKS = 32; // the registry's frame rate (src/Root.tsx)
const BASE: Record<string, [number, number]> = {'16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080], '4:5': [1080, 1350]};

const args = process.argv.slice(2);
const option = (name: string): string | undefined => {
  const i = args.indexOf(name);
  return i >= 0 ? args.splice(i, 2)[1] : undefined;
};
const idsFile = option('--ids-file');
const bundleDir = option('--bundle');
const scale = Number(option('--scale') ?? '0.5');
const [out, ...only] = args;
if (!out) {
  console.error('usage: npm run stills -- <out dir> [id or prefix* ...] [--ids-file f] [--bundle dir] [--scale s]');
  process.exit(2);
}
const wanted = [...only, ...(idsFile ? fs.readFileSync(idsFile, 'utf8').split('\n').filter(Boolean) : [])];
const matches = (id: string) =>
  !wanted.length || wanted.some((o) => (o.endsWith('*') ? id.startsWith(o.slice(0, -1)) : id === o));

const serveUrlOf = async (): Promise<string> => {
  if (bundleDir && fs.existsSync(path.join(bundleDir, 'index.html'))) return path.resolve(bundleDir);
  const dir = path.resolve(bundleDir ?? path.join(ROOT, 'build', 'stills-bundle'));
  fs.rmSync(dir, {recursive: true, force: true});
  return bundle({entryPoint: path.join(ROOT, 'src', 'index.ts'), outDir: dir, publicDir: path.join(ROOT, 'fonts')});
};

type Still = {id: string; name: string; aspect: string; props: Record<string, unknown>; frame: number};
const stills: Still[] = [];
for (const id of fs.readdirSync(path.join(ROOT, 'assets')).sort()) {
  if (!fs.existsSync(path.join(ROOT, 'assets', id, 'asset.json')) || !matches(id)) continue;
  const meta = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets', id, 'asset.json'), 'utf8'));
  const sets: [string, Record<string, unknown>][] = meta.themes.map((t: string) => [t, {...meta.props, theme: t}]);
  for (const [name, props] of Object.entries(meta.samples ?? {})) sets.push([name, props as Record<string, unknown>]);
  for (const aspect of meta.aspects as string[]) {
    for (const [name, props] of sets) {
      stills.push({id, name: aspect === '16:9' ? name : `${name}@${aspect}`, aspect, props, frame: Math.round((meta.poster_ms * TICKS) / 1000)});
    }
  }
}

fs.mkdirSync(out, {recursive: true});
const serveUrl = await serveUrlOf();
const chromiumOptions = {gl: 'swangle' as const};
const puppeteerInstance = await openBrowser('chrome', {chromiumOptions});
let failed = 0;
const one = async (s: Still) => {
  try {
    const selected = await selectComposition({serveUrl, id: `${s.id}--poster`, inputProps: s.props, chromiumOptions, puppeteerInstance});
    const composition = {...selected, width: BASE[s.aspect][0], height: BASE[s.aspect][1]};
    await renderStill({serveUrl, composition, inputProps: s.props, frame: Math.min(composition.durationInFrames - 1, s.frame),
      output: path.join(out, `${s.id}--${s.name}.jpg`), imageFormat: 'jpeg', jpegQuality: 85, scale, chromiumOptions, puppeteerInstance});
    console.log(s.id, s.name);
  } catch (e) {
    failed++;
    console.error(`FAILED ${s.id} ${s.name}: ${(e as Error).message.split('\n')[0]}`);
  }
};
const queue = [...stills];
const workers = Array.from({length: Number(process.env.HONE_STILLS_CONCURRENCY ?? 4)}, async () => {
  for (let s = queue.shift(); s; s = queue.shift()) await one(s);
});
await Promise.all(workers);
await puppeteerInstance.close({silent: true});
process.exit(failed ? 1 : 0);
