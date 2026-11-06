# API forense y estilo

Prefijo `/api/v1/forensics`. Sesión e institución activa; acceso a todos los documentos involucrados. Escrituras requieren CSRF/origen. UUID inaccesible responde 404; estados/incongruencias 409; muestras insuficientes o incompatibles 422; presupuestos 413.

| Método y ruta | Resultado |
| --- | --- |
| GET `/documents/{id}` | Snapshot, metadatos, observaciones originales con hashes y límites; sin conclusión de conducta |
| GET `/documents/{id}/attestation` | Autorización e historial visibles según permiso documental, o revisión cero si no existe |
| POST `/documents/{id}/attestation` | Registra/revoca autorización, requiere evaluador y revisión esperada |
| POST `/style/compare` | Compara trabajo y dos a cinco muestras verificadas, autorizadas y comparables |

Autorización: `expected_revision`, `active`, `verified_writing_sample`, `authorization_reference`, `provenance_reference`, `language`, `domain`, `genre`, `sample_date` ISO y `reason`. Fecha no futura. Autor registrado del archivo no se usa como identidad. Referencias y motivo mínimos de diez caracteres, idioma mínimo dos y dominio/género tres. Se conserva actor, fecha y revisión; máximo veinte cambios y 64 KiB de historial.

Comparación: `document_id`, `source_document_ids` y `expected_revisions` con pares documento→revisión. Revalida acceso, estudiante activo, propiedad, autorización y comparabilidad bajo bloqueo documental ordenado. Fuentes anteriores requieren verified_writing_sample y fecha anterior. Devuelve valores/mediana/rango/diferencia, versiones/hashes y autorizaciones exactas usadas. No persiste resultados ni devuelve probabilidad de autoría. La ausencia de una autorización produce 409; un cambio concurrente también.

La exportación forense usa el mismo GET privado (JSON). Límites de alcance y extracción se documentan en [fase 9](PHASE_9.md). Probabilidades de autoría no se derivan de metadatos ni de diferencias de estilo; el corpus/modelo real continúa pendiente en [el registro de fuentes](../datasets/authorship-v1/README.md).
