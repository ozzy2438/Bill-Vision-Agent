import { build } from 'esbuild';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
const result = await build({entryPoints:['src/main.tsx'],bundle:true,write:false,minify:true,format:'iife',target:['es2020'],define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
const css = await readFile('.build/styles.css','utf8');
const script = result.outputFiles[0].text.replace(/<\/script/gi,'<\\/script');
const output = new URL('../../assets/circular-slider/',import.meta.url);
await mkdir(output,{recursive:true});
await writeFile(new URL('index.html',output),`<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body><div id="root"></div><script>${script}</script></body></html>`);
console.log(`Bundled self-contained carousel (${Math.round((script.length+css.length)/1024)} KiB). No CDN or runtime build needed.`);
