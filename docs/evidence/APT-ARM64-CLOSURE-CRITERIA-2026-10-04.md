# Criterios pendientes del cierre APT arm64

Esta matriz conserva el alcance de DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01. Separa componentes comprobados del cierre integral pendiente; los resultados parciales no cierran la ficha.

| Requisito | Evidencia actual | Trabajo pendiente del selector original |
|---|---|---|
| Sujeto y versiones exactas | native-subject-stack.json: GIGABYTE AI TOP ATOM B.1, BIOS 5.36_0ACUM08, kernel 6.17.0-1032-nvidia, arm64, apt2.8.3, gpgv2.4.4-2ubuntu17.6 | Ligar la captura de cada ensayo a su sujeto/stack; la captura actual no autentica retrospectivamente recibos anteriores ni reproduce otro OEM. |
| Perfil aprobado | Inventario de19 endpoints | Registrar respuesta humana concreta; comparar URI/suite/arquitectura/componentes/Signed-By con perfil aprobado. El inventario no es autorización. |
| Cobertura de fuentes configuradas |25 URI/suites con manifests observados,0 faltantes en ese alcance | Componentes/arquitecturas, deb-src y overrides de APT aún sin cerrar. |
| Firma con clave específica | Componente nativo gpgv:25 firmas verificadas,0 fail,0 CNR, home aislado | Comparar signer permitido con perfil autorizado; conservar binding por source y bytes actuales. |
| Integridad de todos los índices efectivos |137 hashes/tamaños verificados:40 Packages y97 índices de otros tipos | Comparar cobertura con targets configurados esperados, no sólo targets presentes. |
| Vigencia |1 comprobación temporal resuelta,24 CNR sin política de Date/Valid-Until | Resolver política humana por fuente; comprobarla sobre manifests autenticados y tiempo fijado. |
| Actualización fresca antes de upgrade | Ubuntu ports sano aislado y repo file de ensayo actualizaron listas nuevas | Actualización fresca del perfil completo aprobado, con ausencia de reutilización de listas obsoletas. |
| Negativo de source incompatible | APT real: binary-arm64 en archive.ubuntu.com,404/rc100 y targets vacíos | Integrar receipt, source bytes y scope al selector; no basta buscar un marcador suelto. |
| Negativos de integridad | APT real rechaza Packages alterado y Release con BADSIG; targets vacíos | Integrar baseline y negativos con hashes de sus inputs, tiempos y lista aislada nueva por fase. |
| Seguridad del ensayo | Componente rechaza hooks, rutas del host, repos inseguros, arquitectura incorrecta y comandos install | Verificar también los source/config bytes y su correspondencia con el dump capturado. |
| Rollback/cleanup | Collectors preservan limpieza de sus directorios propios, sin install ni cambios de trust/fuentes del host | Incorporar las pruebas de estado antes/después; permiso general de desarrollo no autoriza intervenciones invasivas. |
| Selector original | Componentes disponibles;101 tests focales pasan,100% de ramas | Implementar test_delta_forum_apt_arm64_source_validation_01 con todos los gates; faltantes deben emitir CNR y conservar open. |

Los componentes se reutilizan desde tools/apt_sources.py: parse_deb822, compare_index_identities, verify_release_signature, parse_release_digests, check_release_index, check_release_freshness y check_isolated_update_control. Ninguno concede autorización humana. El selector debe ejecutar los checks y mostrar resultados por requisito; la ausencia de perfil o política no debe esconder las observaciones que sí pudo realizar.

Boletas de perfil y vigencia ya abiertas, sin respuesta registrada. No se asume autorización y no se crean umbrales nuevos para conseguir PASS.

Captura nativa adicional: `effective-index-target-configuration.json` conserva 83 líneas seleccionadas de `apt-config dump`, rc0 y could_not_run=0, más SHA256 de la salida completa. Observa arm64 como única arquitectura global, rutas convencionales de sources y los templates Packages/Sources; Packages y Sources declaran Optional=0. Los targets de iconos grandes declaran DefaultEnabled=false. Estos valores deben alimentar la derivación de índices esperados junto con cada stanza y sus overrides; todavía no prueban que el conjunto observado sea completo. No se cambió la configuración del host.

Contraste Ubuntu por componente: el collector conservado `ubuntu-component-coverage-collector.txt` deriva16 combinaciones suite/componente arm64 de ubuntu.sources; observa15 y marca1 ausencia estructural (noble-backports/restricted). El resultado bruto conserva fail=1 del comparador de presencia; no demuestra corrupción. `ubuntu-component-empty-index-interpretation.json` verifica de nuevo la firma nativa del manifiesto archivado, su SHA y el METAKEY ausente: declara SHA256 de bytes vacíos y tamaño0. Resultado de esa interpretación: firma pass, authenticated_empty_index=true, fail=0, could_not_run=0. El selector compuesto debe distinguir ausencia de índice no vacío de ausencia de índice autenticado vacío; convertir toda ausencia en fallo sería un defecto del instrumento. Otros repos/arquitecturas/targets y vigencia siguen pendientes.

El componente reutilizable check_index_coverage compara paths esperados/observados y exige hash de contenido vacío más tamaño0 para aceptar un índice ausente como vacío. No autentica el manifiesto ni deriva los targets. Regresión baseline/negativos:102 tests,389 sentencias y166 ramas,0 missing/partial,100%; Ruff limpio y Pyright0/0/0. Replay sobre los4 manifests Ubuntu archivados:4 pass,0 fail,0 could_not_run. Recibos empty-index-coverage-unit-validation.json y ubuntu-component-coverage-recomputed.json. La ficha conserva open.

## Binding externo del selector original

El selector pytest conserva su comando literal y obtiene el digest de decisión mediante `BB_APT_APPROVED_DECISION_SHA256`. Debe fijarlo quien tenga la decisión humana registrada, con el SHA-256 exacto del archivo aprobado. Sin esa variable, la aprobación sigue pendiente; el selector no acepta un digest declarado dentro del bundle como autorización. La CLI integral ofrece el equivalente `--decision-sha256`. Ninguna de las dos interfaces autentica a la persona que introduce el digest: la procedencia de aprobación sigue siendo externa y debe conservarse en el registro.
