// Генерирует логотипы «Неручной режим» в палитре карточек/презентации Кнопки
const fs = require('fs');
const path = require('path');
const opentype = require('opentype.js');
const { chromium } = require('playwright');

const OUT = path.resolve(process.argv[2]);
const C = { ink: '#14202B', ink3: '#2F4456', paper: '#F6F4EF', or: '#FF6B3D', or2: '#C2441E', mutd: '#C9D1D9' };

const font = opentype.parse(fs.readFileSync(require.resolve('@fontsource/unbounded/files/unbounded-cyrillic-800-normal.woff')).buffer);

// текст -> path, выравнивание: x слева, baseline y; возвращает {d, w}
function text(str, x, y, size, anchor = 'start') {
  const w = font.getAdvanceWidth(str, size);
  const x0 = anchor === 'middle' ? x - w / 2 : x;
  return { d: font.getPath(str, x0, y, size).toPathData(2), w };
}

// Тумблер «включён»: оранжевая дорожка, светлый бегунок справа, искры
function toggle({ x, y, w, h, track, knob, spark, glow }) {
  const r = h / 2, kr = r - h * 0.11, kx = x + w - r, ky = y + r;
  const s = h / 140; // масштаб искр
  const sp = [[-22, -112, -6, -146], [18, -96, 50, -120], [60, -74, 98, -84]]
    .map(([a, b, c, d]) => `<path d="M${kx + a * s} ${ky + b * s} L${kx + c * s} ${ky + d * s}"/>`).join('');
  return `${glow ? `<rect x="${x}" y="${y + h * 0.14}" width="${w}" height="${h}" rx="${r}" fill="${track}" opacity=".35" filter="url(#glow)"/>` : ''}
<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${track}"/>
<circle cx="${kx}" cy="${ky}" r="${kr}" fill="${knob}"/>
<g stroke="${spark}" stroke-width="${16 * s}" stroke-linecap="round">${sp}</g>`;
}
const glowDef = `<defs><filter id="glow" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="22"/></filter></defs>`;

const svgs = {
  // Основной аватар канала: тёмный, как обложка карточек
  'neruchnoy-dark': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">${glowDef}
<rect width="512" height="512" fill="${C.ink}"/>
${toggle({ x: 86, y: 196, w: 340, h: 136, track: C.or, knob: C.paper, spark: C.or, glow: true })}</svg>`,

  // Светлый вариант: «бумага» карточек, тёмный тумблер, оранжевый бегунок
  'neruchnoy-light': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" fill="${C.paper}"/>
${toggle({ x: 86, y: 196, w: 340, h: 136, track: C.ink, knob: C.or, spark: C.or })}</svg>`,

  // Аватар с надписью (как текущий), для крупных размеров: обложка, сторис
  'neruchnoy-dark-text': (() => {
    const a = text('Неручной', 256, 362, 60, 'middle'), b = text('режим', 256, 430, 60, 'middle');
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">${glowDef}
<rect width="512" height="512" fill="${C.ink}"/>
${toggle({ x: 146, y: 150, w: 220, h: 88, track: C.or, knob: C.paper, spark: C.or, glow: true })}
<path d="${a.d}" fill="${C.paper}"/><path d="${b.d}" fill="${C.or}"/></svg>`;
  })(),

  // Горизонтальный логотип для обложек/шапок
  'neruchnoy-wordmark': (() => {
    const a = text('Неручной', 430, 300, 118), b = text('режим', 430, 440, 118);
    const W = Math.ceil(430 + Math.max(a.w, b.w) + 110);
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} 640">${glowDef}
<rect width="${W}" height="640" fill="${C.ink}"/>
${toggle({ x: 100, y: 262, w: 260, h: 104, track: C.or, knob: C.paper, spark: C.or, glow: true })}
<path d="${a.d}" fill="${C.paper}"/><path d="${b.d}" fill="${C.or}"/></svg>`;
  })(),
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [name, svg] of Object.entries(svgs)) {
    fs.writeFileSync(path.join(OUT, name + '.svg'), svg);
    const [, vw, vh] = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
    const scale = name.includes('wordmark') ? 2 : 640 / vw;
    const w = Math.round(vw * scale), h = Math.round(vh * scale);
    await page.setViewportSize({ width: w, height: h });
    await page.setContent(`<style>*{margin:0}</style>${svg.replace('<svg ', `<svg width="${w}" height="${h}" `)}`);
    await page.screenshot({ path: path.join(OUT, name + '.png'), clip: { x: 0, y: 0, width: w, height: h } });
  }

  // Превью: как выглядит в списке чатов, светлая/тёмная тема
  const img = n => 'data:image/svg+xml;base64,' + Buffer.from(svgs[n]).toString('base64');
  const row = (n, bg, fg, sub) => `<div style="display:flex;align-items:center;gap:16px;background:${bg};padding:14px 18px;border-radius:14px">
<img src="${img(n)}" style="width:56px;height:56px;border-radius:50%"><div><div style="font:700 19px Manrope,sans-serif;color:${fg}">Неручной режим</div><div style="font:500 16px Manrope,sans-serif;color:${sub}">Скрин оплаты — ещё не оплата</div></div></div>`;
  const col = (n, label) => `<div style="display:flex;flex-direction:column;gap:14px;width:340px">
<img src="${img(n)}" style="width:300px;height:300px;border-radius:50%;align-self:center">
<div style="font:800 18px Manrope,sans-serif;text-align:center;color:${C.ink}">${label}</div>
${row(n, '#fff', C.ink, '#7A848F')}${row(n, '#17212B', '#fff', '#8A96A3')}
<div style="display:flex;gap:12px;align-items:center;justify-content:center">${[96, 48, 32].map(s => `<img src="${img(n)}" style="width:${s}px;height:${s}px;border-radius:50%">`).join('')}</div></div>`;
  const prev = `<html><head><style>@font-face{font-family:Manrope;src:url(file://${require.resolve('@fontsource/manrope/files/manrope-cyrillic-700-normal.woff2')})}*{margin:0}</style></head>
<body style="background:#ECE8E0;padding:40px;display:flex;flex-direction:column;gap:36px;width:max-content">
<div style="display:flex;gap:36px">${col('neruchnoy-dark', 'A. Основной — тёмный')}${col('neruchnoy-light', 'B. Светлый')}${col('neruchnoy-dark-text', 'C. С надписью')}</div>
<img src="${img('neruchnoy-wordmark')}" style="width:1092px;border-radius:24px"></body></html>`;
  const pf = path.join(OUT, '_preview.html');
  fs.writeFileSync(pf, prev);
  await page.setViewportSize({ width: 1200, height: 800 });
  await page.goto('file://' + pf);
  await page.screenshot({ path: path.join(OUT, 'preview-v2.png'), fullPage: true });
  fs.unlinkSync(pf);
  await browser.close();
})();
