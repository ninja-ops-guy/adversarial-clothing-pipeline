const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('@playwright/test');

function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

async function main() {
  const outputDir = path.resolve(process.argv[2] || 'benchmarks/runtime/pool');
  const profilePath = path.resolve(process.argv[3] || 'design_profiles/ruthless_reference_v1.json');
  const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
  fs.mkdirSync(outputDir, { recursive: true });
  const baseURL = process.env.PATTERN_LAB_URL || 'http://127.0.0.1:4173';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const records = [];

  try {
    await page.goto(`${baseURL}/product-studio.html`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.RACStudio && document.querySelector('#studioStatus')?.textContent.includes('READY'));
    const families = Object.keys(profile.families);
    for (const family of families) {
      if (!(await page.evaluate(name => typeof patternGenerators[name] === 'function', family))) {
        throw new Error(`Pattern family unavailable: ${family}`);
      }
    }

    let idx = 0;
    for (const family of families) {
      const familyConfig = profile.families[family];
      for (const variant of familyConfig.variants) {
        for (const seed of profile.seeds) {
          idx += 1;
          const candidateId = `RAC-PROD-V3-${String(idx).padStart(3, '0')}`;
          const config = {
            candidate_id: candidateId,
            patternType: family,
            family,
            product: familyConfig.primary_product,
            seed,
            patternScale: variant.scale,
            colorVariance: variant.density,
            edgeIntensity: variant.distress,
            symmetry: 0,
            colorPalette: family === 'error_garden' ? 'error_garden' : 'rac_reference',
            variationPreset: variant.variation,
            featureMotifs: familyConfig.motifs,
            design_variant: variant.name,
            art_direction_profile: profile.profile_id,
            generation_mode: 'reference'
          };

          const rendered = await page.evaluate(cfg => {
            const clamp8 = v => Math.max(0, Math.min(255, Math.round(v)));
            const c = document.createElement('canvas');
            c.width = c.height = 512;
            const ctx = c.getContext('2d', { willReadFrequently: true });
            const effectiveScale = cfg.variationPreset === 'scale_plus' ? Math.min(100, cfg.patternScale + 24) : cfg.patternScale;
            const params = {
              patternType: cfg.family,
              patternScale: effectiveScale,
              colorVariance: cfg.colorVariance,
              edgeIntensity: cfg.edgeIntensity,
              symmetry: 0,
              seed: cfg.seed,
              featureMotifs: cfg.featureMotifs
            };
            let spec = null;
            if (window.RACPatternComposition && window.RACStyleProfiles) {
              spec = RACPatternComposition.buildStyleSpec(
                cfg.family,
                params,
                cfg.seed,
                cfg.product,
                'reference'
              );
              RACPatternComposition.renderFamilyFromSpec(ctx, 512, spec);
            } else {
              const palette = colorPalettes[cfg.family === 'error_garden' ? 'error_garden' : 'rac_reference'];
              patternGenerators[cfg.family](ctx, 512, params, palette, seededRandom(cfg.seed));
            }

            if (!['original', 'scale_plus'].includes(cfg.variationPreset)) {
              const image = ctx.getImageData(0, 0, 512, 512);
              const d = image.data;
              for (let i = 0; i < d.length; i += 4) {
                let r = d[i], g = d[i + 1], b = d[i + 2];
                if (cfg.variationPreset === 'high_contrast') {
                  const avg = (r + g + b) / 3;
                  r = clamp8((r - 128) * 1.7 + 128 + (r - avg) * .14);
                  g = clamp8((g - 128) * 1.7 + 128 + (g - avg) * .14);
                  b = clamp8((b - 128) * 1.7 + 128 + (b - avg) * .14);
                } else if (cfg.variationPreset === 'desaturated') {
                  const y = .2126 * r + .7152 * g + .0722 * b;
                  const v = clamp8((y - 128) * 1.18 + 128);
                  r = v; g = v; b = v;
                } else if (cfg.variationPreset === 'alt_palette') {
                  const nr = clamp8((b - 128) * 1.12 + 128);
                  const ng = clamp8((r - 128) * 1.08 + 128);
                  const nb = clamp8((g - 128) * 1.15 + 128);
                  r = nr; g = ng; b = nb;
                }
                d[i] = r; d[i + 1] = g; d[i + 2] = b;
              }
              ctx.putImageData(image, 0, 0);
            }

            const image = ctx.getImageData(0, 0, 512, 512).data;
            let dark = 0, accent = 0, edge = 0, edgeN = 0, entropyBins = new Array(16).fill(0);
            const lum = new Float32Array(512 * 512);
            for (let i = 0, p = 0; i < image.length; i += 4, p += 1) {
              const r = image[i], g = image[i + 1], b = image[i + 2];
              const y = .2126 * r + .7152 * g + .0722 * b;
              const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
              const sat = mx ? (mx - mn) / mx : 0;
              lum[p] = y;
              if (y < 68) dark += 1;
              if (sat > .42 && y > 45) accent += 1;
              entropyBins[Math.min(15, Math.floor(y / 16))] += 1;
            }
            for (let y = 1; y < 512; y += 1) for (let x = 1; x < 512; x += 1) {
              const p = y * 512 + x;
              edge += Math.abs(lum[p] - lum[p - 1]) + Math.abs(lum[p] - lum[p - 512]);
              edgeN += 2;
            }
            const n = 512 * 512;
            let entropy = 0;
            for (const count of entropyBins) {
              if (!count) continue;
              const p = count / n;
              entropy -= p * Math.log2(p);
            }
            const darkFraction = dark / n;
            const accentFraction = accent / n;
            const edgeDensity = Math.min(1, (edge / Math.max(1, edgeN)) / 96);
            const entropyNorm = entropy / 4;
            const printabilityProxy = Math.max(0, Math.min(1,
              .55 + .25 * entropyNorm - .35 * Math.max(0, edgeDensity - .72) - .25 * Math.max(0, accentFraction - .55)
            ));
            const artDirectionProxy = Math.max(0, Math.min(1,
              1 - (Math.abs(darkFraction - .55) * .55 + Math.abs(accentFraction - .18) * .7 + Math.abs(edgeDensity - .42) * .45)
            ));
            let referenceFidelity = null;
            if (spec && window.RACReferenceScorer) {
              const analysis = RACPatternComposition.analyzeComposition(ctx, 512, spec);
              referenceFidelity = RACReferenceScorer.score({
                family: cfg.family,
                product: cfg.product,
                analysis,
                spec,
                mode: 'reference'
              });
            }
            return {
              dataUrl: c.toDataURL('image/png'),
              reference_fidelity: referenceFidelity,
              visual_profile: {
                dark_fraction: darkFraction,
                accent_fraction: accentFraction,
                edge_density: edgeDensity,
                luminance_entropy: entropyNorm
              },
              printability_proxy: printabilityProxy,
              art_direction_proxy: artDirectionProxy
            };
          }, config);

          const png = Buffer.from(rendered.dataUrl.split(',')[1], 'base64');
          const pngName = `${candidateId}.png`;
          fs.writeFileSync(path.join(outputDir, pngName), png);
          records.push({
            ...config,
            png: pngName,
            png_sha256: crypto.createHash('sha256').update(png).digest('hex'),
            visual_profile: rendered.visual_profile,
            printability_proxy: rendered.printability_proxy,
            art_direction_proxy: rendered.art_direction_proxy,
            reference_fidelity_score: rendered.reference_fidelity ? rendered.reference_fidelity.score : null,
            reference_fidelity_subscores: rendered.reference_fidelity ? rendered.reference_fidelity.subscores : null,
            reference_profile: family,
            product_target: familyConfig.primary_product
          });
        }
      }
    }

    if (records.length !== profile.candidate_count) {
      throw new Error(`Preregistered pool expected ${profile.candidate_count} candidates, got ${records.length}`);
    }

    const pool = {
      schema_version: '3.0',
      generation_policy: 'Product-Studio-only preregistered candidate pool; surrogate-only selection; no held-out feedback.',
      design_profile: profile.profile_id,
      design_profile_sha256: sha256File(profilePath),
      candidate_count: records.length,
      selection_order: profile.selection_order,
      creative_ranking: 'reference_fidelity',
      reference_fidelity_scorer: 'reference-fidelity-v1',
      heldout_feedback_allowed: false,
      candidates: records
    };
    fs.writeFileSync(path.join(outputDir, 'pool.json'), JSON.stringify(pool, null, 2));
    console.log(`Exported ${records.length} product candidates to ${outputDir}`);
  } finally {
    await browser.close();
  }
}

main().catch(err => { console.error(err); process.exit(1); });
