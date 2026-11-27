// Pädagogen-Wiki: zeichnet die Bilder eines Posts aus posts/<id>/spec.json.
// Aufruf: node tools/render.js posts/<id>
// Ergebnis: slide-01.jpg ... (Karussell/Bild) oder scene-1.png ... (Reel, wird danach zu video.mp4)
// Schrift: Outfit (SIL Open Font License), liegt als tools/outfit.woff2 bei.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const dir = process.argv[2];
const spec = JSON.parse(fs.readFileSync(path.join(dir, 'spec.json'), 'utf8'));
const font = fs.readFileSync(path.join(__dirname, 'outfit.woff2')).toString('base64');
const C = { cream: '#FBF7EF', navy: '#1B2550', muted: '#5A6282', orange: '#F6A620', green: '#72B52B', blue: '#00A3C4', pink: '#C94B8F', red: '#D81F4C' };
const P = [C.orange, C.green, C.blue, C.pink, C.red];
const acc = spec.accent || C.orange;
const css = `@font-face{font-family:O;src:url(data:font/woff2;base64,${font}) format('woff2');font-weight:100 900}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:O;color:${C.navy};background:${C.cream};overflow:hidden}
.frame{position:relative;overflow:hidden;background:${C.cream}}
.stripe{position:absolute;left:0;right:0;top:0;height:14px;display:flex}.stripe div{flex:1}
.dots{display:inline-flex;gap:8px;vertical-align:middle}.dots span{width:14px;height:14px;border-radius:50%;display:inline-block}
.pill{display:inline-block;padding:12px 26px;border-radius:999px;font-size:30px;font-weight:500}
small{display:inline-block;margin-top:28px;font-size:36px;color:${C.muted}}`;
const stripe = `<div class="stripe">${P.map(c => `<div style="background:${c}"></div>`).join('')}</div>`;
const dots = `<span class="dots">${P.map(c => `<span style="background:${c}"></span>`).join('')}</span>`;
const blob = (w) => `<div style="position:absolute;width:${w * 0.75}px;height:${w * 0.75}px;border-radius:50%;background:${acc};opacity:.12;right:${-w * 0.3}px;top:${-w * 0.25}px"></div>
<div style="position:absolute;width:${w * 0.45}px;height:${w * 0.45}px;border-radius:50%;border:10px solid ${acc};opacity:.18;left:${-w * 0.18}px;bottom:${-w * 0.15}px"></div>`;
const head = `<div style="position:absolute;left:80px;top:62px;font-size:34px;font-weight:500;display:flex;align-items:center;gap:16px">${dots}Pädagogen-Wiki</div>`;
const foot = (i, n) => `<div style="position:absolute;left:80px;right:80px;bottom:56px;display:flex;justify-content:space-between;font-size:34px;color:${C.muted}"><span>@paedagogen.wiki</span><span>${n ? `${i} / ${n}` : ''}</span></div>`;

function carousel(d) {
  const n = d.items.length + 2, W = 1080, H = 1350, out = [];
  out.push(`<div class="frame" style="width:${W}px;height:${H}px">${blob(W)}${stripe}${head}
   <div style="position:absolute;left:80px;right:80px;top:300px">
   <span class="pill" style="background:${C.navy};color:#fff">${d.series}</span> <span class="pill" style="background:${acc}22;border:2px solid ${acc};margin-left:10px">${d.topic}</span>
   <div style="font-size:${d.title.length > 34 ? 100 : 120}px;line-height:1.02;letter-spacing:-3px;margin-top:50px">${d.title}</div>
   <div style="display:inline-block;margin-top:44px;background:${acc};font-size:44px;font-weight:600;padding:16px 30px;border-radius:18px">${d.badge}</div>
   <div style="font-size:42px;color:${C.muted};margin-top:36px;line-height:1.3">${d.sub || ''}</div></div>
   <div style="position:absolute;right:80px;bottom:130px;font-size:38px;font-weight:600">Wischen →</div>${foot(1, n)}</div>`);
  d.items.forEach((it, k) => out.push(`<div class="frame" style="width:${W}px;height:${H}px">${blob(W)}${stripe}${head}
   <div style="position:absolute;left:80px;right:80px;top:270px">
   <div style="width:130px;height:130px;border-radius:50%;background:${acc};font-size:72px;font-weight:500;display:flex;align-items:center;justify-content:center">${k + 1}</div>
   <div style="font-size:78px;line-height:1.08;margin-top:56px;letter-spacing:-1px;font-weight:500">${it[0]}</div>
   <div style="font-size:48px;line-height:1.4;margin-top:40px">${it[1]}</div></div>${foot(k + 2, n)}</div>`));
  out.push(`<div class="frame" style="width:${W}px;height:${H}px;background:${C.navy};color:${C.cream}">${stripe}
   <div style="position:absolute;left:80px;right:80px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center">
   <div style="font-size:84px;line-height:1.1;letter-spacing:-1px">${d.cta}</div>
   <div style="font-size:40px;margin-top:44px;opacity:.85;line-height:1.4">Speicher dir den Beitrag. ${d.share || ''}</div>
   <div style="font-size:40px;margin-top:70px;display:flex;align-items:center;gap:18px">${dots}<span>Folge dem Pädagogen-Wiki</span></div></div></div>`);
  return out;
}

function question(d) {
  return [`<div class="frame" style="width:1080px;height:1350px">${blob(1080)}${stripe}${head}
   <div style="position:absolute;left:80px;right:80px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center">
   <span class="pill" style="align-self:flex-start;background:${acc}22;border:2px solid ${acc}">${d.kicker}</span>
   <div style="font-size:${d.title.length > 50 ? 88 : 104}px;line-height:1.05;letter-spacing:-2px;margin-top:44px">${d.title}</div>
   <div style="font-size:42px;color:${C.muted};margin-top:44px;line-height:1.3">${d.sub || ''}</div></div>${foot(0, 0)}</div>`];
}

// Reel: Szene 1 ist der Haken (große Frage, sofort lesbar), danach kurze Szenen.
function reel(d) {
  const W = 1080, H = 1920;
  return d.scenes.map((s, k) => {
    const hook = k === 0;
    return `<div class="frame" style="width:${W}px;height:${H}px">${blob(W)}${stripe}
    <div style="position:absolute;left:0;right:0;top:120px;text-align:center;font-size:36px;font-weight:500;display:flex;justify-content:center;align-items:center;gap:16px">${dots}Pädagogen-Wiki</div>
    <div style="position:absolute;left:0;right:0;top:200px;text-align:center"><span class="pill" style="background:${C.navy};color:#fff;font-size:36px">${d.series}</span></div>
    <div style="position:absolute;left:90px;right:90px;top:${hook ? 440 : 520}px;height:${hook ? 760 : 560}px;display:flex;align-items:center;justify-content:center;text-align:center">
      <div style="font-size:${hook ? (s[0].length > 30 ? 104 : 124) : (s[0].length > 16 ? 104 : 132)}px;line-height:1.08;letter-spacing:-2px;${hook ? 'font-weight:500' : ''}">${s[0]}</div></div>
    ${s[1] ? `<div style="position:absolute;left:90px;right:90px;bottom:520px;display:flex;justify-content:center">
      <div style="background:${hook ? acc : C.navy};color:${hook ? C.navy : '#fff'};font-size:54px;line-height:1.3;font-weight:600;padding:32px 44px;border-radius:24px;text-align:center;max-width:900px">${s[1]}</div></div>` : ''}
    </div>`;
  });
}

(async () => {
  const b = await chromium.launch();
  const shot = async (html, w, h, file, type) => {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.setContent(`<html><head><style>${css}</style></head><body>${html}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: path.join(dir, file), type, ...(type === 'jpeg' ? { quality: 92 } : {}) });
    await p.close();
  };
  if (spec.type === 'reel') {
    const s = reel(spec.design);
    for (let i = 0; i < s.length; i++) await shot(s[i], 1080, 1920, `scene-${i + 1}.png`, 'png');
    await shot(s[0], 1080, 1920, 'cover.jpg', 'jpeg');
  } else {
    const s = spec.design.kind === 'question' ? question(spec.design) : carousel(spec.design);
    for (let i = 0; i < s.length; i++) await shot(s[i], 1080, 1350, `slide-${String(i + 1).padStart(2, '0')}.jpg`, 'jpeg');
  }
  await b.close();
})();
