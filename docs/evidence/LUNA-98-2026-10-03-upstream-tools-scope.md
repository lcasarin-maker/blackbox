# Reparación propuesta del alcance upstream

Se preparó un diff mínimo contra el fuente del runtime fijado 8.9.6, SHA256 b556a108901d051bf05cb940f350f741f4dcf412a37ce2dc10814a6aea38fe2d. Reutiliza el barrido existente e incorpora tools; no modifica el ZIP ni la configuración generada.

El repo upstream local está disponible pero contiene cambios sin comitear en el auditor, sus tests y muchos otros archivos. Esos cambios conservan su dueño; esta pasada de BB los leyó y preparó el parche por separado. Integrar la corrección requiere revisar el delta upstream, pasar sus controles positivos/negativos para tools y generar un artefacto con su productor nativo. El parche por sí solo deja DEBT-JUDGE-THREAT-SWEEP-TOOLS-01 abierta.

El control exigido en BB debe comprobar que el runtime publicado lee tools y detecta un homoglyph/invisible inyectado, además del caso sano. También queda por distinguir explícitamente el caso sin archivos examinados de un sujeto juzgado; añadir una ruta no resuelve ese requisito general.
