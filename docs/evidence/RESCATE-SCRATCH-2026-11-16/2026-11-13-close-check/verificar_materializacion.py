import json,sys
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
source=Path(sys.argv[2]) if len(sys.argv)>2 else Path.cwd()/'tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json'
rows=json.loads(source.read_text());ids=[r['id'] for r in rows];missing=[];invalid=[]
for ident in ids:
 p=root/'tasks/backlog'/f'{ident}.md'
 if not p.is_file():missing.append(ident);continue
 fields={l.partition(':')[0]:l.partition(':')[2].strip() for l in p.read_text().split('---',2)[1].splitlines() if ':' in l}
 if fields.get('id')!=ident or fields.get('status')!='open' or fields.get('owner')!='blackbox':invalid.append(ident)
 try:check=json.loads(fields['close_check']);assert check['expect']=='exit_zero' and 'tasks/checks/test_revision_privacidad.py::' in check['cmd']
 except (ValueError,KeyError,AssertionError):invalid.append(ident)
result={'source_items':len(rows),'cards':len(ids)-len(missing),'missing':missing,'invalid':invalid,'duplicate_ids':len(ids)-len(set(ids))}
print(json.dumps(result,sort_keys=True));sys.exit(int(bool(missing or invalid or result['duplicate_ids'])))
