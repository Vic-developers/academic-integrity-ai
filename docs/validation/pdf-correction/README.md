# Corrección del PDF — Rotación y recorte

Se invierte la transformación de pdfminer para recuperar coordenadas PDF originales y se aplica el viewport real de PDF.js. La conversión incluye CropBox, origen de MediaBox, rotación y UserUnit; no requiere modificar ni volver a extraer versiones existentes.

La prueba de navegador usa PDFs válidos generados con 0°, 90°, 180° y 270°, con/sin CropBox; los recortados tienen MediaBox desplazado y uno utiliza UserUnit=2. Comprueba píxeles oscuros dentro de más del 85 % de cajas de caracteres antes/después del zoom. Geometría incoherente y texto alterado siguen provocando abstención.

El [manifiesto de cierre](checks.json) registra el resultado real, imágenes y coincidencia de activos servidos con compilación local. Se conserva la cobertura de las 8 pruebas de fase 4 y se añade la matriz geométrica. No hay cambios de dependencias ni backend de producción; sus 74 pruebas y auditorías corresponden al [cierre anterior](../phase4/checks.json).

La corrección no añade OCR ni inventa coordenadas cuando la extracción de caracteres no es fiable. Documentos complejos mantienen sus advertencias de extracción.
