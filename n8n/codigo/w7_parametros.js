// EDITAR ANTES DE LANZAR: qué se audita y con qué modelo.
//  · tipo 'prueba'  → paquete corto con fallos puestos a propósito: comprueba que el flujo funciona. No es la auditoría.
//  · tipo 'diseno'  → paso 05 de FORGEN: especificaciones de los 9 nodos.
//  · tipo 'backlog' → paso 08 de FORGEN: backlog y solución desplegada (paquete pendiente de preparar).
// El modelo auditor debe ser DISTINTO y MÁS CAPAZ que el que generó el diseño (Claude Opus).
const tipo = 'prueba';
const modelo_auditor = 'claude-fable-5-1';

const ARCHIVOS = {
  prueba:  { paquete: 'auditoria/paquete_prueba.md',  rubrica: 'auditoria/rubrica_diseno.md' },
  diseno:  { paquete: 'auditoria/paquete_diseno.md',  rubrica: 'auditoria/rubrica_diseno.md' },
  backlog: { paquete: 'auditoria/paquete_backlog.md', rubrica: 'auditoria/rubrica_backlog.md' },
};
if (!ARCHIVOS[tipo]) throw new Error(`tipo «${tipo}» no válido: usa prueba, diseno o backlog`);
const cfg = $('Configuración').first().json;
return [{ json: { tipo, modelo: modelo_auditor, ...ARCHIVOS[tipo], repo: cfg.github_repo, rama: cfg.github_rama || 'main' } }];
