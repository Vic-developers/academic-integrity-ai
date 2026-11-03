# Integración con Moodle 5.0.2

## Verificación de fuentes

Se consultó el código oficial del tag v5.0.2. version.php declara 5.0.2 (Build: 20250811). mod/assign/db/services.php registra mod_assign_get_assignments, mod_assign_get_submissions y mod_assign_get_submission_status. lib/plagiarismlib.php expone plagiarism_get_links, plagiarism_print_disclosure y carga de plugins. Copias de investigación y URLs en docs/research/sources.json. Esta consulta verifica existencia de mecanismos, no acceso en una instalación ni contrato completo de respuestas.

## Diseño

Adaptador institucional con URL de Moodle aprobada y token de servicio de mínimo privilegio. Mapear curso, actividad, entrega, archivo y versión a IDs externos bajo tenant. Descargar archivos solo por rutas autorizadas con validación de destinos; no reutilizar token en redirecciones a otros hosts ni registrarlo en URLs de logs. Importación idempotente por instalación/entrega/hash y curso. Sincronización con outbox, checkpoint, retries y reconciliación de entregas modificadas. Respetar exclusiones y visibilidad del estudiante.

Servicios web estándar pueden proporcionar actividades/entregas dependiendo de permisos y configuración; los archivos deben resolverse desde las estructuras y permisos efectivamente devueltos. No asumir que un token puede acceder a todos los cursos ni que una API retorna texto extraído. Consultar contratos externos exactos y ejecutar pruebas en Fase 13.

## Plugin previsto

Evaluar plugin de tipo plagiarism para mostrar enlaces de resultados en la actividad, divulgación/consentimiento y eventos de entrega. Su clase base, callbacks y permisos se verificarán sobre Moodle 5.0.2 antes de implementar. Un servicio local personalizado puede ser necesario para operaciones que no expongan los web services estándar. No escribir notas automáticamente ni usar llamadas no documentadas. Enlace al informe exige sesión/permisos en Academic Integrity AI; no URL pública permanente.

## Puerta de aceptación

Instancia de prueba Moodle 5.0.2 con administrador autorizado, curso/tarea y cuentas docente/alumno. Probar entrega, importación, procesamiento, enlace al informe, acceso denegado a otro alumno, actualización, borrado/retención y recuperación tras caída. Registrar versiones PHP/BD requeridas según documentación oficial al aprovisionar Moodle. No hay plugin ni conectividad Moodle probados en Fase 0.
