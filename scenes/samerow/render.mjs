#!/usr/bin/env node
// Rasterise the scene's SVG frames in the parked lab Chrome (CDP 127.0.0.1:9222) — the same route
// as design/artapodcast/shot.mjs, ONE page for the whole run instead of one per frame. Never opens
// anything in the operator's browser.
//
//   node render.mjs measure   -> metrics.json  (getBBox of every string the film sets, from measure.svg)
//   node render.mjs frames    -> frames/NNNNN.png from svg/NNNNN.svg
//
// Fonts are embedded as data: URIs so the render does not depend on the network and the frame is
// set in exactly the faces the kit is set in (Montserrat 700, Inter 500/600).
import { chromium } from '/Users/arash/.artaquest-dev/tools/node_modules/playwright/index.mjs';
import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync, unlinkSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const FONTS = resolve(HERE, '..', 'teaser', 'fonts');
const mode = process.argv[2];
if (!['measure', 'frames'].includes(mode)) {
  console.error('usage: node render.mjs measure | frames');
  process.exit(2);
}

const face = (fam, wt, file) =>
  `@font-face{font-family:"${fam}";font-weight:${wt};src:url(data:font/ttf;base64,${readFileSync(resolve(FONTS, file)).toString('base64')}) format("truetype")}`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
${face('Montserrat', 700, 'Montserrat-700.ttf')}
${face('Inter', 500, 'Inter-500.ttf')}
${face('Inter', 600, 'Inter-600.ttf')}
html,body{margin:0;padding:0;background:#010C17;overflow:hidden}
#stage{width:1920px;height:1080px}
#stage svg{display:block}
</style></head><body><div id="stage"></div>
<div style="position:absolute;left:-9999px;top:0;font-family:Montserrat;font-weight:700">x</div>
<div style="position:absolute;left:-9999px;top:0;font-family:Inter;font-weight:500">x</div>
<div style="position:absolute;left:-9999px;top:0;font-family:Inter;font-weight:600">x</div>
</body></html>`;

const browser = await chromium.connectOverCDP(process.env.AQ_CDP || 'http://127.0.0.1:9222', { timeout: 8000 });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
try {
  await page.setContent(html, { waitUntil: 'load', timeout: 20000 });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([
    document.fonts.load('700 32px Montserrat'), document.fonts.load('500 28px Inter'), document.fonts.load('600 44px Inter'),
  ]));
  const loaded = await page.evaluate(() => [...document.fonts].map(f => `${f.family} ${f.weight} ${f.status}`));
  console.log('fonts:', loaded.join(' · '));
  if (!loaded.every(s => s.endsWith('loaded'))) throw new Error('a font did not load — the frame would set in a fallback');

  if (mode === 'measure') {
    const svg = readFileSync(resolve(HERE, 'measure.svg'), 'utf8');
    const m = await page.evaluate((svg) => {
      document.getElementById('stage').innerHTML = svg;
      const out = {};
      for (const t of document.querySelectorAll('text[id]')) {
        const b = t.getBBox();
        // relative to the text's own origin (x=100, y=300 in measure.svg)
        out[t.id] = { x: b.x - 100, y: b.y - 300, w: b.width, h: b.height };
      }
      return out;
    }, svg);
    writeFileSync(resolve(HERE, 'metrics.json'), JSON.stringify(m, null, 1) + '\n');
    console.log(`metrics.json: ${Object.keys(m).length} strings measured`);
  } else {
    const src = resolve(HERE, 'svg');
    const dst = resolve(HERE, 'frames');
    mkdirSync(dst, { recursive: true });
    for (const f of readdirSync(dst)) if (f.endsWith('.png')) unlinkSync(resolve(dst, f));
    const files = readdirSync(src).filter(f => f.endsWith('.svg')).sort();
    const t0 = Date.now();
    for (const f of files) {
      const svg = readFileSync(resolve(src, f), 'utf8');
      await page.evaluate((svg) => { document.getElementById('stage').innerHTML = svg; }, svg);
      await page.screenshot({ path: resolve(dst, f.replace('.svg', '.png')), clip: { x: 0, y: 0, width: 1920, height: 1080 }, type: 'png' });
    }
    console.log(`frames/: ${files.length} PNGs in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
} finally {
  await page.close();
  await ctx.close();
  await browser.close();
}
