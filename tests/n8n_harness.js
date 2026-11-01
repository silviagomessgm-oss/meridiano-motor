// Ejecuta el código de un nodo Code de n8n con $input, $() y $env simulados. Uso: node n8n_harness.js archivo.js datos.json
const fs = require('fs');
const [, , archivo, datos] = process.argv;
const d = JSON.parse(fs.readFileSync(datos, 'utf8'));
const items = arr => (arr || []).map(json => ({ json }));
const $input = { all: () => items(d.input), first: () => items(d.input)[0] };
const $ = nombre => ({ all: () => items((d.nodos || {})[nombre]), first: () => items((d.nodos || {})[nombre])[0] });
const fn = new Function('$input', '$', '$env', fs.readFileSync(archivo, 'utf8'));
process.stdout.write(JSON.stringify(fn($input, $, d.env || {}).map(i => i.json)));
