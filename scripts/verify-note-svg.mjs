import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import { lookup } from '../node_modules/astro/dist/assets/utils/vendor/image-size/lookup.js';
const directory = path.resolve('public/notes-assets');
const repairReport = JSON.parse(await fs.readFile('notes-svg-repair-report.json', 'utf8').catch(() => '[]'));
const repairedNames = new Set(repairReport.map(row => row.file));
const results = [];
for (const name of (await fs.readdir(directory)).filter(name => name.endsWith('.svg'))) {
  try {
    const metadata = await sharp(path.join(directory, name)).metadata();
    if (!metadata.width || !metadata.height) throw new Error('SVG dimensions missing');
    const bytes = await fs.readFile(path.join(directory, name));
    const astroMetadata = lookup(bytes);
    if (!astroMetadata.width || !astroMetadata.height) throw new Error('Astro SVG dimensions missing');
    let pixelsUnchanged;
    let pixelComparisonSkipped;
    if (repairedNames.has(name)) {
      const original = path.resolve('../markdown_articles/assets', name);
      if (await fs.access(original).then(() => true).catch(() => false)) {
        const before = await sharp(original).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
        const after = await sharp(bytes).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
        pixelsUnchanged = before.info.width === after.info.width && before.info.height === after.info.height && before.data.equals(after.data);
        if (!pixelsUnchanged) throw new Error('Root style migration changed rendered pixels');
      } else pixelComparisonSkipped = 'original corpus unavailable';
    }
    results.push({ file: name, width: metadata.width, height: metadata.height, astroLookup: true, pixelsUnchanged, pixelComparisonSkipped, ok: true });
  } catch (error) {
    results.push({ file: name, ok: false, error: String(error) });
  }
}
await fs.writeFile('notes-svg-validation.json', JSON.stringify(results, null, 2));
console.log(JSON.stringify({ svg: results.length, failures: results.filter(row => !row.ok) }));
if (results.some(row => !row.ok)) process.exitCode = 1;
