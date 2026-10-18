// The library check on the Node side (design §11), run by `npm run check` after `tsc`: the derived files
// are up to date and the default props and samples pass each zod schema (scripts/export.ts --check), and
// the sources keep the authoring rules a reader can check by eye: no Math.random, clock or network, and
// no per-character splitting of text. Everything about asset.json itself is checked in Python
// (`hone-motif check`, run by the default test suite), which needs no Node (design/decisions.md D-016).
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');

const RULES: [RegExp, string][] = [
  [/Math\.random\s*\(/, "Math.random: use Remotion's seeded random(seed)"],
  [/\bDate\.now\s*\(|\bnew Date\s*\(/, 'the clock: an asset depends only on its props and the frame'],
  [/\bfetch\s*\(|XMLHttpRequest|https?:\/\/(?!www\.w3\.org)/, 'the network: fonts and media come from the library'],
  [/\.split\(\s*(''|"")\s*\)|Array\.from\(\s*(text|label|title|line|s)\s*\)|\[\.\.\.(text|label|title|line|s)\]/,
    'per-character text: animate whole words, lines or masks (right-to-left scripts, design §11)'],
];

const sources = (dir: string): string[] =>
  fs.readdirSync(dir, {withFileTypes: true}).flatMap((e) => {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) return sources(full);
    return /\.(ts|tsx)$/.test(e.name) ? [full] : [];
  });

const problems: string[] = [];
for (const file of [...sources(path.join(ROOT, 'assets')), ...sources(path.join(ROOT, 'shared'))]) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (line.trimStart().startsWith('//')) return;
    for (const [pattern, why] of RULES) {
      if (pattern.test(line)) problems.push(`${path.relative(ROOT, file)}:${i + 1}: ${why}`);
    }
    if (path.basename(file) !== 'color.ts' && /export const inkOn = \(hex: string\)/.test(line)) {
      problems.push(`${path.relative(ROOT, file)}:${i + 1}: inkOn(hex): import from shared/color.ts`);
    }
  });
}
for (const p of problems) console.error(p);
try {
  execFileSync(process.execPath, [path.join(ROOT, 'scripts', 'export.ts'), '--check'], {stdio: 'inherit'});
} catch {
  process.exit(1);
}
process.exit(problems.length ? 1 : 0);
