// Lo que devuelve la acción de GitHub al terminar (o nada, si el tiempo de espera se agotó).
const b = ($input.first().json || {}).body;
if (!b || typeof b !== 'object') {
  return [{ json: { ok: false, error: 'El motor no ha respondido en 30 minutos (revisa la pestaña Actions del repositorio)' } }];
}
return [{ json: b }];
