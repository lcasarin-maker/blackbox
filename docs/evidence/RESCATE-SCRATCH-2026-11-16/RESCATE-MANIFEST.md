# RESCATE-MANIFEST: estado de trabajo de ~/scratch/blackbox, 2026-11-16

Voto de Luis (2026-11-16): guardar el estado de trabajo para que no se pierda nada. Fuente: `~/scratch/blackbox/` (solo lectura; nada se movio ni se borro allí).
Este directorio conserva la ruta relativa de origen. Las rutas con datos que la guarda del repo publico rechaza aparecen con `@PRIV@` en lugar del token; el sha256 identifica el archivo original.

## Resumen medido

| Categoria | Archivos | Bytes |
|---|---:|---:|
| copiados al repo | 171 | 347198 |
| ya en el repo (blob existente en el historial) | 89 | 29219 |
| no copiados (por archivo, con motivo) | 109 | 1152908 |
| copias de arbol de repo (por unidad) | 104280 | 1477053262 |
| tmp de pytest y fixtures (por unidad) | 77744 | 1367524032 |
| .git de fixtures (por unidad) | 117 | 97651 |
| no regulares: enlaces simbolicos y tuberias (por unidad) | 531 | 42317 |
| **total** | **183041** | **2846246587** |

Limites aplicados: archivo mayor de 2 MB no se copia; rescate total menor de 60 MB (copiado: 347198 bytes); sin node_modules, target, cache, volcados, modelos ni copias de repos enteros. `could_not_run: 4`: cuatro archivos de fixtures con modo 000 (`parameters/modeset` de `test_drm_modeset_leer_control_1`, uno por cada copia de la suite) no se pudieron leer; su digest de unidad incluye la marca `COULD_NOT_READ:PermissionError` en lugar del hash. La clasificacion en si no tuvo fallos de instrumento (`COULD_NOT_RUN` por archivo: 0).

Criterio de copia: texto UTF-8, menor de 2 MB, con blob ausente del historial del repo y con **cero** coincidencias del patron de `tests/test_sin_datos_privados.py` (usuario, hostname, IPs RFC 1918, MAC, proyectos ajenos, rutas de la base de conocimiento) y de un barrido adicional de correos, claves y tokens. En la duda, al manifiesto. Verificacion de cada copia: `sha256sum` de la copia igual al del origen (171 de 171).

## 1. Copiados al repo

| ruta (relativa a `~/scratch/blackbox/`) | bytes | sha256 |
|---|---:|---|
| `2026-11-09-prueba-1025/carga.txt` | 1173 | `664df1fdfbb10f10d6fe59ff111729f414bafe312f6dd49e7f280b27fee23c5b` |
| `2026-11-09-prueba-1025/log.txt` | 2252 | `72a7f10a781da5f1e3adfaad96ee8e7c46bf6a0e9b8a37c13c38ee787a706d8d` |
| `2026-11-09-prueba-1025/observa.sh` | 1446 | `8d481b94366746d2544f71c84945e8dfd3b1211bcf61412abc782f49bbabe533` |
| `2026-11-09-zneill/borrador-387832-respuesta-zneill.md` | 6771 | `c5a3777660281e923e9d74779556e65cc721ec80458d4d2a98e9a32ba62f010f` |
| `2026-11-13-clean/REPORT-FLOTA-SOL.md` | 7049 | `fb2f677c3c85900f668b552953d1f6e3376b4f395d29c7b4b383721ebbbec044` |
| `2026-11-13-clean/after-branches.txt` | 122 | `ac794d2fd0b72aee74ca590aef3247efeef835c6d9ec320be2f2be86c0e10f79` |
| `2026-11-13-clean/after-cherry.txt` | 165 | `939ac1c7a2b6786fb78833272f93a269e7e9642e781417de7d96a1e6bb480003` |
| `2026-11-13-clean/after-status.txt` | 31 | `28a913811dbc4c22a5a4b0fac6d25b33da9e1009cb5b9b2ffa31cdad41b49622` |
| `2026-11-13-clean/before-branches.txt` | 122 | `98fcc6701442ac659ce88389762e40c97937291d8636495572f74206dbdc2560` |
| `2026-11-13-clean/before-cherry.txt` | 55 | `e42825922b9157526b63c2827b2d6e5860146d9b95e8b1090d061aff654c8e49` |
| `2026-11-13-clean/cherry-after-harvest.txt` | 165 | `939ac1c7a2b6786fb78833272f93a269e7e9642e781417de7d96a1e6bb480003` |
| `2026-11-13-clean/deepclean-ejecucion.txt` | 286 | `3e058d0b644994c5f8149d70e4867317b9b79b5dc5b406f5ec6c3ca05f2d2805` |
| `2026-11-13-clean/deepclean-sim.txt` | 168 | `ec3215a88ca9f1e4856c4f945431dd7376eb62924a0b384fa4bac76c93c9ea8d` |
| `2026-11-13-clean/diagnose.txt` | 2043 | `91496cb31832311643115f1a1e19f5d9810891d431f365300ae6f41b86d6fa3e` |
| `2026-11-13-clean/h3-resolucion/MANIFEST.json` | 347 | `37c2cd8fb93302083b5553aec30a7f965a0a8681779ad7fb14bd3bb28a0545f8` |
| `2026-11-13-clean/h3-resolucion/aceptacion-roja.txt` | 5245 | `90c4194da2e373df2243a89d54eaf09feaf0b72e67018c70cb62a7bed01aa43f` |
| `2026-11-13-clean/h3-resolucion/conciliacion-final.txt` | 1058 | `18d383f28f7a3034057017417e01a88ad7d9099abea535dc0e10797a5afaf3fb` |
| `2026-11-13-clean/h3-resolucion/control-completitud.json` | 189 | `e563f46b9fd278ae6a436bb9799af260bc718d59a54fc304c804bd36d059cb46` |
| `2026-11-13-clean/h3-resolucion/control_identidad.py` | 535 | `977bdc04e1c6921f4fb3dd57f425cc999d9752b7d3a306828af71e9196ca942e` |
| `2026-11-13-clean/h3-resolucion/identidad-control.json` | 293 | `e0afafc2ab9c41cff5baf4ace33100b5efb906fb3818d0cf408917374c536ace` |
| `2026-11-13-clean/last-check.txt` | 81 | `61c511a53645f7301721fc05cac1a862b7266b6bbd040d07e8972e3ab1683958` |
| `2026-11-13-clean/main-reflog.raw.txt` | 1185 | `fa26abd30ed5a8ab763d9f756a29279bbbc818710f2500761c6e847bd5e25667` |
| `2026-11-13-clean/main-reflog.txt` | 1185 | `fa26abd30ed5a8ab763d9f756a29279bbbc818710f2500761c6e847bd5e25667` |
| `2026-11-13-clean/origin-cherry.txt` | 43 | `955dce26d3d65dd39b141926d4a512967c2b0a329787ebf43bf95221ca1fb3dd` |
| `2026-11-13-clean/privacy-current.txt` | 836 | `f6f07c81b625cadf77d011eaf19301e2ab7d783cc60691ec78c0f0418a77f33f` |
| `2026-11-13-clean/published-all.txt` | 261 | `367cd1058f19c978d50fcacd8a7e2a64ee1f35b3fd94531e8b0502d8d249b365` |
| `2026-11-13-clean/published-commits.txt` | 120 | `96e29de7011e815fd5efb60d88585bc6c75701c907a00468fb7bb636f7bab371` |
| `2026-11-13-clean/push-privacy-task.txt` | 4201 | `0cf83ddf2851426ea3728e7662a16c85f9b66a0212f0b8474fabfb1346847f24` |
| `2026-11-13-clean/push-suite-task.txt` | 4177 | `7bc2bd30faf118c3f0d2a2fbb02dda08873543cc20959b4dcf6400c3a9dc8bd7` |
| `2026-11-13-clean/reflog.raw.txt` | 1185 | `fa26abd30ed5a8ab763d9f756a29279bbbc818710f2500761c6e847bd5e25667` |
| `2026-11-13-clean/reflog.txt` | 1185 | `fa26abd30ed5a8ab763d9f756a29279bbbc818710f2500761c6e847bd5e25667` |
| `2026-11-13-clean/remote-equality.txt` | 145 | `3b938c69eb17145b67f5be209cbba8a971da66107ed3351f96be39920ef28b41` |
| `2026-11-13-clean/ruff-gitleaks-controls.txt` | 195 | `0b8babf7e6ec50eab854f95521712aeaf1ff962c83f9c34bd07769034002b74b` |
| `2026-11-13-clean/status-branch.raw.txt` | 26 | `2ebd13cacaf6c180d91decb9d32bb9bdbcef747ebc3c5ea521c2c03a21924f14` |
| `2026-11-13-clean/status-branch.txt` | 26 | `2ebd13cacaf6c180d91decb9d32bb9bdbcef747ebc3c5ea521c2c03a21924f14` |
| `2026-11-13-clean/suite-comparison.txt` | 725 | `c5abe624d92c16c92c3724617d93e25971165720b3809b37e123675bb82ef106` |
| `2026-11-13-clean/worktrees.txt` | 101 | `c01a3f322c020626e0953fc3d593616200665c833082fea4f6bb38c8910bc4cb` |
| `2026-11-13-close-check-r2/candidato-staged.diff` | 25182 | `7aa33416dd4a4e1176e9edb346a56b8369245855bdc96cdf589d25ae93d1cde8` |
| `2026-11-13-close-check-r2/canonical-measurement.txt` | 99 | `abee1293489a3c019ad41568b4f3bb9dcd9ba7cf83619dfa76c340587b484fbe` |
| `2026-11-13-close-check-r2/casos/bad.sh` | 27 | `690e5d7dcfadfffa453ce38076cff9a5264d660d1512afee1db6e9ffc17f7d31` |
| `2026-11-13-close-check-r2/casos/good.sh` | 29 | `4821a32101c5aeb4fca95480483c9aa3905675e0d2c1f76a308a1237b4b69e78` |
| `2026-11-13-close-check-r2/casos/product.py` | 112 | `a6c6b534c07f8d30d777c1ee0e678f286b598d1bef9838e4b6a7f61915210fe5` |
| `2026-11-13-close-check-r2/casos/ran` | 8 | `85dc0c638f095c20fa6e90eeaf897d9f821ae2419ef05f5e078e69d5a06454d5` |
| `2026-11-13-close-check-r2/casos/receipt` | 2 | `2689367b205c16ce32ed4200942b8b8b1e262dfc70d9bc9fbc77c49699a4f1df` |
| `2026-11-13-close-check-r2/measurement-tests-final.txt` | 98 | `c517efd297862dd312ec9e4a24ca5981120918f4b1bc5cde1429bca318323b85` |
| `2026-11-13-close-check-r2/measurement-tests.txt` | 98 | `4411b877d5771fc1e4342c11d5cada44ce93ed7b3a6de21693ca4dcc3342143b` |
| `2026-11-13-close-check-r2/medir_clasificador.py` | 4091 | `22aac5513e720e0e62ecdff3159728d33d73bce41b03b2c6f2fbad76884e909f` |
| `2026-11-13-close-check-r2/negativos.py` | 1588 | `6b0048767dd801db3c2ea455f161bdfd6104cd3f166e1c755a9d63f374484085` |
| `2026-11-13-close-check-r2/privacidad.txt` | 98 | `048f1bb2edb3fd2cdbebceec667909248a071ef092e73d9de1a8930367f68401` |
| `2026-11-13-close-check-r2/reporte.md` | 7484 | `64bd3c3fed6b7f98cb9493047edc44e78813d4d123fa024008f83a627e1947b1` |
| `2026-11-13-close-check-r2/runner-cnr.json` | 1001 | `1518e39995a576c84959746d8c549a12aa1fdf1d0c2c8d8d73bdad705f8e394e` |
| `2026-11-13-close-check-r2/runner-report.json` | 979 | `6e3f8ac7c78a6a49b63a2422a7a3029564b2763a67658bd9b413b0f0309f15fe` |
| `2026-11-13-close-check-r2/runner-report/simple.json` | 394 | `31de8a89a14847c567623bc69bb8eb1f1df07abb1cf3b2e9d0b96d95f6c7f490` |
| `2026-11-13-close-check-r2/runner-report/tasks/OLD.md` | 71 | `e7047c72a504b94fc213a762792733779da471c4aad8f4da1ca5964bbed5aa24` |
| `2026-11-13-close-check-r2/runner-report/tasks/X.md` | 72 | `a01ab151274f0334990d492161925a195d5760f79ded7102ef57c1da6b273153` |
| `2026-11-13-close-check-r2/runner_report.py` | 1768 | `9e93e69e003c6bc3d410bd1e8a04517ccb13879e65596c040884965cd700ab4c` |
| `2026-11-13-close-check-r2/test_close_check_lint_block.py` | 877 | `2d5fe6a3e3b029522bf8ea98536099ff387199d4f611fe037abe45e467c67ff2` |
| `2026-11-13-close-check-r2/test_close_check_report_measurement.py` | 3503 | `2cf033747ac46c488651c21991cd420f9884340b20c7e16ebac28198f1e7f939` |
| `2026-11-13-close-check-r2/test_sin_aislar_git.py` | 3466 | `837ae1bf806cc6d51410f6c0d7ca8e30087e03833b9c6893155d258778e750c0` |
| `2026-11-13-close-check/aceptacion-roja.txt` | 4340 | `2bac38e301339723e7519d955952ba5d1712f2172e7c38e9c79b4e819c768f49` |
| `2026-11-13-close-check/antes.json` | 570 | `5df8e01d228e7a632b73f48295231900396708093abf120374117b54172bf148` |
| `2026-11-13-close-check/close-check-enforce.patch` | 3488 | `7a3b9dda4b80b80f4ca8ca8204e3cf0b302ef18f321a1392c37814140e85fabf` |
| `2026-11-13-close-check/fixture-medidor/product.py` | 70 | `5c963b923b7238d57efaaa7ba4ae22451782e94941edacb6ad319b2053095c62` |
| `2026-11-13-close-check/fixture-medidor/ran` | 18 | `1c50089d94855310620b86b0dffa64313afe2f0f7109eae8afe451452a701e15` |
| `2026-11-13-close-check/fixture-medidor/tasks/done/X.md` | 70 | `85cb100ae5d22518b8273ee8f506519a8f072a8465828e7daecab04549ceccd8` |
| `2026-11-13-close-check/fuente-duplicada.json` | 1057 | `135ae61be3e505f2ba889a70a9d1b6fe2830638f4880c5de5d039c595fb17cae` |
| `2026-11-13-close-check/gate-staged.diff` | 9846 | `610435e6cf60189202a133caddea61cf17f8982edde26240861365e83e781969` |
| `2026-11-13-close-check/materializacion-staged.diff` | 11184 | `438d85333a43f1fd597eb3f8f3d13fd22d50cc7cfb93fa5de1787c30f8aa8a7f` |
| `2026-11-13-close-check/materializacion.json` | 459 | `fd90810efbe76a3c7db88c21f7d3bb9e5e8d01ac2a92c716e5553ab22785d460` |
| `2026-11-13-close-check/materializar.py` | 2757 | `fd7f580b719e35c4c5b003e7f0309c340727070891847620f6f12d4f2eb2f147` |
| `2026-11-13-close-check/medir_detector.py` | 1723 | `73244275d4939b7d93dff56c76489cda50b66a39826acc5cf7e132594e5ca746` |
| `2026-11-13-close-check/policy-tests.txt` | 99 | `0ad254ff34e4359d5b284919268027367a3953edbb3532e78c69f6d3c612f959` |
| `2026-11-13-close-check/preparar_fix.py` | 1595 | `b5f9e5ae181a77f44f0fcabcf219b8982d13e5ade3b1de7dfbdc6ada0ac20235` |
| `2026-11-13-close-check/privacidad.txt` | 98 | `0736b0d0d05bbe15a95e77677baef49a38cf862fa0a7f81131e74e3256879f16` |
| `2026-11-13-close-check/reporte.md` | 7322 | `5a9f044d2552f86a17106ae915eaf9c5ff16da948c839363e39006455ef28ed1` |
| `2026-11-13-close-check/runner-actual.json` | 982 | `3319c72b4524e453b08d3cafe008bb0133543b12d8fa8a17f05d839dfce9885c` |
| `2026-11-13-close-check/runner-actual/simple.json` | 330 | `028c2db5ea1e3909f3bde25eb70c01054280279bfa0e5ba21bbb3a5dc6683bda` |
| `2026-11-13-close-check/verificar_materializacion.py` | 1126 | `ba5b126a66bdc6148f921603b2bf95532bf230a6699a7f9700081e4677cb38bd` |
| `2026-11-13-corredor-close-check-r2/INFORME.md` | 2740 | `e8e27064ca60cc95a4d8a42b7db72fcea380eba6e02b96c44fde94f194aff6bb` |
| `2026-11-13-corredor-conciliacion/FICHA-EVIDENCIA.md` | 1935 | `3a18c22a6fd844de7d1f1e7dfccaa756ecef758ee17cfcb3b175d45695b5e33d` |
| `2026-11-13-corredor-conciliacion/both-bases-invalid.stdout` | 2189 | `784ef9c41006cabe09acf4b6e071eee6093f7e29466f8d532c2debd8db135dad` |
| `2026-11-13-corredor-conciliacion/canonical-control-grep.stdout` | 38 | `9acdc4b2a616ea0b0d4e6440f67396895548b6ede82841d18cab6584b2848298` |
| `2026-11-13-corredor-conciliacion/canonical-red-echo.stdout` | 35 | `0adb169c48db5ffe05de41e50cd10a3e8e59e801e965a59be259ba58c8aa5e5e` |
| `2026-11-13-corredor-conciliacion/fallback-control-commit.stdout` | 41 | `4c05551212c3749755550a9ddec6047d5e493737a68caf05325cd83fac755744` |
| `2026-11-13-corredor-conciliacion/fallback-control-tree.stdout` | 41 | `cd33eafcbf62e377aaa2c10cc60a3e9dc862678856e793f436e4643ed1bf7637` |
| `2026-11-13-corredor-conciliacion/final-subject.stdout` | 82 | `21e60eb2277c1a898f754cae862fb584cd44de21d6f95dfb227708c6abddcd58` |
| `2026-11-13-corredor-conciliacion/fixture-commit-tree.stdout` | 41 | `b28728e4cb38aed8f8c1bb2e08ec2d73d0b73858bc50ff9b57014cab8508b79b` |
| `2026-11-13-corredor-conciliacion/fixture-write-tree.stdout` | 41 | `12f04cdc8c887fea94207fbcd999d7a27143b8e1b05e6d9dc4608c96fbcf18d4` |
| `2026-11-13-corredor-conciliacion/invalid-contract-base-initial-confounded.stdout` | 2737 | `ad5704b08c18bad5ace20c1864905ea71bef96f049c4474eb145c5e984ee0a98` |
| `2026-11-13-corredor-conciliacion/invalid-contract-base.stdout` | 2016 | `ec89671263f20772ea104bb6bc0a8705c1dda507b55b54bd9bb074b4357d4c53` |
| `2026-11-13-corredor-conciliacion/invalid-policy-base.stdout` | 1807 | `0c1f37118de75ff80bc5701ea93826a1a53aadcc679d9492ed11a05a068d7dcd` |
| `2026-11-13-corredor-conciliacion/invalid-selection-base.stdout` | 2023 | `4b96119eccf9c0e2a8cbb3b2dbcc8217f4be5f7a515bd3c528f62289f5abfef9` |
| `2026-11-13-corredor-conciliacion/invalid-selection-fallback-fails.stdout` | 2022 | `f62557ae4a02ccb9092f15b9951a376f411252e70cfc6b5889331b82e01edee7` |
| `2026-11-13-corredor-conciliacion/policy-real-invalid-base.stdout` | 570 | `5df8e01d228e7a632b73f48295231900396708093abf120374117b54172bf148` |
| `2026-11-13-corredor-conciliacion/policy-real-positive.stdout` | 570 | `5df8e01d228e7a632b73f48295231900396708093abf120374117b54172bf148` |
| `2026-11-13-corredor-conciliacion/policy-source-invalid-base.stderr` | 151 | `d270a3ec53abda8d4d76c5d3215a7913a5bbd540d801c3ffc120f304f4b42502` |
| `2026-11-13-corredor-conciliacion/policy-source-real-positive.stdout` | 41 | `11352994f364fdfcb2dbde376f4628209b125575745920cceb8150b09d45e864` |
| `2026-11-13-corredor-conciliacion/positive.stdout` | 1641 | `83549a8fcf22b5d3361f66f09762be16a3e10510cf7baa41ff275ce383f4103b` |
| `2026-11-13-corredor-conciliacion/privacy-instrument-cnr.stdout` | 1863 | `8aa11df46ad73f2cc2531ad07c1deba07ee84dbaec32e3321f675c7b4998e807` |
| `2026-11-13-corredor-conciliacion/privacy-negative.stdout` | 2363 | `5f75715469d7168a1afaa2ecdf7f3e4dae545855d28ab4647ce53473f0530d6d` |
| `2026-11-13-corredor-conciliacion/privacy-real-positive.stdout` | 98 | `d733615cadfa15962f9ed05708527503cab133d625003c52bf7406667b8f6818` |
| `2026-11-13-corredor-conciliacion/setup-16.stdout` | 41 | `4cdd9b8c1dd7ca6709e9dc7beae4ab334df85d02319e59adbec24847a2958d06` |
| `2026-11-13-corredor-conciliacion/setup-17.stdout` | 41 | `85f099a2d796fcf4b73ebf2f000854b5789d198e69ae6ab425a40ae79e5349ed` |
| `2026-11-13-corredor-conciliacion/setup-21.stdout` | 41 | `70173c5e754617571ca6f24c6b83cfa0853bcd53b55cb891510b5f2c62866b32` |
| `2026-11-13-corredor-conciliacion/setup-22.stdout` | 41 | `6c08960ad117010da9e40d5e8b239dcefe9d3412fc3264b06048b2d75309bb85` |
| `2026-11-13-corredor-conciliacion/setup-3.stdout` | 41 | `231bc3fb71975204eca0bc0389beb7bf1943c38e1addf3e895e8c8225c51564a` |
| `2026-11-13-corredor-conciliacion/setup-4.stdout` | 41 | `ee1595566dc9f91bc6dcc7533f55b5d350b202287f14ec6e0e724e97a465a5ea` |
| `2026-11-13-corredor-conciliacion/setup-8.stdout` | 41 | `9ac022c3b57c46664fcc230c9eff3e2d142cabd175d4a066a15d2ce27f937a83` |
| `2026-11-13-corredor-conciliacion/setup-9.stdout` | 41 | `63b923e61ea74e924de7b979b572085754a8e2d2ccbc49ab7465d9dd8981ab3f` |
| `2026-11-13-corredor-conciliacion/subject.stdout` | 82 | `21e60eb2277c1a898f754cae862fb584cd44de21d6f95dfb227708c6abddcd58` |
| `2026-11-13-corredor-conciliacion/sujeto/simple.json` | 1576 | `c485f7d1b028c37b559b84dbaba9bd2440c7e994e8cac3977432666b81f905b5` |
| `2026-11-13-paquete-aterrizaje/MANIFEST.json` | 1041 | `e92a76119abecfd506541caebc7f88d5b1cda9d6aecb827b78b484c2ca0c7083` |
| `2026-11-13-paquete-aterrizaje/PAQUETE.md` | 18359 | `38249b31d55658e27f74d2c08f68cb5df144b3347b113252f387702b80bd739a` |
| `2026-11-13-paquete-aterrizaje/boleta-borrador.json` | 1922 | `b71c32a62793243a065f60bbe66d9b5c403fc7781ded86f9ec0fa9c8751301af` |
| `2026-11-13-paquete-aterrizaje/evidencias.json` | 5940 | `5c7cea4cd334a4147c3b78d0fb9109a2cd261bc0fd90e2631b520f82f38d90dd` |
| `2026-11-13-paquete-aterrizaje/sujeto.json` | 8787 | `27398747da2802a3efa30607da76d2fb3354f22af0990cd400c4da252259c5d5` |
| `2026-11-13-publicacion-6194cf8f/MANIFEST.json` | 1061 | `c3c932383a83cfa1384a4f37aadd5c630f09c8f1fa272877b42d84846195b722` |
| `2026-11-13-publicacion-6194cf8f/PUBLICACION.md` | 5295 | `b1fe0c98d030979bfee4999ec1a93d05bf0776512ef7f01eefc7b38476d3e632` |
| `2026-11-13-publicacion-6194cf8f/conciliacion-antes.json` | 931 | `f0597f548558e9f7f5373fe6e39b301f10fc4037e8c4ca15d7394a93f280d69a` |
| `2026-11-13-publicacion-6194cf8f/conciliacion-despues.json` | 782 | `00152b2ea1c52cc178b0927fc40b3b2de11e742dc991e3b85402ec0133f26312` |
| `2026-11-13-publicacion-6194cf8f/ls-remote-despues.txt` | 59 | `27f18095252ea5daeb7dadd47c8ff8b6f5ca51726ae57114bead652328f79f35` |
| `2026-11-13-publicacion-6194cf8f/push-exit.json` | 164 | `4a228fce5b547831c5e67f038a1bfcd360f009f46b00b64c6b30b33e2282c589` |
| `2026-11-13-publicacion-6194cf8f/push-sanitizado.txt` | 7702 | `335b7eef38fff46fbde0238a0d882338d2a40d91cbf4d49cfa92b22441fa24f4` |
| `2026-11-13-publicacion-6194cf8f/push.raw.NO-PUBLICAR.txt` | 7702 | `335b7eef38fff46fbde0238a0d882338d2a40d91cbf4d49cfa92b22441fa24f4` |
| `2026-11-13-publicacion-6194cf8f/recibo-hook.json` | 11096 | `15e058c2889929a6104e506894b6971de08b4d002f32e899e8a9b1eb320b7cdc` |
| `2026-11-13-remediacion/ajustar.py` | 1201 | `79880e8d9c9c19627bb24da6687911a003d300a354eb1d4f304a85d9f7a8938a` |
| `2026-11-13-remediacion/alarma-control/alarma.json` | 116 | `f3b9edc3159dd5322b14fc5fa4ddf2498bc796ebc5d39e510152601813cf93cf` |
| `2026-11-13-remediacion/conciliacion-publicacion.json` | 222 | `faa153764eb305a9820926b9d358db84cda14444d6603d63b35c6972e20a12db` |
| `2026-11-13-remediacion/focal.txt` | 187 | `0e149d3d1aebefbfa94fd93cb3528ff76499c90c6aaf2d6ad6387b7bba9e9fff` |
| `2026-11-13-remediacion/gate-limpio.txt` | 2363 | `a3abdf25db8884722761ed17989cb95ccc7802534825a994db3039e934a403a8` |
| `2026-11-13-remediacion/gate-negativo.txt` | 2865 | `91956b6e7bc8e8fceb0a5b89bd061db72aa361206be4f73eb39699edae32163f` |
| `2026-11-13-remediacion/guarda-antes.txt` | 754 | `4169435776441b26cdd160e39da9f1028b18a60e108ba599108f86d56a205bae` |
| `2026-11-13-remediacion/guarda-despues.txt` | 98 | `22dd0c62627bab2e59d897d144787cbc5739e962cdbdb0cb1119ee695b3fe482` |
| `2026-11-13-remediacion/guarda-ficha.txt` | 98 | `b1b71f754b5df16da9dacd727d80b8aef00ca43f62f17c599c06d65e697af750` |
| `2026-11-13-remediacion/guarda-negativa.txt` | 751 | `4e0046e1823dbc5fdfc1253c534861f598358ae320856af3e1cefef9235cd43b` |
| `2026-11-13-remediacion/guarda-revision.txt` | 98 | `76add6ffa65db93bff25b27dbc86fcb066b040b12fc7e9bafa514787962f34ce` |
| `2026-11-13-remediacion/historia-conteos.json` | 117 | `c56d10b04ab8a75428cd20bca4e792498b369764d08c7a43ce93f3f70ab7092c` |
| `2026-11-13-remediacion/historia-marcas.json` | 77 | `b565957655e91585fbb87b454d2d2010e7e102b110b1249cbe2130215bf552d3` |
| `2026-11-13-remediacion/publicacion-verdict.json` | 416 | `a891f51cc700ab4a3fcbde780be514b49f16e5267487f7c339e8d018390db02b` |
| `2026-11-13-remediacion/publicacion.md` | 6748 | `2c1b67e1790bde36b3ee6e2b916b87e0f5b31f8d7208c85f0727956198aeeb29` |
| `2026-11-13-remediacion/reporte.md` | 7323 | `c72989d27dcfa73f55ad3302983ee1323cc7a51ee4f2db9dbc6d25f35ab3a3fe` |
| `2026-11-13-remediacion/revision-emergencia-staged.txt` | 625 | `2f6c7bb82211e2d79f3b96f8e65faf01453c68cac54da31ceff98de3d8c6cb14` |
| `2026-11-13-remediacion/revision-focal-final.txt` | 358 | `1bdcb763caf5c688955bfafbf58aab2df6fa43568eb109b82edd6efba8af00c3` |
| `2026-11-13-remediacion/revision-gate-head-disco-limpio.txt` | 3000 | `382271288dc4cce2e187a0d38a9d8d0a80805f53018a9007417606924d30cb40` |
| `2026-11-13-remediacion/revision-gate-limpio.txt` | 2342 | `547195dbdad768f9ec9452458778156a8cd9c412942d5b5b5d05fa49c8735486` |
| `2026-11-13-remediacion/revision-green.txt` | 1618 | `07731422d3df2fedfd6828f79a0a549dd876370f5a81cd5f578a964e517027c1` |
| `2026-11-13-remediacion/revision-guarda-head-disco-borrado.txt` | 751 | `4307c56ef2942ebfc1c4b62724158a3c85d367bc05ae41cdd6c8c957ce1e933a` |
| `2026-11-13-remediacion/revision-guarda-head-disco-limpio.txt` | 751 | `a7c9538401184937defd1703cf75458f183f456a705abdcb4b5db3c78a43cd04` |
| `2026-11-13-remediacion/revision-inventario-staged.txt` | 344 | `9e03a910ca03a66e9ea25922c286e6d5451968b5d68774eb705ff5b0bd111f96` |
| `2026-11-13-remediacion/revision-respuestas.md` | 6986 | `f0db03fcab11fc37444ac33c691b046b4b5afa5c9afe58aa245a305a634cb410` |
| `2026-11-13-remediacion/revision-snapshot-staged.txt` | 201 | `16da9aa58006a2d988a83f33e9238a92320001d2c59fdb5db2a95c75e25f0233` |
| `2026-11-13-remediacion/suite-comparacion.json` | 1986 | `eb19492936683f05b8a35d0cd3291854b6b0a94452234aa7094b1bb61187ccd4` |
| `2026-11-13-remediacion/suite-revision-comparacion.json` | 1987 | `533688a2811374a03b84658e428e9c77517d20012d9f55b8780d0e61f253bad6` |
| `2026-11-13-remediacion/transformaciones.json` | 509 | `6473552277121d49a124e1c58b695003ef3bfd1697ed5a68c7548f977aee317f` |
| `2026-11-13-revision-claude/bash-nuevo.txt` | 446 | `02c4d5f3ef0e458bc0cf789bdadc95ade0573d8b3971c45dce3ce1f40af91b5a` |
| `2026-11-13-revision-claude/bash-previo.txt` | 373 | `d7e7cb20fbc9fb1a722da2e4302d75747e0d9a268f6608cf46c012209447d646` |
| `2026-11-13-revision-claude/verify-limpio.json` | 8802 | `7a999f2170c7daa80ae5d977e6a96074e4c9573e9959ddcb5c845f641124b0c1` |
| `2026-11-13-revision-claude/verify-plantado.json` | 9444 | `1b013f2d8a33b06f7a1da2afbddea8139ddbc24f8e61a0a23959e41ad7b4d0af` |
| `2026-11-13-revision-close-check-opus-r2/alineacion.txt` | 177 | `08afb5bb1dafb6227b4748620d0048a77761c670e323e5c16991509da0bdd806` |
| `2026-11-13-revision-close-check-opus-r2/clasificador-vivo.txt` | 379 | `d3f46ea28015f9a133ca36e0aadbc3f41d2139ff8fc6f1f009c55b5434e0dda6` |
| `2026-11-13-revision-close-check-opus-r2/informe.md` | 8618 | `00c5e873e2f13f29c959014d97872ea119bd1d4e5daa3933b3569b4ce7b8123e` |
| `2026-11-13-revision-close-check-opus-r2/negativos-r2.txt` | 718 | `36508906e75b881aaac908683a89f53fb4dc24036aa82d43d8ff30316887c796` |
| `2026-11-13-revision-close-check-opus-r2/sujeto-hashes.txt` | 728 | `0c8634fca85313c919e54ace5629bad0a4df6dd99f03eb58939812a2452a27ef` |
| `2026-11-13-revision-close-check-opus/fichas.txt` | 387 | `5a3d3c4a5e2217130c681ed32b75296debfaf7853c55ae755e524cc55f3ac81b` |
| `2026-11-13-revision-close-check-opus/fp-blackbox.txt` | 12005 | `bb4d7aad33f28e7d0a8db6476aa6a35b63d6d365adb375a45e3295b7036b5972` |
| `2026-11-13-revision-close-check-opus/revisor-corridas.txt` | 1484 | `c47c7910915e3b44508ee5d3fc81201aa793542d35cf7be3b28c20e9a13da62d` |
| `2026-11-16-clean/deepclean.txt` | 291 | `d1dbf1edc961229a15f74579d917ffd48a3a7b303d4de6b79185aaf4e2560867` |
| `2026-11-16-clean/negctl-gateway/tools/gateway/admission_check_wrapper.sh` | 43 | `eb3b842adb8e6a4ef0f5e0cfe16b769720d738bda1cc1c211f73e4cae17c2472` |
| `2026-11-16-clean/negctl-gateway/tools/gateway/main.py` | 64 | `c568ad3d061bf81c395bc14f9f7beb66745dc5c0a19f76212a315a7d39f6f2c7` |
| `2026-11-16-clean/push-1.log` | 11652 | `0f7ac346a9c87a9f73c6dec684d8fc6d09236a5660318caf1a859227d34e5eea` |
| `2026-11-16-clean/push-2.log` | 5410 | `f27131e7de248a45035f7e64829227398a0ea6ef771d7a18fcf4ddad4c70a26b` |

## 2. Ya en el repo (no se copian: su blob existe en el historial)

| ruta | bytes | sha256 |
|---|---:|---|
| `2026-11-09-prueba-1025/salida.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-09-prueba-1025/salida2.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/fetch.raw.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/fetch.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/stashes.raw.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/stashes.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/status.raw.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-clean/status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-close-check/materializacion-control/tasks/backlog/DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01.md` | 1581 | `f3b6b35f8360b605b06b9b83eacc0c39b0b0acea81eebeaed055e4b757537b2b` |
| `2026-11-13-close-check/materializacion-control/tasks/backlog/DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01.md` | 1367 | `24c72ce41baca7bb9086a1d537cf970b37132f93f107e20a4189073f51762b13` |
| `2026-11-13-close-check/runner-actual/.simple/state/verify.lock` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-close-check/simplecode-source.json` | 249 | `89c1bd4084eebda3d66b9805e07b347f4b3df5e467da148a5e10c699f42aa4ec` |
| `2026-11-13-corredor-conciliacion/both-bases-invalid.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/canonical-control-grep.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/canonical-red-echo.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-commit.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-ref.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-ref.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-reset-index.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-reset-index.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-stage.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-stage.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fallback-control-tree.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/final-status.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/final-status.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/final-subject.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-commit-tree.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-ref-contract.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-ref-contract.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-reset-index.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-reset-index.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-return-good.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-return-good.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-stage-contract.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-stage-contract.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/fixture-write-tree.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/invalid-contract-base-initial-confounded.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/invalid-contract-base.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/invalid-policy-base.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/invalid-selection-base.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/invalid-selection-fallback-fails.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/policy-real-invalid-base.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/policy-real-positive.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/policy-source-invalid-base.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/policy-source-real-positive.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/positive.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/privacy-instrument-cnr.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/privacy-negative.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/privacy-real-positive.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-1.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-1.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-10.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-10.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-15.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-15.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-16.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-17.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-18.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-18.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-2.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-2.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-20.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-20.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-21.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-22.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-23.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-23.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-3.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-4.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-5.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-5.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-6.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-6.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-7.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-7.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-8.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/setup-9.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/subject.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-corredor-conciliacion/sujeto/tests/fixtures/datos_privados_baseline.json` | 3050 | `3a1a57acd52f832eb48ca1022d98f9369fd1bec7156a887991d4c05a3b538fb4` |
| `2026-11-13-corredor-conciliacion/sujeto/tests/test_sin_datos_privados.py` | 11619 | `605741b6b21035cae8df753598d758bce6f1a47e149c0401bd7fae7dd1e05e34` |
| `2026-11-13-remediacion/pendientes-revision.json` | 1110 | `859b4d0178145f1c59c26bf14b9c0fd9f4ac793e0affe0740502938103fea64a` |
| `2026-11-13-revision-claude/verify-limpio.err` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-revision-claude/verify-limpio.time` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-revision-claude/verify-plantado.err` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-13-revision-close-check-opus-r2/patch-r2.patch` | 6298 | `146ce275ee1c02f45ab27c76d80085749803892c5b47297fd8576ac364aab767` |
| `2026-11-16-clean/negctl-gateway/tests/test_gateway_handoff.py` | 3945 | `925d389c4950eecd8216a7bc046a4c653681bd87d09066e7458586efdd2c406f` |
| `2026-11-16-clean/sarctl/dd/sa15` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-16-clean/sarctl/full/sa20261115` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `2026-11-16-clean/sarctl/stale/sa20261115` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## 3. No copiados, por archivo

Motivo: la guarda de privacidad del repo publico los rechazaria, o son salida reproducible de una herramienta. Siguen en scratch; al caducar (14 dias) pasan a cuarentena, no se borran. Rescatarlos al repo exige sanearlos con voto de Luis (la guarda solo crece por voto fechado).

| ruta | bytes | sha256 | motivo |
|---|---:|---|---|
| `2026-11-09-deepclean/MANIFEST.tsv` | 3879 | `201f5f4d9125fb3331b898a36cdb90b6576439f82e8a5f11447a8068a2029683` | gate de privacidad del repo: 5 dato(s) privado(s) |
| `2026-11-11-deepclean/MANIFEST.tsv` | 126 | `07d9df746b78ffaf01fab9d6661075fc2ab18f5131295167fdcff2d750372e2c` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-clean/REPORT.md` | 14769 | `8a2fed915fdb989b71ebfc240372fa7e92fd24664a895e53986092ac74e40c77` | gate de privacidad del repo: 17 dato(s) privado(s) |
| `2026-11-13-clean/activity-final.raw.json` | 27151 | `8e2f9beb25c6c8e0f06746302259900958de8d2d3716dd71d1355675a23144e0` | gate de privacidad del repo: 39 dato(s) privado(s) |
| `2026-11-13-clean/after-worktrees.txt` | 78 | `14d23ea2f868894c84e00ce38d1f910c4e3ee924acebe03b1ea0eb0a9c3e8a0c` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/before-worktrees.txt` | 219 | `dc2013898ca353363853155fac8d94eced6e25029281a77e53bec17e564b0830` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/code-identity-control.txt` | 3798 | `f51759cd7602f327fa624ea473241586ae423805b7f7b3acb3d71fa31e17f719` | fila pii-staged del pre-commit: 2 falsos positivos (decoradores +@pytest.* leidos como correo); no se evade el gate |
| `2026-11-13-clean/commands.raw.json` | 10001 | `b6b297a81859a6887d628417c2a72a03d8268d6ccb42e3bdd4261a5a18cc4215` | gate de privacidad del repo: 4 dato(s) privado(s) |
| `2026-11-13-clean/commit-master.txt` | 5441 | `febc134488abd88129a93bf1cca2f04c231d09585eb2ee59fbb1344565bca58d` | gate de privacidad del repo: 7 dato(s) privado(s) |
| `2026-11-13-clean/commit-privacy-task.txt` | 5488 | `24d009f3722dc5458dd3586db88b04cf1137795c33419e85f27ce298e3da9033` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/commit-suite-task.txt` | 5388 | `8f3b8536c69ab69fa4f63bf1258dced7ba4e831e3d2b2add06d0048927e37fb8` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/deepclean-final.txt` | 426 | `ff2b6fdaf9b0aae637c3e497148a81d96d53eeff09e64af289b07c0774238531` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/deepclean-negative.txt` | 543 | `f1720c54e6d25ebf57656fcd4b5d3e0d09c712f70e82a744d8492fdb41a46f60` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/deepclean.txt` | 426 | `dc00f1a0db15f61ba73adc9781e17ef8d8ab157b4789c83a681a9a1be32a6e16` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/diagnose-after.txt` | 2400 | `1dd0139c90c318a24a3d4da50d7106fe8ed0020aef01bc3850520e19514738f6` | gate de privacidad del repo: 8 dato(s) privado(s) |
| `2026-11-13-clean/diagnose-before.txt` | 2549 | `60426ea59c3531e31916c6e83feb3e418d5660548315f853e29956f39569b305` | gate de privacidad del repo: 11 dato(s) privado(s) |
| `2026-11-13-clean/diagnose.raw.txt` | 2069 | `edd1d6c3aa07c469a3cf04ba638cfeb5b531119e2fae361b0b57134e050e77d0` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-clean/gateway-negative.txt` | 5284 | `ae8425ce1ec0d8a65f6708800bd2ae2cd177c31241a145765c220c8616029118` | gate de privacidad del repo: 17 dato(s) privado(s) |
| `2026-11-13-clean/guard-controls.txt` | 958 | `8fa3eb0318c1b58bafd7c2a22743602f09966a461717cc37d952e29c78aaa957` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/h3-resolucion/control-identidad.txt` | 190 | `4696fb24a71748504625630e600ccebb4f4a52ee258d97d11e69b69e003cb79b` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/inspection.json` | 5575 | `21b6cc9704a63f3549b6c370981e92d5692bd3093a0bc4fe9582459fe060e45a` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/instrument-recheck.txt` | 475 | `7688bdf691a67f0498e426b77e00aaefac2a9e0d036c179e88f07aef952af846` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/orca-guide.json` | 34802 | `f0125a72526d3a665daa210441230a30af8026495e043bb45337bcaefd100b2f` | salida reproducible de herramienta externa (guia del CLI de Orca), sin estado de trabajo |
| `2026-11-13-clean/privacy-baseline.txt` | 943 | `7432e1fbc5184b8c49dcf52014e9f0a9fe0e5159b3361ac384915bee0ac0c854` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/privacy-counts-history.json` | 6394 | `6f16f8e40db3624e999b219121cb7ffe6982710c12b1bd3d09686ffc18a5a8ef` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/privacy-counts.json` | 3539 | `0221ac5fad915b3a3b316bb7aa08311c18711bd6046ed5d3be76860872f4473c` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-clean/push.txt` | 4217 | `d77d8596df871740b25dd56b8cdfb53f8dcad3313918002074a95918da7ebeb4` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-clean/refs.raw.txt` | 3865 | `1f86c941599c8e6ad678e9a785369a27d0d55755b6b89445b5f9b96cf794b5dd` | fila pii-staged del pre-commit: 1 falso positivo (un SHA de git leido como dato personal); no se evade el gate |
| `2026-11-13-clean/refs.txt` | 3865 | `1f86c941599c8e6ad678e9a785369a27d0d55755b6b89445b5f9b96cf794b5dd` | fila pii-staged del pre-commit: 1 falso positivo (un SHA de git leido como dato personal); no se evade el gate |
| `2026-11-13-clean/remove-worktree.txt` | 96 | `270456d586cec4ef71662611ee18119f193b4c6c2538facab2d57bcaa92dcbca` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-clean/sessions-after.json` | 2230 | `4ab5e0a56f164a011cb80bdb28f4304b83dd97b3756a60b0f16cc801aeae0ebf` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-clean/sessions-before.json` | 2537 | `e284e77bc7e9dea5da0c53e2ad852b8c3f7d58212a6bd03f001b070b88ad4bd3` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-clean/suite-after-h3.txt` | 34535 | `70091f7321a204945642980aa50b325b3bf74f7178f35aca0462250a78a5b0ac` | gate de privacidad del repo: 52 dato(s) privado(s) |
| `2026-11-13-clean/suite-before.txt` | 29097 | `2d740056b4b4fba4a71e8ba80531877eaee0d25b8b41f2d561425eda3ffb1f22` | gate de privacidad del repo: 20 dato(s) privado(s) |
| `2026-11-13-clean/worker-historical.raw.json` | 5884 | `8a71c3931f86d70614e25fae77f990655c3102297e5c92dab99d7f41437e1a84` | gate de privacidad del repo: 6 dato(s) privado(s) |
| `2026-11-13-clean/workers-final.raw.json` | 248060 | `d16b5d188036036abde76f6a483b1527b530423adfb515405ea5923b11b599f8` | gate de privacidad del repo: 311 dato(s) privado(s) |
| `2026-11-13-clean/worktrees.raw.txt` | 114 | `eb4fb6a05c26daea5880e86e72a1123928b03e4d5f08634c068b10c7221bf969` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check-r2/acceptance-tests-final.txt` | 2825 | `642bea7085b44c68a5870753481ac4a6285db63d409706c269201b3119c56c62` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-close-check-r2/acceptance-tests.txt` | 1559 | `56e9a3aff72b9da3ec95935e86ff78287afef63119f07b4cb2238a66c833ff05` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-close-check-r2/canonical-acceptance.txt` | 2566 | `899626c7f5ea71a31a72963bd4fba1b981ec13dfc276a7c6c24514f48a82383b` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check-r2/commit.txt` | 9751 | `afbf05dc0207f0dc81c6c0cdaba7579a079455b09194b488a6b4b8940fa5315e` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check-r2/measurement-r2.raw.NO-PUBLICAR.json` | 4269 | `10545abc47f6ee171fef6a9c592f112e2e21bb2090b154ef99a08cb225ec45b0` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-close-check-r2/negativo-detector.txt` | 1747 | `13ab82861e5df2cee7a5a4a641ae5468cf80b3319626729827dab5c761c60cbe` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check-r2/negativo-git-presente.txt` | 1527 | `0056355b0196b00440f6b75ebd1f59547e9095235a79c83a45b3c2bb52a8dd2e` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check/aceptacion-roja-final.txt` | 10820 | `f298133e7ac72dffed0b56b3626d6d98b17660b58db38b054500a57fbd83da65` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check/detector-retirado.txt` | 1450 | `0a633271d5fb80db61b079968757f15bdc7552aeea2f167327182b28301827ca` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-close-check/gate-commit.txt` | 6786 | `7e771ae5f25e173ec2eafcf8cea9f26e884f49d739ecc412821dbaf827af3b36` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check/materializacion-commit.txt` | 8082 | `6c5d58960e0e4e6a7869be255864417531cc4b12b4598a4f083d7292e6ae9822` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-close-check/runner-actual/.simple/state/a8feffef481ff1a4fec812fb24829d4260d1a94d68608faeb8530e8d115b6cc2.json` | 982 | `e7d2bed4eae5eb64c122e019e2e1881491ce8b702420b7c34de262cea4e419f7` | git ya lo ignora (nada que git ignore entra) |
| `2026-11-13-close-check/runner-actual/.simple/state/timing.json` | 18 | `41a4e7de513332161bf23bd335f1b71f9bf40348f48cd038621b603239856f76` | git ya lo ignora (nada que git ignore entra) |
| `2026-11-13-corredor-conciliacion/EVIDENCIA.md` | 33843 | `36bbd2bd6ed3589ef02f236f675b6a5356310d75368ee5cb1f015e07b22b78c5` | gate de privacidad del repo: 72 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/INFORME.md` | 9242 | `650e80fe9ef5208a720f128c66986165f11762d10d517b04370cf4abb80aae04` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/commands.json` | 50135 | `4a91c2a136b69e85365f2a3cbb4c6c9fe54138325a9bace9577804a2e6002ff1` | gate de privacidad del repo: 139 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/metadata.json` | 2027 | `ebd8dfa7e277c96fffc3e0380c721a3739da7d0cb484574d7d90eaf4b2ec3333` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/run.py` | 5986 | `f590553ee864bf2368af1cfef4101cb9f9eb30eff10366de888212b67d7e33cb` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/sujeto/docs/probe.md` | 44 | `8b21de065e1f23cad664ed93a13062be61be27297a4d0115bcf51c4058d62086` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-corredor-conciliacion/supplement.py` | 4262 | `5748907f87c41edd66acbc71cce4bc9df232a0b545daa419b25a49a30d05bcb4` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-deepclean/MANIFEST.tsv` | 559 | `e9bb05fe9b1c0e362c8e77f5328cd41da047a52d4cab50b0b040f58859b80755` | gate de privacidad del repo: 9 dato(s) privado(s) |
| `2026-11-13-guarda-28/evaluacion.md` | 29591 | `7fdb80d469113f8a875972d5244449ca0d68705b6333f3ddb590be3777156b1c` | gate de privacidad del repo: 9 dato(s) privado(s) |
| `2026-11-13-lectura-backlog/clasif.py` | 4259 | `efa5ecac00edc18a896eef6c98922f938275f171784b407607bf4d460ca9783b` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-lectura-backlog/informe.md` | 10988 | `e1d437c81d4927b908ba6f054d60603f8658e1020878d394a65a928e454ec756` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-reescritura/valores-a-purgar.NO-PUBLICAR.txt` | 2558 | `a1158a4eba6df17d82a2306a6121e32ebc697d367e15182c42f00df66a2681df` | gate de privacidad del repo: 78 dato(s) privado(s) |
| `2026-11-13-remediacion/base.py` | 1370 | `51c1850cb4a071f350f5b64ceaa06564a484619266b894a0ad7ee65f23a9361a` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-remediacion/clases.json` | 1277 | `34cf12e81d167fc982039124fd50d4061e1a46869220a01973cda9eaeacbedab` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-a-retry.txt` | 3325 | `9034765c8861410340c01cf09c221f346e6c6a4f56408ad671ddd3d0c40da2d5` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-a.py` | 894 | `fb90dcc923cdfedb3c703b813eba305ac75cb14842794c77035fa33cd4535efb` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-a.txt` | 12228 | `6b4aa2d109386abe06a2c0f8c8ba8c951429bf9447aa98660a8e276f6a07b26f` | gate de privacidad del repo: 7 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-b.txt` | 5235 | `d0540e20a8aa9470173853746ffd3441140eefe64a0c5679235f5431492d3079` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-conciliacion.txt` | 5386 | `94713f8af563f48a8c6d2577e022f2140170f137fc8152bdd74cb9b897c9c607` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-correccion.txt` | 5368 | `a5c112be1e05a57a9f72efca71da761dd75db1e64520000e6558d65a6c935a5a` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-ficha.txt` | 5394 | `647e5327039aabacb9649b2dbbc413c17a596c21d8bbfc235c1015a6db8bb085` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commit-gate.txt` | 5570 | `e5ef725de18270db08265ed5404d030ad4da4d9d71d861e92a0b4bfd4d2126fe` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/commits-revision.py` | 1521 | `b9a9443f386572ab35e58a2fed49b78fbeba35e0601c310926c4faaefa335b1f` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/comparar.py` | 857 | `364f51450efd0f5386452e091fe41f1498f430ce7bd6127d6916f003cf0c60ac` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/config-red.txt` | 2350 | `5af9fdacb483299a9cee1385d471ba173e1df058a232fa0ac491d0e5c96821ce` | gate de privacidad del repo: 12 dato(s) privado(s) |
| `2026-11-13-remediacion/control-revision.py` | 1300 | `816006d5add2d40306d1d4e38fcd76747f9b3ec6afa84b37e50ee25d2a1768a6` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/control.py` | 1295 | `53e50f476f9478873e203da95bca8ba5337acbb47d1be2d4730be49a378a4287` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-remediacion/corregir-revision.py` | 8015 | `57fe7b3b99ebe604ffc4faac5ae6a528e34b6b17c13be2981e11820824b4f8ad` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-remediacion/documentar.py` | 4988 | `b12fcb64d9da733ba88edbd19fe8c80ebdfa8a5acb41ff89831ffdbc3f7ef4a8` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/gate-corregido.txt` | 4823 | `a875aa92e20450318de9ac9fe3a3711c45d63b12b68b16d7802ce9cffd42f27e` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/gate-final.txt` | 6001 | `00e1cc1cf29fc039130ef5ccf4f9de8a9805763c5dd0725d366b3e3bae78877f` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/historia.py` | 1769 | `f4f5abdb7fa37e2e46f7457eb12c5cc052e41428b1d4b51085957870ddc69bdd` | gate de privacidad del repo: 4 dato(s) privado(s) |
| `2026-11-13-remediacion/limpiar.py` | 3669 | `f05e0dda6a55cb3aa14842497804dfc2f5c173a72c0d8bf5c75dc87b330d8cf9` | gate de privacidad del repo: 5 dato(s) privado(s) |
| `2026-11-13-remediacion/marcar-historia.py` | 1279 | `a1ca8f395fbd2ab71dc67d845b591d6533c4ce684c128fc46d32869ef4092b90` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-13-remediacion/push-normal.txt` | 9364 | `9244587202589176badd01b1b2a84830717a10f2f087b1e1d46a824c96916291` | gate de privacidad del repo: 6 dato(s) privado(s) |
| `2026-11-13-remediacion/reporte-revision.py` | 6732 | `c4109937fa0fa2c858a8be501ae29a96cca0b721d2aac261bc70e1bf8d907220` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/reporte.py` | 7160 | `9e84af969d442d3e9ea5fae28020fb590cba09fb1843543eb720c5dc19794191` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/revision-emergencia-commit.txt` | 6524 | `a22c8df94418e46f809f187ff9862100c7b70afa6ab37244050a0fbde85b57bf` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/revision-ficha-commit.txt` | 5391 | `d7bcaa874511e0258da40e5482c7e52cbbdc9ce1f3d623469e013644036e78ec` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/revision-inventario-commit.txt` | 7027 | `532803d364705726d43ebe7b7ebdeba848d773c94be5c99602024d6e5bb490c5` | gate de privacidad del repo: 14 dato(s) privado(s) |
| `2026-11-13-remediacion/revision-red.txt` | 6362 | `e52e1e3c27a91db72b438e02d34c00b98055f9475461dd5da0975879a4237523` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-13-remediacion/revision-snapshot-commit.txt` | 5358 | `53a70d8be464d162c22e2f29787a8ca9ed14f33225eb0295cbaf160f5a78dc06` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-remediacion/suite-revision.txt` | 29985 | `077186f063916f3a978f683343b3d17efb0921abef55d941fab22d7c5ccf2f00` | gate de privacidad del repo: 23 dato(s) privado(s) |
| `2026-11-13-remediacion/suite.txt` | 28127 | `c036e9929f0c9edb7af1fad8fe49cafc0dc6a4ef5f6f090eb21076d1bcd47f04` | gate de privacidad del repo: 19 dato(s) privado(s) |
| `2026-11-13-revision-claude/REPORTE.md` | 10380 | `5df41233bdb1df84028e7114dae7ff0ed3716def1f9abc99f6d2159fad8b8c6a` | gate de privacidad del repo: 6 dato(s) privado(s) |
| `2026-11-13-revision-claude/busqueda.json` | 114233 | `a5c9956ccbc8cf26332c7fa82218f182807c5368a760b11c8749e1a64ea1549a` | gate de privacidad del repo: 4 dato(s) privado(s) |
| `2026-11-13-revision-close-check-opus/fp-@PRIV@.txt` | 4698 | `b53115d84db1c184d29486de8f89ae5ae727f6a5f3b5c492c61ba7809226bb5a` | gate de privacidad del repo: 13 dato(s) privado(s) |
| `2026-11-13-revision-close-check-opus/fp-simplecode.txt` | 601 | `7d571330dd16993486d6a8f684056e578fe3be88bf585689161d7e9b9ca0a80c` | gate de privacidad del repo: 5 dato(s) privado(s) |
| `2026-11-13-revision-close-check-opus/informe.md` | 8780 | `c9136108762c2defc45a6aa251d5fb73599aafbc5320c211e210ee2a0b9151a6` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-revision-close-check-opus/patch.sha256` | 201 | `b3188157b0a8962a2d73b09e99754d6a9dc16699cf83ad37cd50c0a0bb5d8b46` | gate de privacidad del repo: 1 dato(s) privado(s) |
| `2026-11-13-revision-close-check-opus/revisor/test_revisor_enforce.py` | 3830 | `5f0619f132c2cd0eb7d600e5a8fa92bfbeee2e256226a419f9fe6dd74bb8ff14` | fila ruff del pre-commit del repo: S602 (subprocess con shell=True) en la linea 62; el archivo no se altera ni se silencia el gate |
| `2026-11-13-revision-final-claude/INFORME.md` | 9997 | `7be713d590747d0233a97b14f0e822e6dfaabcf40d3bd788a68a98ddbc65ffae` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-15-deepclean/MANIFEST.tsv` | 130 | `3424cba4e63525dd3acc8b12a153862d0324516498c2fdd92b3e88317db35513` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-16-clean/INFORME.md` | 10143 | `d63d0423ba40f039d34d9adc20666a98bbf8dfd5a6f50e2255bb317a1cf1a595` | gate de privacidad del repo: 10 dato(s) privado(s) |
| `2026-11-16-clean/diagnose-1.txt` | 2465 | `791126a98dddb1d80e844b5d291367a766420bd780475319429fefeaa9eac2cd` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-16-clean/diagnose-2.txt` | 1825 | `685b44d81c3354a148aa7a273c6b6ed368e5105d131003355b02703e60158726` | gate de privacidad del repo: 3 dato(s) privado(s) |
| `2026-11-16-clean/orca-ps.json` | 105430 | `1948cc014dcfef6248cdb1143fe01a7540cc002b2df3099ab9a65a272b386566` | gate de privacidad del repo: 158 dato(s) privado(s) |
| `2026-11-16-clean/to-push-2.txt` | 567 | `d6b9c573b3306423d8e93f6be03aff55eae0bc90ed5aefe2cf0d33f8d71d0d17` | gate de privacidad del repo: 2 dato(s) privado(s) |
| `2026-11-16-clean/to-push.txt` | 397 | `85ae0ea0bb84326544b413435e000cf1ff7c2562c5e5ef8dd105ee6565e18ac2` | gate de privacidad del repo: 2 dato(s) privado(s) |

## 4. Unidades no copiadas (directorios)

Digest de arbol = sha256 de las lineas `ruta-relativa<TAB>sha256` ordenadas. Una copia de arbol contiene un repo completo (blackbox o el de su dependencia de hooks) en un estado de prueba; un tmp de pytest es el basetemp de una corrida.

| unidad | archivos | bytes | clase | digest de arbol |
|---|---:|---:|---|---|
| `r13/suite` | 15971 | 381202262 | tmp_pytest | `09142f1f29d306a6f9857ceed42930db07a35b01a70b6f85557af9cdc734227e` |
| `r13/suite-revision` | 16081 | 374789722 | tmp_pytest | `747d92f5bb78906e44b9057356c26f260023144cfe8945780a226419c766f950` |
| `2026-11-13-clean/pytest-after` | 15963 | 296972635 | tmp_pytest | `9193cb056b49c4d2738f7d982a3434267fe4ec4c9cfe4a14dd22a0eea6ef1021` |
| `2026-11-13-clean/pytest-before` | 15965 | 296591813 | tmp_pytest | `42ad91a5b35381ab275be21b27e7018ac4d0551415ca1a6f721ba2306b089106` |
| `2026-11-13-revision-claude/clon` | 8897 | 141359183 | copia_arbol | `da948b673e6acc409fe98d21e1ab5589934cf7bb193ccbf6cf01138489ce43ac` |
| `2026-11-13-revision-close-check-opus-r2/runner` | 9024 | 141207466 | copia_arbol | `83132558320b6bb29a17a551b11d0e16d8828d9ab49dfae748b201676a2594ca` |
| `2026-11-13-revision-close-check-opus/runner` | 9028 | 141165311 | copia_arbol | `f55281054c157526d4288a5387c941f0a00eefd66844a7b910bf36f4b887c951` |
| `2026-11-13-revision-final-claude/clon2` | 8963 | 141099597 | copia_arbol | `4fa4aa5d0ed5d834459989164e0d1447188cd62eb05362055ebcbc17e7553a2e` |
| `2026-11-13-revision-final-claude/clon` | 8952 | 141093483 | copia_arbol | `09eb1f878e7e8423ed339bc162f55d353d36e0431b737c4e1c16537c90dc355c` |
| `2026-11-13-revision-final-claude/clon3` | 8964 | 141084226 | copia_arbol | `15f0e76735bc03247b560ab433a6de1aa0a180fae1b358c7a1401a6215ff3b85` |
| `2026-11-13-remediacion/control-revision` | 8951 | 141069424 | copia_arbol | `7c3cbd9f7933c22d1c63fcbecde570395dcb575a3a72a70ddf3ab59ce0ab2fa6` |
| `2026-11-13-revision-claude/clon2` | 8897 | 140882511 | copia_arbol | `ba19266b8f0e46cdbccbd2dea1eb0a01258375da848d1ab82f6e4b7b10cf8e56` |
| `2026-11-13-remediacion/control` | 8897 | 140881559 | copia_arbol | `b9823fa88880cbe345dbee75c3b2cc82dfc686dffb1ff6c345e495561948199b` |
| `2026-11-13-revision-claude/previo` | 7114 | 46826509 | copia_arbol | `bb1efc9c194ef34ef72943f708f46341d989a06c52060ec31e9eb23e3418999a` |
| `2026-11-13-clean/baseline` | 3670 | 37151246 | copia_arbol | `3a478789df46d134e00df3c57ca977d120912adef005a39afe65282399d577d7` |
| `2026-11-13-clean/h3-resolucion/head-con-test` | 3671 | 36684099 | copia_arbol | `482b26f9596cf83aa3c60a57c1e2919a1c95c60825aa7517cf7d3b2a1b76621d` |
| `2026-11-13-revision-final-claude/noRepo` | 3654 | 36646901 | copia_arbol | `7841de050835c92f6771bb694619dd8450be1531ddf629cfb7cdd82e28711b26` |
| `2026-11-13-revision-claude/arbol` | 3652 | 36630182 | copia_arbol | `912d3ae236911e33fd676523cc1805c146f70071bc57ffb6c5947b3034c1bef0` |
| `2026-11-13-revision-final-claude/bt` | 2490 | 3696799 | tmp_pytest | `26531035b8335237615cd08c45b97e97544941cc2640812298bc9d526b9d63c9` |
| `r13/revision-focal-final` | 2375 | 3608160 | tmp_pytest | `cde1b9af7f669eb53d772836811d2f49e6a365e75a6436e4dde18a36f7904e82` |
| `r13/revision-green2` | 2366 | 3606339 | tmp_pytest | `cd2ef4716f52d99c242c70b5848be1e396512fce92f642cf1181f2184c87ea8e` |
| `r13/revision-green` | 2366 | 3606144 | tmp_pytest | `80df44edb25977415981b2061fef207c9eb34bf02810115daa249fd355c1d28e` |
| `2026-11-13-revision-close-check-opus-r2/sc` | 353 | 1752730 | copia_arbol | `0b9928738cd2ffd6f688738e26c68698de1d1ec97737203924c47f14d41a20d9` |
| `2026-11-13-revision-close-check-opus-r2/p1` | 158 | 1270963 | copia_arbol | `a3702fbae4645b63653a9f551d06d8c3fc0298c84cd7590d8e4e92a47cb085f8` |
| `2026-11-13-revision-close-check-opus-r2/n3` | 158 | 1270819 | copia_arbol | `5ca9b4b3c66d325aec93bab7ad6950e59a4af1b25fae70792c10ea26f60b106a` |
| `2026-11-13-revision-close-check-opus-r2/n1` | 158 | 1270792 | copia_arbol | `87e9238222eea2b0c491742893639424f0bc0b9c308f91b0cdefc9bbe7098526` |
| `2026-11-13-revision-close-check-opus-r2/p2` | 158 | 1270782 | copia_arbol | `41f3380759b4fa38f334f21abf3115195e142ff291d7a3a313deba9bfd3e7791` |
| `2026-11-13-revision-close-check-opus-r2/n2` | 158 | 1270718 | copia_arbol | `3cc7c0511d576353f00c7c4ae6196b709ce893f7a2efe0ac252e68117792215d` |
| `2026-11-13-revision-close-check-opus/sc` | 269 | 1239928 | copia_arbol | `53b60d5d7d4964efe1bf7865562fb214fd07bc16edd4a3b8d3f8b7312defed12` |
| `2026-11-13-revision-close-check-opus-r2/bt` | 1404 | 1129738 | tmp_pytest | `3f016579876c75f57185b7521626d230927d10757a58b47188affb8ee7164458` |
| `2026-11-13-revision-close-check-opus/sinbarrera` | 118 | 882505 | copia_arbol | `a03811c4a68fd9ca2fd91d4e3ffdb39cf102489eb705c963583d951314268759` |
| `2026-11-13-revision-close-check-opus/gitpresente` | 118 | 882489 | copia_arbol | `fc398ee5a8a0223d6bcd2eb7e9ee0624e10d80308edf576315177ec8820944bb` |
| `2026-11-13-close-check-r2/candidate-simplecode` | 62 | 439761 | copia_arbol | `0aa14265dedf0d5b6c9a04bc12a0c1560adbcd63b5b971a229045bc852d82ad4` |
| `2026-11-13-close-check/simplecode-propuesta` | 60 | 434786 | copia_arbol | `881fa5e535fea94da9a31847497de01bd0dcf6e322d09cc626dfc3f7524ca69a` |
| `2026-11-13-close-check/simplecode-sin-detector` | 60 | 434551 | copia_arbol | `d3c0896e1879321c5f73c0384c60a70bbc2b4cf98c34715b1bd620be91da8c15` |
| `2026-11-13-revision-close-check-opus/orig` | 58 | 425491 | copia_arbol | `28867b3cd3f2722dd38f802a544a0c21eaf858df51991caf7d4411ea4e0b4065` |
| `2026-11-13-close-check-r2/sin-detector` | 58 | 425250 | copia_arbol | `6a08941e7b811e2edba9da0642e9b6d0209b9bc20a84d5188c814fc1b8469102` |
| `2026-11-13-revision-close-check-opus/bt` | 526 | 418976 | tmp_pytest | `52793cb7867c26a2fda3f96a285dd35296110c0239d5d0a5da5fdb9a725103cb` |
| `2026-11-13-revision-close-check-opus/pytest-of-@PRIV@` | 186 | 264839 | tmp_pytest | `ab22227d629c9fa98b63ddb1098bffb176a10c8b2cfd8c93470b62f449765b1d` |
| `2026-11-13-revision-close-check-opus-r2/pytest-of-@PRIV@` | 195 | 216096 | tmp_pytest | `5e0d07bd5ab72601d98864c11bb21187599762927bfce4bc353efd53a6826405` |
| `2026-11-13-remediacion/focal` | 422 | 203675 | tmp_pytest | `ba2089c29e662ad928129c58d1d3744e4eb0659758b15ee87cbe9ff37a5e23df` |
| `2026-11-13-close-check/bt-aceptacion-final` | 93 | 132420 | tmp_pytest | `bbbefcefc7802cd89b61e3fb8a8170a7da43d8be5d94107f9e6dea5114c73e20` |
| `t/base` | 3 | 119422 | tmp_pytest | `4f72bad97d59415b26bde2000c0177a5c260d846f9cd92c1b064a2ce423564dc` |
| `2026-11-13-close-check-r2/bt-measure` | 142 | 113274 | tmp_pytest | `d668fb8c5f59057da5bcedfce876b6363afead8f15bdb13276438f2414d928bb` |
| `2026-11-13-close-check-r2/bt-measure-final` | 142 | 113271 | tmp_pytest | `ce275fd345c67a9856cdd965318658cd9e407b2274cf759ae6e479bb708c6371` |
| `2026-11-13-close-check/bt-policy` | 143 | 112373 | tmp_pytest | `463a0bd86a8378cf82887e4b642136bd45634605508b881d8237806472624960` |
| `r13/snapshot-both` | 224 | 92403 | tmp_pytest | `750d3e716780905bd5b5103f2fb3c5eb04b198e73667409caa88a1e6a074868e` |
| `2026-11-13-close-check/bt-aceptacion` | 62 | 88303 | tmp_pytest | `2ac69e3b1423798904dc5104b5e89195fa6bc7aa74cf419a98cde89f57294a7f` |
| `r13/revision-red` | 97 | 82031 | tmp_pytest | `22900377b50987d7e09d583de872a06264055019ce8078a6433d15fb4db98e1a` |
| `r13/revision-red2` | 97 | 82031 | tmp_pytest | `b6c668de5cf0cfaf1bb979d9de4e4f3dd74c611e320a681fa091379ede672fc9` |
| `r13/snapshot-final` | 97 | 82031 | tmp_pytest | `f1d73b4ba10dcb7d5cf671bd4d56e29d9ccc594bd00a869507f2c701fc0ec8ac` |
| `2026-11-13-corredor-conciliacion/sujeto/.git` | 53 | 40751 | git_fixture | `25f70a90928d7c744d4c35a2abd27753dd29f2370bcb410f8bca0abd9f925789` |
| `2026-11-13-close-check-r2/runner-report/.git` | 38 | 29734 | git_fixture | `d4660dbb2a6293786415e6ae53b4fc6317f6a861ba9c5017033a6b02d8235f29` |
| `2026-11-13-close-check-r2/bt-acceptance-final` | 34 | 28095 | tmp_pytest | `73bea61f4aba3e0dfcc2fa67d140f5ddfa07b123d241e5657a9aa9c2ad139bfc` |
| `2026-11-13-close-check-r2/bt-acceptance` | 34 | 28094 | tmp_pytest | `ec55eee6f8cf25d81b2c3877e714258656a27703c20a8f7f4ec3968ac4f83c42` |
| `2026-11-13-close-check-r2/bt-acceptance-final2` | 34 | 28094 | tmp_pytest | `9011e23167019b2eb3392c56ffe70c11747610b8719182de3c75b2be584e319b` |
| `2026-11-13-close-check/runner-actual/.git` | 26 | 27166 | git_fixture | `1807f7f3817bd41c14c045fa8147e97d703247fb7822ca297a3d4bed94c1e756` |
| `2026-11-13-clean/negative-deepclean` | 18 | 26249 | tmp_pytest | `5ec896efe9ee9f870488066d1b3239bcd53ffc17ad18e3e9e1fdc10c6b640b05` |
| `2026-11-13-clean/tmp` | 34 | 21526 | tmp_pytest | `c46a07ea9c638421b7f307334609797c0f3d8c8c1df871271d4a5d286e047fa5` |
| `r13/pytest-of-@PRIV@` | 30 | 21319 | tmp_pytest | `1549c3033723ac7a3bef2b5332ea33e16c375329678b1e4e10eb2828225af310` |
| `t/pytest-of-@PRIV@` | 22 | 20754 | tmp_pytest | `a025c1846066588994fe5f0f01bbf0d8d4255d13f7efeb5e56e65823ebb08a2a` |
| `2026-11-16-clean/negctl-gateway/tests/__pycache__` | 1 | 15806 | tmp_pytest | `93c03aff4214ab2bfa1155ebd2f50febfe2aa2cb172e050d1728ab9b4ae45f83` |
| `r13/inventario` | 118 | 8644 | tmp_pytest | `9d829c0fad4f27955c9057d30ed9d9264bcd12762beab5f689a7ff8cf7ff4742` |
| `2026-11-16-clean/negctl-gateway/tools/gateway/__pycache__` | 1 | 330 | tmp_pytest | `c3076ed10d3bffb9cde1503a6379b4b4027c6cd49d67a133be8727d7c9fe87b9` |
| `2026-11-13-clean/pytest-guards` | 4 | 206 | tmp_pytest | `d1622654ab92fdee57f5a9d1a76f46a5b8b900b1a20b552fa770301c56532a48` |
| `2026-11-13-remediacion/red` | 2 | 79 | tmp_pytest | `0427f42468692e3bfe23d1a4227c707e8c08e11db8e85a6f1f2f9e719e68308b` |
| `2026-11-13-remediacion/focal2` | 2 | 79 | tmp_pytest | `0427f42468692e3bfe23d1a4227c707e8c08e11db8e85a6f1f2f9e719e68308b` |

Commits que existen solo en estas copias (medido con `git rev-list --all` contra `cat-file -e` en el repo): 8 en `2026-11-13-revision-close-check-opus/runner/sujeto`, 2 en `...-opus-r2/runner/sujeto`, 1 en `2026-11-13-revision-claude/clon2`, 1 en `2026-11-13-remediacion/control`, 1 en `.../control-revision`, 2 en `2026-11-13-revision-final-claude/clon2`, 3 en `.../clon3`, y 3 y 4 en los fixtures `corredor-conciliacion/sujeto` y `close-check-r2/runner-report`. Por su asunto (`planta`, `sanea`, `plantado`, `contrato ...`, `test: control negativo sintetico`, `Fixture ... synthetic ...`) son commits de control negativo o fixtures sinteticos, no trabajo candidato; solo se leyeron los asuntos, no los diffs. Por eso no se exportan.

Los arboles `candidate-simplecode`, `simplecode-propuesta`, `sin-detector`, `simplecode-sin-detector`, `p1`, `p2`, `n1`, `n2`, `n3`, `sc`, `orig`, `sinbarrera` y `gitpresente` son copias del repo de la dependencia de hooks, no de blackbox; su delta de candidato puede estar en `close-check-enforce.patch` y `candidato-staged.diff` (copiados, seccion 1) y en `patch-r2.patch` (ya en el repo, seccion 2). No se verifico que esos parches cubran el delta completo: pendiente.

## 5. Archivos de mas de 2 MB (todos dentro de unidades de la seccion 4)

| bytes | apariciones | ejemplo |
|---:|---:|---|
| 32921989 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-1096173fa1e053b1ab216780490a0676925a98a4.pack` |
| 20449906 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-dd04788a82aecac21430462d50c553500ac031d0.pack` |
| 16777217 | 4 | `2026-11-13-clean/pytest-after/test_cgroup_malformed_nested_j0/evidence/capture.json` |
| 8760442 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-56ea0dc72429eb4dc95bc270d3b1aa46a508ea8f.pack` |
| 8388928 | 4 | `2026-11-13-clean/pytest-after/test_el_log_del_portero_tiene_0/portero.jsonl.1` |
| 8388609 | 24 | `2026-11-13-clean/pytest-after/test_signature_input_unavailab2/input` |
| 5103734 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-f8aa2cb7d943a76b496c99242e53d2a5857a6233.pack` |
| 4392562 | 1 | `r13/suite/test_debt_sunset_test_bb_bash_4/mutant-counter/sigterm.jsonl` |
| 4390966 | 1 | `r13/suite/test_debt_sunset_test_bb_bash_4/negative-counter/sigterm.jsonl` |
| 4383612 | 1 | `r13/suite/test_debt_sunset_test_bb_bash_3/negative/sigterm.jsonl` |
| 4368828 | 1 | `r13/suite/test_debt_sunset_test_bb_bash_2/rate-mutant/sigterm.jsonl` |
| 4361729 | 1 | `r13/suite/test_un_contador_que_RETROCEDE0/blackbox/sigterm.jsonl` |
| 4358130 | 1 | `r13/suite/test_debt_sunset_test_bb_bash_2/positive/sigterm.jsonl` |
| 4355569 | 1 | `r13/suite/test_control_negativo_sin_traf0/blackbox/sigterm.jsonl` |
| 4349463 | 1 | `r13/suite/test_swap_mide_el_RITMO_no_sol0/blackbox/sigterm.jsonl` |
| 4194305 | 28 | `2026-11-13-clean/pytest-after/test_reader_bounds_raw_json_an0/large.json` |
| 4194304 | 64 | `2026-11-13-clean/pytest-after/test_control_un_destino_udp_in0/anillo.bin` |
| 4081668 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-ca0755fe8ba224ce78de605a4e5d9b1584dce1ba.pack` |
| 4000001 | 4 | `2026-11-13-clean/pytest-after/test_wifi_reader_is_bounded_st0/oversized.json` |
| 3529839 | 9 | `2026-11-13-revision-claude/clon2/.git/objects/pack/pack-e6393a82072cb03a484222039911feacccb7d024.pack` |
| 3049290 | 1 | `r13/suite-revision/test_debt_sunset_test_bb_bash_4/mutant-counter/sigterm.jsonl` |
| 3048581 | 1 | `r13/suite-revision/test_debt_sunset_test_bb_bash_4/negative-counter/sigterm.jsonl` |
| 3048344 | 2 | `r13/suite-revision/test_debt_sunset_test_bb_bash_2/rate-mutant/sigterm.jsonl` |
| 3048109 | 1 | `r13/suite-revision/test_debt_sunset_test_bb_bash_2/positive/sigterm.jsonl` |
| 2989876 | 1 | `r13/suite-revision/test_un_contador_que_RETROCEDE0/blackbox/sigterm.jsonl` |
| 2989650 | 1 | `r13/suite-revision/test_control_negativo_sin_traf0/blackbox/sigterm.jsonl` |
| 2988243 | 1 | `r13/suite-revision/test_swap_mide_el_RITMO_no_sol0/blackbox/sigterm.jsonl` |
| 2690068 | 14 | `2026-11-13-revision-claude/clon/tasks/evidence/CLEAN-2026-10-03/raw-manifest.json` |

## 6. NO REVISADO

- El contenido archivo por archivo de las unidades de la seccion 4 (copias de arbol y tmp de pytest, 182141 archivos): se clasificaron por estructura y se resumieron con digest, no se leyeron.
- Los no regulares (531, enlaces simbolicos y tuberias dentro de esas unidades): se cuentan, no se siguen.
- El scratch de otros repos (`~/scratch/<otro>/`): fuera de alcance de este manifiesto.

