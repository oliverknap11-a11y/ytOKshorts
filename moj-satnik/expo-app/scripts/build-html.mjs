// Zabalí webovú appku (../../index.html) do JS modulu assets/app-html.js,
// ktorý WebView načíta. Jediný zdroj pravdy ostáva moj-satnik/index.html.
// Spusti po každej zmene webovej appky:  npm run build:html
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, '..', '..', 'index.html');     // moj-satnik/index.html
const out = join(here, '..', 'assets', 'app-html.js'); // expo-app/assets/app-html.js

const html = readFileSync(src, 'utf8');
const banner =
  '// AUTO-GENEROVANÉ z moj-satnik/index.html – needituj ručne.\n' +
  '// Znovu vytvor cez: npm run build:html\n';
writeFileSync(out, banner + 'export default ' + JSON.stringify(html) + ';\n');

console.log('✔ assets/app-html.js vygenerované (' + html.length + ' znakov).');
