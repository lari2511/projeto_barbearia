import { chromium } from 'playwright';

const urls = [
  { url: 'http://127.0.0.1:8000/static/index.html', name: 'home' }
];

const viewports = [
  { width: 375, height: 812, name: 'iPhoneSE' },
  { width: 390, height: 844, name: 'iPhone12' }
];

(async () => {
  const browser = await chromium.launch();
  try {
    for (const vp of viewports) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, userAgent: `Mozilla/5.0 (Mobile; ${vp.name})` });
      const page = await context.newPage();
      for (const u of urls) {
        const target = u.url;
        console.log(`Loading ${target} at ${vp.width}x${vp.height}`);
        try {
          await page.goto(target, { waitUntil: 'networkidle', timeout: 15000 });
        } catch (e) {
          console.error('Erro ao carregar', target, e.message);
        }
        const path = `../screenshots/${u.name}-${vp.name}-${vp.width}x${vp.height}.png`;
        await page.screenshot({ path, fullPage: true });
        console.log('Saved', path);
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
