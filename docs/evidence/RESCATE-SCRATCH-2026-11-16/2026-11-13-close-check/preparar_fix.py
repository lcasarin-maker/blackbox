from pathlib import Path
import shutil,difflib,hashlib,json
s=Path.home()/'scratch/blackbox/2026-11-13-close-check';repo=Path.home()/'projects/simplecode';copy=s/'simplecode-propuesta';copy.mkdir(exist_ok=True)
shutil.copytree(repo/'policy',copy/'policy',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
(copy/'tests/policy').mkdir(parents=True,exist_ok=True)
shutil.copy2(repo/'tests/policy/test_close_check_lint.py',copy/'tests/policy/test_close_check_lint.py')
p=copy/'policy/simple_policy/close_check_lint.py';old=p.read_text();new=old.replace('Exit codes: 0 reported (never blocks in this phase), 2 COULD_NOT_RUN.','Exit codes: 0 reported; with --enforce, 1 when no_ejecuta > 0; 2 COULD_NOT_RUN.')
new=new.replace('    args = parser.parse_args(argv)','    parser.add_argument("--enforce", action="store_true", help="block closed cards without a product executor")\n    args = parser.parse_args(argv)')
new=new.replace('    return 0\n\n\nif __name__', '    return int(args.enforce and tally["no_ejecuta"] > 0)\n\n\nif __name__');assertnew=new!=old;assert assertnew;p.write_text(new)
(s/'close-check-enforce.patch').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/policy/simple_policy/close_check_lint.py',tofile='b/policy/simple_policy/close_check_lint.py')))
(s/'simplecode-source.json').write_text(json.dumps({'source':'simplecode:policy/simple_policy/close_check_lint.py','sha256_original':hashlib.sha256(old.encode()).hexdigest(),'sha256_propuesta':hashlib.sha256(new.encode()).hexdigest()},indent=2)+'\n')
