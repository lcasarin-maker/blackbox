from pathlib import Path
import subprocess
p=Path(__file__).parent/'head-con-test/tests/test_gateway_handoff.py'
expected=subprocess.check_output(['git','show','codex/h3-gateway-receiver:tests/test_gateway_handoff.py'])
assert p.read_bytes()==expected
print('copia_sin_alterar rc=0')
try:
 p.write_bytes(expected+b'\n# control negativo de identidad\n')
 rc=int(p.read_bytes()!=expected)
 print('copia_alterada rc='+str(rc))
 assert rc==1
finally:p.write_bytes(expected)
print('copia_restaurada rc='+str(int(p.read_bytes()!=expected)))
