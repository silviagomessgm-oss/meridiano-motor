// Solo si el motor falló o no respondió: aviso a dirección (no se publica ningún plan nuevo).
return $input.all().filter(i => !i.json.ok).map(i => ({ json: {
  error: i.json.error || (i.json.body && i.json.body.message) || 'No se ha podido lanzar el motor en GitHub',
  ejecucion_github: i.json.ejecucion_github || '',
} }));
