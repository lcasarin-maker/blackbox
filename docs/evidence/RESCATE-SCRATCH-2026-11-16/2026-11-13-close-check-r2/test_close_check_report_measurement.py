"""Report-only: Git ranges, actual controlled product, and missing instrument."""
import json
import os
from pathlib import Path
import subprocess
import sys

POLICY = Path(os.environ.get('POLICY_SOURCE', str(Path(__file__).resolve().parents[2] / 'policy'))).resolve()
sys.path.insert(0,str(POLICY))
ENV = {k:v for k,v in os.environ.items() if not k.startswith('PRE_COMMIT_') and k != 'SIMPLE_BASE'}
ENV.update(PYTHONPATH=str(POLICY),PYTHONDONTWRITEBYTECODE='1')


def git(repo,*args):
    return subprocess.run(['git','-c','user.name=Prueba','-c','user.email=prueba@example.org',*args],cwd=repo,check=True,capture_output=True,text=True).stdout.strip()


def card(cmd,status='done'):
    return '---\nid: X\nstatus: '+status+'\nclose_check: '+json.dumps({'cmd':cmd})+'\n---\n'


def fixture(repo):
    repo.mkdir()
    (repo/'tasks').mkdir()
    (repo/'tasks/OLD.md').write_text(card('test -f old.receipt'))
    (repo/'tasks/X.md').write_text(card('test -f receipt.json','open'))
    git(repo,'init','-q')
    git(repo,'add','--','tasks/OLD.md','tasks/X.md')
    git(repo,'commit','-qm','base')
    base=git(repo,'rev-parse','HEAD')
    (repo/'tasks/X.md').write_text(card('test -f receipt.json'))
    git(repo,'add','--','tasks/X.md')
    git(repo,'commit','-qm','cierre documental')
    return base,git(repo,'rev-parse','HEAD')


def policy(repo,*args,env=None):
    return subprocess.run([sys.executable,'-m','simple_policy','close-check','--root',str(repo),*args],cwd=repo,env=env or ENV,capture_output=True,text=True)


def test_range_reports_only_changed_closed_card(tmp_path):
    repo=tmp_path/'r';base,head=fixture(repo)
    r=policy(repo,'--base',base,'--head',head)
    assert r.returncode==0 and 'fichas_cerradas=1 ejecuta=0 no_ejecuta=1' in r.stdout,(r.stdout,r.stderr)
    assert 'OLD.md' not in r.stdout
    via_hook=policy(repo,env={**ENV,'PRE_COMMIT_FROM_REF':base,'PRE_COMMIT_TO_REF':head})
    assert via_hook.returncode==0 and via_hook.stdout==r.stdout,(via_hook.stdout,via_hook.stderr)


def test_git_missing_in_valid_repo_is_cnr_and_restoring_it_passes(tmp_path):
    repo=tmp_path/'r';base,head=fixture(repo)
    good=policy(repo,'--base',base,'--head',head)
    assert good.returncode==0
    missing=policy(repo,'--base',base,'--head',head,env={**ENV,'PATH':str(tmp_path/'empty-bin')})
    assert missing.returncode==2 and 'COULD_NOT_RUN' in missing.stderr,(missing.stdout,missing.stderr)
    restored=policy(repo,'--base',base,'--head',head)
    assert restored.returncode==0 and restored.stdout==good.stdout


def test_invalid_range_is_cnr_in_valid_repo(tmp_path):
    repo=tmp_path/'r';_,head=fixture(repo)
    r=policy(repo,'--base','missing-ref','--head',head)
    assert r.returncode==2 and 'COULD_NOT_RUN' in r.stderr


def test_real_product_positive_and_report_does_not_execute_it(tmp_path):
    repo=tmp_path/'r';base,_=fixture(repo)
    (repo/'product.py').write_text("from pathlib import Path\nPath('ran').write_text('producto')\n")
    (repo/'tasks/X.md').write_text(card('python3 product.py'))
    git(repo,'add','--','product.py','tasks/X.md');git(repo,'commit','-qm','producto')
    subprocess.run([sys.executable,'product.py'],cwd=repo,check=True)
    assert (repo/'ran').read_text()=='producto'
    (repo/'ran').unlink()
    r=policy(repo,'--base',base,'--head','HEAD')
    assert r.returncode==0 and 'fichas_cerradas=1 ejecuta=1 no_ejecuta=0' in r.stdout,(r.stdout,r.stderr)
    assert not (repo/'ran').exists(),'el reporte no debe fingir ejecucion del cierre'
