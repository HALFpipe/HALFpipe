// Real Chromium, fabricated SVGs, and a narrow page fixture. Never opens manual pages.
import { readFileSync, readdirSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const { chromium } = createRequire(import.meta.url)('playwright');
const root = new URL('../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const bootstrapDir = new URL('_preview-layout/site_libs/bootstrap/', root);
const bootstrapCss = readdirSync(bootstrapDir).find(name => name.startsWith('bootstrap-') && name.endsWith('.min.css'));
let css = read(`_preview-layout/site_libs/bootstrap/${bootstrapCss}`) + '\n' +
  read('_preview-layout/site_libs/quarto-contrib/glightbox/glightbox.min.css') + '\n' +
  read('styles.css') + '\n' + read('qc/photo-viewer.css');
css = css.replace(/@import[^;]*;/g, ''); // Keep the fixture fully offline, using fallback fonts.
const svg = (width, height, label) => 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
  <rect width="100%" height="100%" fill="#326a9b"/>
  ${Array.from({length: 21}, (_, i) => `<rect x="${(i % 7) * width / 7 + 4}" y="${Math.floor(i / 7) * height / 3 + 4}" width="${width / 7 - 8}" height="${height / 3 - 8}" fill="${['#e6b85c','#78b6a1','#ae91c6'][Math.floor(i / 7)]}"/><text x="${(i % 7 + .5) * width / 7}" y="${(Math.floor(i / 7) + .5) * height / 3}" text-anchor="middle" font-size="24">${label} ${i + 1}</text>`).join('')}</svg>`);
const captions = ['Fabricated wide example: all seven columns should use the window width.',
  'A long fabricated caption, retained exactly. '.repeat(160)];
const figure = (src, caption) => `<div class="quarto-figure"><figure><p><a class="lightbox" href="${src}" data-gallery="synthetic"><img src="${src}" alt="Fabricated test image"></a></p><figcaption>${caption}</figcaption></figure></div>`;
const html = `<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body class="qc-manual"><main style="max-width:720px;margin:60px auto"><h1>Synthetic image type</h1><section><h2>Example of a good subject</h2><div class="qc-example-gallery">${figure(svg(1200,600,'Wide'),captions[0])}${figure(svg(400,1200,'Portrait'),captions[1])}</div></section></main></body></html>`;
const browser = await chromium.launch({ headless: true });
const output = process.env.QC_TEST_OUTPUT || '/tmp/qc-preview-browser';
mkdirSync(output, { recursive: true });
let scenarios = 0;
try {
  for (const [width,height] of [[1751,1280],[1440,900],[1024,768],[390,844],[320,568],[844,390]]) {
    const context = await browser.newContext({ viewport: {width,height} });
    await context.route('**/*', route => route.abort()); // No network or participant assets.
    const page = await context.newPage(); const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent(html);
    await page.addStyleTag({ content: css });
    await page.addScriptTag({ content: read('_preview-layout/site_libs/bootstrap/bootstrap.min.js') });
    await page.addScriptTag({ content: read('_preview-layout/site_libs/quarto-contrib/glightbox/glightbox.min.js') });
    await page.evaluate(() => { window.lightboxQuarto = GLightbox({selector:'.lightbox'}); });
    await page.addScriptTag({ content: read('qc/photo-viewer.js') });
    await page.addScriptTag({ content: read('qc/preview-zoom.js') });
    await page.evaluate(() => document.dispatchEvent(new Event('DOMContentLoaded')));
    const expectedContext = 'Synthetic image type · Example of a good subject';
    assert.equal(await page.locator('.qc-photo-context').textContent(), expectedContext);
    await page.locator('.qc-photo-viewer .carousel-item.active a.lightbox').click();
    assert.equal(await page.locator('.qc-image-context').textContent(), expectedContext);
    await page.waitForFunction(() => {
      const image = document.querySelector('.qc-image-workspace img');
      return document.querySelector('dialog').open && !image.hidden && image.naturalWidth > 0;
    });
    await page.waitForTimeout(80); // Deliver ResizeObserver before gesture assertions.
    const geometry = () => page.evaluate(() => {
      const box = selector => {
        const r = document.querySelector(selector).getBoundingClientRect();
        return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};
      };
      return { dialog:box('dialog'),header:box('.qc-image-toolbar'),stage:box('.qc-image-workspace'),
        caption:box('.qc-image-caption'),image:box('.qc-image-workspace img') };
    });
    let g = await geometry();
    assert.equal(g.dialog.x,0); assert.equal(g.dialog.y,0);
    assert.equal(g.dialog.width,width); assert.equal(g.dialog.height,height);
    assert.equal(g.stage.x,0); assert.equal(g.stage.width,width);
    assert.ok(g.header.bottom <= g.stage.y + 1);
    assert.ok(g.stage.bottom <= g.caption.y + 1); assert.ok(g.caption.bottom <= height + 1);
    assert.equal(await page.locator('.glightbox-container').count(),0);
    assert.equal(await page.locator('.qc-image-caption').textContent(),captions[0]);
    if(width===1751 || width===390) await page.screenshot({path:`${output}/${width===1751?'desktop':'phone'}-fit.png`});
    const state = () => page.locator('.qc-image-workspace img').evaluate(image => {
      const m = new DOMMatrix(getComputedStyle(image).transform);
      return {scale:m.a,x:m.e,y:m.f,width:parseFloat(image.style.width),height:parseFloat(image.style.height)};
    });
    const cx = g.stage.width/2, cy = g.stage.y + g.stage.height/2;
    const dx = width >= 1000 ? 80 : 0;
    await page.locator('.qc-image-workspace').evaluate(el => el.addEventListener('wheel',event=>{
      window.fixtureWheelX=event.clientX;
    }));
    await page.mouse.move(cx + dx,cy); await page.mouse.wheel(0,-300);
    await page.waitForFunction(() => document.querySelector('.qc-image-zoom [role=status]').textContent !== '100%');
    let s = await state(); assert.ok(s.scale > 1);
    if (dx) {
      const point=await page.evaluate(()=>window.fixtureWheelX)-cx;
      assert.ok(Math.abs((point-s.x)/s.scale-point)<.1);
    }
    for (let i=0;i<6;i++) await page.locator('dialog').getByRole('button',{name:'Zoom in',exact:true}).click();
    g = await geometry(); assert.ok(g.image.width > width);
    const edgeHits = await page.evaluate(cy => [2,innerWidth-2].map(x =>
      document.elementFromPoint(x,cy) === document.querySelector('.qc-image-workspace img')),cy);
    assert.deepEqual(edgeHits,[true,true]); // No invisible fitted-frame side walls.
    assert.ok(g.header.bottom <= g.stage.y + 1); assert.ok(g.stage.bottom <= g.caption.y + 1);
    if (width===1751) await page.screenshot({path:`${output}/desktop-zoomed.png`});
    await page.locator('dialog').getByRole('button',{name:'Fit image to window'}).click();
    s=await state();assert.equal(s.scale,1);assert.equal(s.x,0);assert.equal(s.y,0);
    for(let i=0;i<3;i++) await page.locator('dialog').getByRole('button',{name:'Zoom in',exact:true}).click();
    await page.mouse.move(cx,cy);await page.mouse.down();await page.mouse.move(cx+60,cy+30,{steps:4});await page.mouse.up();
    s=await state();assert.ok(s.x>0);assert.ok(s.y>0);
    assert.ok(Math.abs(s.x)<=Math.abs(s.width*s.scale-width)/2+1);
    await page.locator('dialog').getByRole('button',{name:'Fit image to window'}).click();
    await page.locator('.qc-image-workspace').focus();await page.keyboard.press('+');
    assert.ok((await state()).scale>1);await page.keyboard.press('0');assert.equal((await state()).scale,1);
    await page.locator('dialog').getByRole('button',{name:'Next example'}).click();
    await page.waitForFunction(() => !document.querySelector('.qc-image-workspace img').hidden);
    assert.equal(await page.locator('.qc-image-caption').textContent(),captions[1]);
    assert.equal(await page.locator('.qc-image-context').textContent(),expectedContext);
    assert.ok(await page.locator('.qc-image-context').evaluate(el => el.getBoundingClientRect().top >= 0));
    assert.equal((await state()).scale,1);
    g=await geometry();assert.equal(g.stage.width,width);assert.ok(g.stage.bottom<=g.caption.y+1);
    assert.ok(g.caption.height<=height*.3+1);
    assert.ok(await page.locator('.qc-image-caption').evaluate(el=>el.scrollHeight>el.clientHeight));
    assert.equal(await page.locator('dialog').getByRole('button',{name:'Next example'}).isDisabled(),true);
    if(width===390) await page.screenshot({path:`${output}/phone-long-caption.png`});
    await page.locator('dialog').getByRole('button',{name:'Previous example'}).click();
    await page.waitForFunction(() => !document.querySelector('.qc-image-workspace img').hidden);
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>!document.querySelector('dialog').open &&
      !document.body.classList.contains('qc-image-preview-open') && document.activeElement.matches('a.lightbox'));
    assert.equal(await page.evaluate(()=>document.activeElement.matches('a.lightbox')),true);
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('qc-image-preview-open')),false);
    assert.deepEqual(errors,[]);
    await context.close();scenarios++;
  }
  console.log(`PASS: ${scenarios} Chromium viewport scenarios; full-window edges, no native lightbox, caption/control separation, wheel anchoring, drag, keyboard, navigation, focus return, and long captions. Screenshots: ${output}`);
} finally { await browser.close(); }
