from pathlib import Path
import json,hashlib,re,runpy
root=Path.cwd();scratch=Path.home()/'scratch/blackbox/2026-11-13-close-check'
source=Path.home()/'scratch/blackbox/2026-11-13-remediacion/pendientes-revision.json';raw=source.read_bytes();rows=json.loads(raw)
assert len(rows)==3 and len({r['id'] for r in rows})==3
spec={
'DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01':('test_error_lector_es_could_not_run','Base ilegible y Git ausente deben ser CNR; hallazgo real debe seguir siendo fail, y HEAD limpio pass.'),
'DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01':('test_dato_nuevo_en_guarda_no_queda_exento','Dato nuevo en el archivo de la guarda debe bloquear; preservar los tokens firmados y fixtures imprescindibles mediante excepciones acotadas.'),
'DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01':('test_spec_usa_una_notacion_gateway','Tabla y narrativa deben usar la misma notacion del gateway, comprobando el contenido real de SPEC.')}
evidence=root/'tasks/evidence/REVISION-PRIVACIDAD-2026-11-13';evidence.mkdir(parents=True,exist_ok=True);(evidence/'pendientes-revision.json').write_bytes(raw)
for row in rows:
 ident=row['id'];assert re.fullmatch(r'DEBT-[A-Z0-9-]+',ident)
 node,accept=spec[ident];p=root/'tasks/backlog'/f'{ident}.md';assert not p.exists()
 check={'cmd':f'python3 -m pytest -q -p no:cacheprovider tasks/checks/test_revision_privacidad.py::{node}','expect':'exit_zero','porque':accept+' Prueba de producto, no existencia de evidencia.'}
 text=f'''---
id: {ident}
kind: debt
domain: {'DOCUMENTATION' if 'SPEC' in ident else 'SECURITY'}
title: {json.dumps(row['accion'],ensure_ascii=False)}
status: open
severity: {'P3' if 'SPEC' in ident else 'P2'}
origin: measured
owner: blackbox
created: 2026-11-13
close_check: {json.dumps(check,ensure_ascii=False)}
---

## Fuente y evidencia

Generada desde `tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json`.
ID conservado; estado de origen: {row['estado']}.
SHA256 del JSON fuente: `{hashlib.sha256(raw).hexdigest()}`.

{row['evidencia']}

## Responsable y aceptacion

Owner: blackbox; revision independiente antes de publicar el arreglo.
{accept}

Accion pendiente: {row['accion']}

El close_check ejecuta una regresion contra el producto actual y queda rojo
hasta corregirlo. Registrar esta ficha no lo resuelve ni autoriza su cierre.
'''
 p.write_text(text)
m=runpy.run_path(str(root/'tests/test_sin_datos_privados.py'));assert all(m['cuenta']((root/'tasks/backlog'/f"{r['id']}.md").read_text())==0 for r in rows)
manifest={'source_sha256':hashlib.sha256(raw).hexdigest(),'ids':[r['id'] for r in rows],'paths':[f"tasks/backlog/{r['id']}.md" for r in rows]}
(scratch/'materializacion.json').write_text(json.dumps(manifest,indent=2)+'\n');print('items_fuente=3 fichas_generadas=3')
