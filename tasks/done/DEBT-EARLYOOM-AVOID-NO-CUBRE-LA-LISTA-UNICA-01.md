---
id: DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01
kind: task
domain: MEMORY
title: "El --avoid desplegado de earlyoom no evita 10 nombres de la lista unica de procesos protegidos"
status: done
closed_at: 2026-10-16
closure_type: fixed
reason: "el --avoid de earlyoom cubre los 24 nombres de la lista unica de procesos protegidos; desplegado por Luis con el script sellado el 2026-10-16, verificado en la maquina (hash igual al del repo, earlyoom active, bb drift sin divergentes)"
evidence: {"pass": "tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/pass.txt", "fail": "tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/fail.txt", "e2e": "tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/e2e.txt"}
severity: P3
origin: detected
detector: {"rule": "tests/test_procesos_protegidos.py::test_earlyoom_hueco_medido_es_el_declarado", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_procesos_protegidos.py::test_earlyoom_cubre_toda_la_lista", "expect": "exit_zero", "porque": "Sale 1 hoy: el --avoid de adopted/system-config/etc_default_earlyoom (desplegado 2026-10-14) no casa con claude, node, cowork-linux-he, electron, chrome_crashpad, Xwayland, init, dbus, earlyoom ni bb, que data/procesos_protegidos.json protege en los otros cuatro vigilantes. Cierra cuando Luis despliegue un --avoid que los cubra (script de root sellado, como el del 2026-10-14) y se re-adopte el fichero; al cerrar, quitar el xfail y vaciar FALTAN_EN_EARLYOOM en el mismo test."}
---

## Medido
`tests/test_procesos_protegidos.py::test_earlyoom_hueco_medido_es_el_declarado` compara cada `nombre` de
`data/procesos_protegidos.json` contra la regex `--avoid` desplegada (sin anclar, contra `comm`, como earlyoom 1.7).
Faltan 10: `claude`, `node`, `cowork-linux-he`, `electron`, `chrome_crashpad`, `Xwayland`, `init`, `dbus`,
`earlyoom`, `bb`. El de mas peso es `claude`: la regex solo trae `claude-desktop`, asi que el CLI de Claude Code
(comm `claude`, medido en esta maquina con `ps -eo comm`) no recibe el -300 de `--avoid`.

## Al reves (lo que earlyoom evita y la lista unica no)
`journal` (cubierto en la lista por el prefijo `systemd`, salvo `journalctl`/`journal-udp-for`) y `antigravity`.
Decidir si `antigravity` entra en la lista unica es parte de esta ficha.

## Limite que no cambia
`--avoid` solo RESTA 300 al oom_score (DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01): aun cubierto, no es una exclusion.

## Por que no se ataca ahora
El fichero es configuracion desplegada como root; cambiarlo es un despliegue de Luis, no un commit.

## Avance 2026-10-16 (todo lo que no exige root; la ficha sigue ABIERTA hasta que Luis despliegue)
- Contenido nuevo: `adopted/pendiente-de-despliegue/etc_default_earlyoom` (sha256 0e8bc5de5b688de3b3a876298458f88096956a3a93ff402bd2900eb37a563733).
  --avoid `(claude|pipewire|wireplumber|dbus|gnome-shell|gnome-session|Xorg|Xwayland|gdm|sshd|systemd|journal|xdg-|antigravity|vllm|VLLM|docker|containerd|^bb-|^(node|cowork-linux-he|electron|chrome_crashpad|init|earlyoom|bb)$)`.
  `claude` y `dbus` sustituyen a `claude-desktop` y `dbus-daemon` (las contienen); los nombres cortos van exactos y anclados
  porque sin ancla `init`, `node` o `bb` evitarian todo comm que los contenga. Umbrales y --prefer iguales.
- Medido (`tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/matcher.txt`): faltan 10 en el desplegado y 0 en el
  pendiente, con el matcher del repo (re.search) y con `grep -E` (POSIX ERE de glibc) de acuerdo; ninguno de python3, pytest,
  bash, sleep evitado; sobre los comm vivos, 0 que el desplegado evite y el pendiente no, y 6 nuevos evitados, todos de la lista.
  earlyoom 1.7 real (`--dryrun`, como usuario) compila la regex nueva (rc 124) y rechaza la rota (rc 6).
- Pruebas: `test_earlyoom_pendiente_cubre_toda_la_lista_y_no_evita_lo_no_protegido` (verde sobre el pendiente; roja sobre el
  desplegado y sobre el pendiente sin `node`: `rojo_y_verde.py` en la evidencia), `test_earlyoom_pendiente_solo_amplia_lo_desplegado`
  y `test_control_negativo_quitar_un_nombre_del_pendiente_se_ve` (10 casos). El close_check y su xfail no se tocan: hoy sale 1 (`fail.txt`).
- Script sellado: `adopted/root-scripts/earlyoom-proteger.sh` actualizado en su sitio (misma clase estatica y mismas pruebas de
  ejecucion sobre tmp_path), de 89fe78da... (lo desplegado el 2026-10-14) a 0e8bc5de...; copia del viejo en
  /var/lib/blackbox/etc_default_earlyoom.<sha viejo>; reinicia solo earlyoom y restaura si no queda activo. Manifiesto propuesto
  regenerado (`--propose`). Pasos, verificacion y reversion: `adopted/pendiente-de-despliegue/LEEME.txt`.
- **La linea que pega Luis**, desde el checkout principal y con esta rama ya en master. Re-aprueba el manifiesto y corre el
  script; si el manifiesto, el runner o el sudoers cambiaron desde hoy, `sha256sum -c` falla antes de mover nada y el `&&` no
  corre el script: entonces se regenera con `python3 -m tools.bb_root_manifest --propose` y se pega su ultima linea con el mismo sufijo.

      sudo sh -c 'set -e; install -d -m 0755 -o root -g root /etc/bb-root-run; install -m 0755 -o root -g root /home/lcasarin/projects/blackbox/tools/bb_root_run.py /usr/local/sbin/bb-root-run.nuevo; echo "0c9f47a49e925e930661d5f544d1a8647cc0e8b3b38c989ee364bcec446c2e2f  /usr/local/sbin/bb-root-run.nuevo" | sha256sum -c -; install -m 0644 -o root -g root /home/lcasarin/projects/blackbox/adopted/pendiente-de-despliegue/bb-root-run.manifest.json /etc/bb-root-run/manifest.json.nuevo; echo "dff36047b6f65450eae60614322ca98b97acfb1c4fc76b7d3d82a4ae12eb1d77  /etc/bb-root-run/manifest.json.nuevo" | sha256sum -c -; install -m 0440 -o root -g root /home/lcasarin/projects/blackbox/adopted/pendiente-de-despliegue/etc_sudoers.d_bb-root-run /etc/sudoers.d/bb-root-run.nuevo; echo "46ec14fbc0e741f54ce025426808210bb0437dccea3eae234c4ff44fa7fc1e93  /etc/sudoers.d/bb-root-run.nuevo" | sha256sum -c -; visudo -c -f /etc/sudoers.d/bb-root-run.nuevo; mv -f /usr/local/sbin/bb-root-run.nuevo /usr/local/sbin/bb-root-run; mv -f /etc/bb-root-run/manifest.json.nuevo /etc/bb-root-run/manifest.json; mv -f /etc/sudoers.d/bb-root-run.nuevo /etc/sudoers.d/bb-root-run' && sudo -n bb-root-run earlyoom-proteger

- Despues del despliegue: `git mv adopted/pendiente-de-despliegue/etc_default_earlyoom adopted/system-config/etc_default_earlyoom`,
  quitar el xfail, vaciar FALTAN_EN_EARLYOOM y re-apuntar EARLYOOM_PENDIENTE / EARLYOOM_VIEJO / EARLYOOM_NUEVO (LEEME paso 4).
- NECESITA DECISION, antigravity (abierta, sin votar). Hechos: 9 procesos `antigravity` vivos hoy; Luis voto conservar el
  editor el 2026-10-15 (DECISIONS.md); el editor lanza pytest-xdist bajo su scope `snap.antigravity.antigravity-*.scope`
  (tasks/done/DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP.md). Opciones:
  A (recomendada) dejarlo fuera de la lista unica y dentro de --avoid: asimetria declarada de un nombre (mas `journal`); coste:
      los otros cuatro vigilantes pueden matar al editor (trabajo sin guardar).
  B meterlo en la lista unica: coste: vigilante_memavail aplica la `unidad` (por defecto el comm) al nombre de la unidad y
      rechazaria el scope del editor, que contiene los pytest-xdist que lanza: una suite desbocada desde el editor deja de ser
      detenible por memavail; ademas obliga a tocar los tres respaldos en codigo.
  C sacarlo tambien de --avoid: listas identicas; coste: earlyoom elige al editor 300 puntos antes.
  El contenido pendiente vale tal cual para A y B; solo C lo cambia (y re-sella el script).

## Voto de Luis 2026-10-16: antigravity solo en earlyoom
Registrado en `DECISIONS.md`: `antigravity` queda en el `--avoid` de earlyoom y fuera de `data/procesos_protegidos.json`. El archivo pendiente `adopted/pendiente-de-despliegue/etc_default_earlyoom` ya es el definitivo; el script sellado no se re-sella. Falta solo el despliegue con root de Luis (ver el comando en 'Avance 2026-10-16').

## Root Cause
El --avoid desplegado el 2026-10-14 se escribio antes de la lista unica de procesos protegidos y no casaba con 10 de sus 24 nombres (claude, node, cowork-linux-he, electron, chrome_crashpad, Xwayland, init, dbus, earlyoom, bb).

## Regression Test
`tests/test_procesos_protegidos.py::test_earlyoom_cubre_toda_la_lista` (antes xfail), con el control negativo `test_control_negativo_el_desplegado_anterior_dejaba_diez_nombres_fuera` y `test_control_negativo_quitar_un_nombre_del_pendiente_se_ve` (10 casos).

## Verification Evidence
Triada en tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/: fail.txt (rojo contra lo desplegado antes), pass.txt (verde sobre el contenido nuevo) y e2e.txt (salida real del despliegue de Luis y verificacion en la maquina). antigravity queda solo en el --avoid por voto del 2026-10-16 (DECISIONS.md).
