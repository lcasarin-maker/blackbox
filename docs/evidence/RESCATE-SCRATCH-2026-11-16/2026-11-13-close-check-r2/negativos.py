from pathlib import Path
import shutil,subprocess,sys,os
s=Path.home()/'scratch/blackbox/2026-11-13-close-check-r2';dest=s/'sin-detector';shutil.copytree(Path.home()/'projects/simplecode/policy',dest/'policy',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
p=dest/'policy/simple_policy/close_check_lint.py';text=p.read_text();a=text.index('def classify(');b=text.index('\n\ndef cards(',a);p.write_text(text[:a]+'def classify(command: str) -> tuple[str,str]:\n    return "ejecuta", "neutralizado en control"\n'+text[b:])
env={**os.environ,'POLICY_SOURCE':str(dest/'policy'),'PYTHONDONTWRITEBYTECODE':'1'}
r=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(s/'test_close_check_report_measurement.py')+'::test_range_reports_only_changed_closed_card'],env=env,capture_output=True,text=True);(s/'negativo-detector.txt').write_text(r.stdout+r.stderr);print('detector_neutralizado_rc='+str(r.returncode),r.stdout.splitlines()[-1]);assert r.returncode==1
p=s/'test_sin_aislar_git.py';text=(s/'test_close_check_report_measurement.py').read_text().replace("env={**ENV,'PATH':str(tmp_path/'empty-bin')}",'env=ENV');p.write_text(text)
env['POLICY_SOURCE']=str(Path.home()/'projects/simplecode/policy')
r=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(p)+'::test_git_missing_in_valid_repo_is_cnr_and_restoring_it_passes'],env=env,capture_output=True,text=True);(s/'negativo-git-presente.txt').write_text(r.stdout+r.stderr);print('git_presente_control_rc='+str(r.returncode),r.stdout.splitlines()[-1]);assert r.returncode==1
