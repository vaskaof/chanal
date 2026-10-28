// Рендер HTML → PNG через Playwright.
// Вход: JSON-список заданий {file, w, h, html, transparent, frames?: {dir, fps, dur}}.
// Если задано frames — страница должна определить window.setT(t); пишется последовательность dir/%05d.png.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const FONTS = path.join(__dirname, 'node_modules/@fontsource');
const css = ['unbounded/700', 'unbounded/800', 'manrope/500', 'manrope/600', 'manrope/700', 'manrope/800']
  .map(f => `<link rel="stylesheet" href="file://${FONTS}/${f}.css">`).join('');
(async () => {
  const items = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage();
  const tmp = path.join(__dirname, 'out', '_tmp.html');
  fs.mkdirSync(path.dirname(tmp), { recursive: true });
  for (const it of items) {
    await p.setViewportSize({ width: it.w, height: it.h });
    fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8">${css}<style>
      *{margin:0;padding:0;box-sizing:border-box} html,body{width:${it.w}px;height:${it.h}px;overflow:hidden;
      background:${it.transparent ? 'transparent' : '#14202B'};font-family:'Manrope',sans-serif;color:#F6F4EF}
      .u{font-family:'Unbounded',sans-serif}</style></head><body>${it.html}</body></html>`);
    await p.goto('file://' + tmp);
    await p.evaluate(async () => { await document.fonts.load('700 40px Unbounded', 'Кнопка'); await document.fonts.load('700 40px Manrope', 'Кнопка'); await document.fonts.ready; });
    if (it.frames) {
      const { dir, fps, dur } = it.frames;
      fs.mkdirSync(dir, { recursive: true });
      const n = Math.round(dur * fps);
      for (let i = 0; i < n; i++) {
        await p.evaluate(t => window.setT(t), i / fps);
        await p.screenshot({ path: path.join(dir, String(i).padStart(5, '0') + '.png') });
      }
    } else {
      await p.screenshot({ path: it.file, omitBackground: !!it.transparent });
    }
  }
  await b.close();
})();
