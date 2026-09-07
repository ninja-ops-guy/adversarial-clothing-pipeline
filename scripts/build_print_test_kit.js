const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('@playwright/test');

const PRODUCTS = ['hoodie', 'hat', 'beanie', 'cargo', 'mask', 'shirt'];
const PRIMARY_BY_FAMILY = {
  signal_shadow: 'hat',
  machine_static: 'hoodie',
  ghost_hound: 'beanie',
  broken_human: 'cargo',
  error_garden: 'shirt'
};

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function pngDimensions(file) {
  const b = fs.readFileSync(file);
  if (b.length < 24 || b.toString('ascii', 1, 4) !== 'PNG') throw new Error(`${file} is not a PNG`);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

async function saveDownload(page, buttonName, destination) {
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: buttonName, exact: true }).click();
  const download = await downloadPromise;
  await download.saveAs(destination);
  if (!fs.existsSync(destination) || fs.statSync(destination).size < 1000) {
    throw new Error(`Export failed or empty: ${destination}`);
  }
}

async function applyCandidate(page, cfg, product) {
  await page.selectOption('#productType', product);
  await page.selectOption('#designFamily', cfg.family || cfg.patternType);
  await page.locator('#studioScale').fill(String(cfg.patternScale));
  await page.locator('#studioDensity').fill(String(cfg.colorVariance));
  await page.locator('#studioDistress').fill(String(cfg.edgeIntensity));
  await page.locator('#studioSeed').fill(String(cfg.seed));

  for (const motif of cfg.featureMotifs || []) {
    const card = page.locator(`.motif-card[data-motif="${motif}"]`);
    if (await card.count()) {
      const classes = await card.getAttribute('class');
      if (!String(classes).includes('selected')) await card.click();
    }
  }
  const preset = cfg.variationPreset || 'original';
  const variation = page.locator(`.variation-card[data-variation="${preset}"]`);
  if (await variation.count()) await variation.click();
  await page.evaluate(() => RACStudio.renderAll());
  await page.waitForFunction(
    ({ family, seed, product }) => {
      const c = document.getElementById('mockupCanvas');
      return c && c.dataset.renderFamily === family && c.dataset.renderSeed === String(seed) && c.dataset.renderProduct === product;
    },
    { family: cfg.family || cfg.patternType, seed: cfg.seed, product }
  );
}

async function main() {
  const configPath = path.resolve(process.argv[2] || 'benchmarks/runtime/candidate-config.json');
  const outputDir = path.resolve(process.argv[3] || 'print-test-kit');
  const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const family = cfg.family || cfg.patternType;
  if (!PRIMARY_BY_FAMILY[family]) throw new Error(`Unsupported Product Studio family: ${family}`);

  fs.rmSync(outputDir, { recursive: true, force: true });
  fs.mkdirSync(path.join(outputDir, 'mockups'), { recursive: true });
  fs.mkdirSync(path.join(outputDir, 'design'), { recursive: true });
  const baseURL = process.env.PATTERN_LAB_URL || 'http://127.0.0.1:4173';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 }, acceptDownloads: true });
  const primaryProduct = cfg.product || PRIMARY_BY_FAMILY[family];

  try {
    await page.goto(`${baseURL}/product-studio.html`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.RACStudio && document.querySelector('#studioStatus')?.textContent.includes('READY'));
    await applyCandidate(page, cfg, primaryProduct);

    const tilePath = path.join(outputDir, 'design', 'pattern_tile_4096.png');
    const primaryBoard = path.join(outputDir, 'design', `reference_board_${primaryProduct}_4096x5119.png`);
    const studioManifest = path.join(outputDir, 'design', 'product_studio_manifest.json');
    await saveDownload(page, 'Export 4096px POD Tile', tilePath);
    await saveDownload(page, 'Export Reference Board PNG', primaryBoard);
    await saveDownload(page, 'Export Production Manifest', studioManifest);

    const mockups = {};
    for (const product of PRODUCTS) {
      await applyCandidate(page, cfg, product);
      const out = path.join(outputDir, 'mockups', `${product}_4096x5119.png`);
      await saveDownload(page, 'Export Reference Board PNG', out);
      mockups[product] = {
        path: path.relative(outputDir, out).replaceAll('\\', '/'),
        sha256: sha256(out),
        dimensions: pngDimensions(out)
      };
    }

    const tileDims = pngDimensions(tilePath);
    const boardDims = pngDimensions(primaryBoard);
    if (tileDims[0] !== 4096 || tileDims[1] !== 4096) throw new Error(`Unexpected tile size: ${tileDims.join('x')}`);
    if (boardDims[0] !== 4096 || boardDims[1] !== 5119) throw new Error(`Unexpected board size: ${boardDims.join('x')}`);

    const verification = {
      schema_version: '1.0',
      candidate_id: cfg.candidate_id,
      source_candidate_id: cfg.source_candidate_id || null,
      family,
      primary_product: primaryProduct,
      design_profile: cfg.art_direction_profile || null,
      design_profile_sha256: cfg.design_profile_sha256 || null,
      pattern_tile: {
        path: 'design/pattern_tile_4096.png',
        sha256: sha256(tilePath),
        dimensions: tileDims
      },
      primary_reference_board: {
        path: path.relative(outputDir, primaryBoard).replaceAll('\\', '/'),
        sha256: sha256(primaryBoard),
        dimensions: boardDims
      },
      product_studio_manifest: {
        path: 'design/product_studio_manifest.json',
        sha256: sha256(studioManifest)
      },
      mockups,
      status: 'digital_print_assets_verified',
      physical_validation_performed: false
    };
    fs.writeFileSync(path.join(outputDir, 'export-verification.json'), JSON.stringify(verification, null, 2) + '\n');
    fs.copyFileSync(configPath, path.join(outputDir, 'design', 'candidate-config.json'));
    console.log(JSON.stringify(verification, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch(err => { console.error(err); process.exit(1); });
