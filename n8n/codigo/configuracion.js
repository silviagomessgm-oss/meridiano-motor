// EDITAR UNA VEZ tras importar: valores del despliegue que NO son secretos.
// Las claves privadas (GitHub, Claude, clave de servicio de Supabase, Gmail) van en credenciales de n8n, nunca aquí.
return [{ json: {
  github_repo: 'TU-USUARIO/meridiano-motor',                    // repositorio donde corre el motor (GitHub Actions)
  github_rama: 'main',
  supabase_url: 'https://xxxxxxxx.supabase.co',
  hoja_datos_id: 'ID-de-la-hoja-de-Google-Sheets',               // lo que va entre /d/ y /edit en la URL de la hoja
  panel_url: 'https://meridiano-panel.lovable.app',
  correo_direccion: 'direccion@meridiano.com',
  correo_datos: 'datos@meridiano.com',                           // responsable de la hoja de datos (avisos de la carga)
  correo_privacidad: 'privacidad@meridiano.example',             // aparece en el pie de los correos (derechos de protección de datos)
  baja_url: 'http://localhost:5678/webhook/meridiano-baja',      // URL de producción del webhook de W8 (enlace de baja de los correos)
  modelo_ia: 'claude-sonnet-5-5',
  // MODO DEMO (datos ficticios): todos los correos van al buzón de pruebas, con el destinatario real en el asunto.
  // Los correos salen de la cuenta de Gmail conectada en n8n; el buzón de pruebas puede ser esa misma cuenta (con alias +demo).
  modo_demo: true,
  buzon_demo: 'TU-CUENTA+demo@gmail.com',
} }];
