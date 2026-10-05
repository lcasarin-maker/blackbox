from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
from datetime import datetime, timedelta
import uuid
from typing import Any

import unittest
from unittest.mock import patch

from tools import apt_sources, verify_apt_sources_closure as closure

CARD=closure.CARD_ID


def _artifact(root: Path, name: str, data: bytes) -> dict[str,Any]:
    path = root / name
    path.write_bytes(data)
    return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}


def _copy_synthetic_files(root: Path, fixture: Path) -> None:
    for name in ("InRelease","Packages","closure-keyring.gpg"):
        (root/name).write_bytes((fixture/name).read_bytes())


def _wrong_source(root: Path) -> dict[str,str]:
    content=b"Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: fixture\nComponents: main\n"
    return _artifact(root,"wrong.sources",content)


def _baseline_source(root: Path) -> dict[str,Any]:
    content=(b"Types: deb\nURIs: https://apt.invalid/repo/\nSuites: fixture\n"
             b"Components: main\nArchitectures: arm64\nSigned-By: closure-keyring.gpg\n")
    source=_artifact(root,"fixture.sources",content)
    source.update(source_id="fixture",selected_uri="https://apt.invalid/repo/",selected_suite="fixture")
    return source



def _build_synthetic_canary(root: Path, now: str, spec: tuple[str,str,dict[str,Any],str,int,str,bool]) -> dict[str,Any]:
    name,outcome,source_record,output,exit_code,target_output,needs_fresh_list=spec
    finished_at=(datetime.fromisoformat(now)-timedelta(seconds=1)).isoformat()
    started_at=(datetime.fromisoformat(now)-timedelta(seconds=3)).isoformat()
    isolated=f"/tmp/bb-apt-closure-{uuid.uuid4().hex}-{name}"
    isolated_config=(f'Dir::Etc "{isolated}/etc";\nDir::State::lists "{isolated}/lists";\n'
                     f'Dir::Cache "{isolated}/cache";\nDir::Log "{isolated}/log";\n'
                     'APT::Update::Error-Mode "any";\nAcquire::AllowInsecureRepositories "0";\n'
                     'APT::Architecture "arm64";\n')
    command_rows={
        "config":{"argv":["apt-config","dump"],"exit_code":0,"stdout":isolated_config,"stderr":"",
                  "stdout_truncated":False,"stderr_truncated":False},
        "update":{"argv":["apt-get","update"],"exit_code":exit_code,"stdout":output,"stderr":"",
                  "stdout_truncated":False,"stderr_truncated":False},
        "targets":{"argv":["apt-get","indextargets"],"exit_code":0,"stdout":target_output,"stderr":"",
                   "stdout_truncated":False,"stderr_truncated":False}}
    receipts={key:_artifact(root,f"{name}-{key}.json",(json.dumps(value,sort_keys=True)+"\n").encode())
              for key,value in command_rows.items()}
    after=[]
    if needs_fresh_list:
        list_raw=b"fresh synthetic list\n"
        list_row=_artifact(root,f"{name}-fresh-list",list_raw)
        after=[{**list_row,"size":len(list_raw),"mtime":now}]
    return {"outcome":outcome,"isolated_root":isolated,"source_id":"fixture","source":source_record,
            "source_sha256":source_record["sha256"],"receipts":receipts,
            "fresh_state":{"started_at":started_at,"finished_at":finished_at,"before":[],"after":after}}


def _synthetic_bundle(root: Path) -> tuple[dict[str,Any],str]:
    fixture=Path(__file__).parents[1]/"tests/fixtures/apt_closure_synthetic"
    _copy_synthetic_files(root,fixture)
    source=_baseline_source(root)
    config_text='''APT::Architecture "arm64";
APT::Architectures:: "arm64";
Acquire::Languages "none";
Acquire::AllowInsecureRepositories "0";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Packages::Optional "0";
'''
    config=_artifact(root,"apt-config.dump",config_text.encode())
    config.update(argv=["apt-config","dump"],exit_code=0,stdout_truncated=False,stderr_truncated=False)
    targets_text='''Repo-URI: https://apt.invalid/repo/
Suite: fixture
Architecture: arm64
Identifier: Packages
MetaKey: main/binary-arm64/Packages
Component: main
Target-Of: deb
'''
    effective=_artifact(root,"indextargets.txt",targets_text.encode())
    effective.update(argv=["apt-get","indextargets"],exit_code=0,stdout_truncated=False,stderr_truncated=False)
    keyring=_artifact(root,"closure-keyring.gpg",(root/"closure-keyring.gpg").read_bytes())
    inrelease=_artifact(root,"InRelease",(root/"InRelease").read_bytes())
    packages=_artifact(root,"Packages",(root/"Packages").read_bytes())
    provenance=json.loads((fixture/"provenance.json").read_text(encoding="utf-8"))
    fingerprint=provenance["fingerprint"]
    subject={"manufacturer":"fixture OEM","product":"fixture host","bios":"fixture BIOS",
             "kernel":"fixture kernel","architecture":"arm64","apt_version":"fixture apt",
             "gpgv_version":"fixture gpgv"}
    profile={"source_id":"fixture","uri":"https://apt.invalid/repo/","suite":"fixture",
             "architecture":"arm64","types":"deb","components":"main",
             "signed_by":"closure-keyring.gpg","allowed_fingerprints":[fingerprint]}
    decision={"card_id":CARD,"subject":subject,"profile":[profile],
              "freshness":{"fixture":{"max_age_seconds":2147483647}}}
    decision_row=_artifact(root,"decision.json",(json.dumps(decision,sort_keys=True)+"\n").encode())
    now=subprocess.run(["date","--utc","--iso-8601=seconds"],check=True,capture_output=True,text=True).stdout.strip()
    clock_bytes=(json.dumps({"argv":["date","--utc","--iso-8601=seconds"],"exit_code":0,
                            "stdout":now,"stderr":"","stdout_truncated":False,
                            "stderr_truncated":False})+"\n").encode()
    clock=_artifact(root,"clock.json",clock_bytes)
    stack=_artifact(root,"subject-stack.json",(json.dumps(subject,sort_keys=True)+"\n").encode())
    index_release=inrelease
    coverage={"source":"fixture","release":index_release,"expected_meta_keys":["main/binary-arm64/Packages"],
              "observed_meta_keys":["main/binary-arm64/Packages"]}
    index_row={"source":"fixture","meta_key":"main/binary-arm64/Packages",
               "release":index_release,"content":packages}
    package_state=_artifact(root,"package-state.txt",b"synthetic package state\n")
    wrong_source=_wrong_source(root)
    healthy=_build_synthetic_canary(root,now,("healthy","healthy",source,"Hit:1 fixture repository",0,"fixture target",True))
    wrong=_build_synthetic_canary(root,now,("wrong","wrong_arm64_source",wrong_source,
                                      "404 http://archive.ubuntu.com/ubuntu binary-arm64/Packages",100,"",False))
    bad_package=_build_synthetic_canary(root,now,("bad-package","bad_package_hash",source,"Hash Sum mismatch",100,"",False))
    bad_package["meta_key"]="main/binary-arm64/Packages"
    corrupted_packages=_artifact(root,"Packages.corrupt",(root/"Packages").read_bytes()+b"corrupt")
    bad_package["negative_input"]=corrupted_packages
    bad_signature=_build_synthetic_canary(root,now,("bad-signature","bad_release_signature",source,"BADSIG",100,"",False))
    corrupted_release=(root/"InRelease").read_bytes().replace(b"Suite: fixture",b"Suite: altered",1)
    bad_signature["negative_input"]=_artifact(root,"InRelease.corrupt",corrupted_release)
    all_canaries=[bad_package,bad_signature]
    roots=[healthy["isolated_root"],wrong["isolated_root"],
           bad_package["isolated_root"],bad_signature["isolated_root"]]
    cleanup=[]
    for index,isolated in enumerate(roots):
        receipt=_artifact(root,f"cleanup-{index}.json",
                          (json.dumps({"argv":["test","!","-e",isolated],"exit_code":0})+"\n").encode())
        receipt["expected_absent_path"]=isolated
        cleanup.append(receipt)
    state={"sources":[source["sha256"]],"keyrings":[keyring["sha256"]],
           "apt_config":config["sha256"],"package_state":package_state["sha256"]}
    before=_artifact(root,"state-before.json",(json.dumps(state,sort_keys=True)+"\n").encode())
    after_state=_artifact(root,"state-after.json",(json.dumps(state,sort_keys=True)+"\n").encode())
    rollback={"before":before,"after":after_state,"cleanup_receipts":cleanup}
    doc={"schema":1,"id":CARD,"subject_stack":stack,"decision_anchor":decision_row,
         "apt_config_dump":config,"effective_targets":effective,"sources":[source],
         "repositories":[{"source":"fixture","inrelease":inrelease,"keyrings":[keyring],
                          "allowed_fingerprints":[fingerprint]}],
         "indexes":[index_row],"coverage":[coverage],
         "freshness":[{"source":"fixture","release":inrelease,"clock":clock}],
         "healthy_canary":healthy,"wrong_source_canary":wrong,
         "integrity_negative_canaries":all_canaries,
         "safety":{"source":source,"config":_artifact(root,"safety-config.txt",
                   json.loads((root/healthy["receipts"]["config"]["path"]).read_text(encoding="utf-8"))["stdout"].encode()),
                   "isolated_root":healthy["isolated_root"]},
         "package_state":package_state,"rollback":rollback}
    doc_path=root/"capture.json"
    doc_path.write_text(json.dumps(doc,sort_keys=True)+"\n", encoding="utf-8")
    return doc,hashlib.sha256((json.dumps(decision,sort_keys=True)+"\n").encode()).hexdigest()


def test_synthetic_signed_baseline_passes_all_twelve_gates_and_tamper_fails(tmp_path: Path) -> None:
    _,anchor=_synthetic_bundle(tmp_path)
    capture=tmp_path/"capture.json"
    baseline=closure.verify(capture,anchor)
    assert baseline["status"]=="pass"
    assert baseline["could_not_run"]==0 and baseline["fail"]==0
    assert [item["status"] for item in baseline["gates"]]==["pass"]*12
    cli=subprocess.run(["python3","-m","tools.verify_apt_sources_closure",
                        "--evidence",str(capture),"--decision-sha256",anchor],
                       cwd=Path(__file__).parents[1],capture_output=True,text=True,check=False)
    assert cli.returncode==0
    assert json.loads(cli.stdout)["status"]=="pass"

    package_path=tmp_path/"Packages"
    package_path.write_bytes(package_path.read_bytes()+b"changed")
    tampered=closure.verify(capture,anchor)
    assert tampered["status"]=="fail"
    index_gate=next(item for item in tampered["gates"] if item["gate"]=="effective_index_integrity_and_coverage")
    assert index_gate["status"]=="fail"


def test_full_bundle_unavailable_dependency_stays_unknown(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    doc["effective_targets"].pop("stdout_truncated")
    capture=tmp_path/"capture.json"
    capture.write_text(json.dumps(doc,sort_keys=True)+"\n", encoding="utf-8")
    result=closure.verify(capture,anchor)
    assert result["status"]=="unknown"
    source_gate=next(item for item in result["gates"] if item["gate"]=="configured_source_coverage")
    assert source_gate["status"]=="could_not_run"


def test_full_bundle_missing_negative_input_stays_unknown(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    doc["integrity_negative_canaries"][0].pop("negative_input")
    capture=tmp_path/"capture.json"
    capture.write_text(json.dumps(doc,sort_keys=True)+"\n", encoding="utf-8")
    result=closure.verify(capture,anchor)
    assert result["status"]=="unknown"
    gate=next(item for item in result["gates"] if item["gate"]=="integrity_negatives")
    assert gate["status"]=="could_not_run"


def test_source_target_addition_must_match_native_indextargets(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    raw=b'''APT::Architecture "arm64";
APT::Architectures:: "arm64";
Acquire::Languages "en";
Acquire::AllowInsecureRepositories "0";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
'''
    config=doc["apt_config_dump"]
    (tmp_path/config["path"]).write_bytes(raw)
    config["sha256"]=hashlib.sha256(raw).hexdigest()
    capture=tmp_path/"capture.json"
    capture.write_text(json.dumps(doc,sort_keys=True)+"\n", encoding="utf-8")
    result=closure.verify(capture,anchor)
    source_gate=next(item for item in result["gates"] if item["gate"]=="configured_source_coverage")
    assert source_gate["status"]=="fail"


def test_source_gate_requires_approved_profile_before_target_comparison(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    assert closure._source_gate(doc,tmp_path,None)["status"]=="could_not_run"
    mismatched={**decision,"profile":[{**decision["profile"][0],"uri":"https://other.invalid/"}]}
    result=closure._source_gate(doc,tmp_path,mismatched)
    assert result["status"]=="fail" and "unapproved configured source" in result["reason"]
    missing={**doc,"effective_targets":None}
    assert closure._source_gate(missing,tmp_path,decision)["status"]=="could_not_run"


def test_source_architecture_add_remove_are_applied_to_profile() -> None:
    stanza={"types":"deb","components":"main","architectures":"arm64",
            "architectures-add":"amd64","architectures-remove":"arm64"}
    config=closure.TargetConfig({"deb":{"Packages":{"DefaultEnabled":"true"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    rows=closure._source_profile_rows("fixture",stanza,"https://apt.invalid/repo/","fixture",config)
    assert [row["architecture"] for row in rows]==["amd64"]


def test_malformed_integrity_negative_record_returns_unknown_without_traceback(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    doc["integrity_negative_canaries"].append("malformed")
    capture=tmp_path/"capture.json"
    capture.write_text(json.dumps(doc,sort_keys=True)+"\n", encoding="utf-8")
    result=closure.verify(capture,anchor)
    assert result["status"]=="unknown"
    gate=next(item for item in result["gates"] if item["gate"]=="integrity_negatives")
    assert gate["status"]=="could_not_run"


def test_missing_bundle_reports_all_gates_could_not_run(tmp_path: Path) -> None:
    result = closure.verify(tmp_path / "absent.json")
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 12
    assert [row["gate"] for row in result["gates"]] == list(closure.GATES)


def test_existing_dossier_commands_without_integral_capture_stays_cnr() -> None:
    dossier = Path("tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json")
    result = closure.verify(dossier)
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 12
    assert result["gates"][0]["status"] == "could_not_run"


def test_malformed_and_wrong_identity_are_distinguished(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    assert closure.verify(malformed)["status"] == "unknown"

    wrong_id = tmp_path / "wrong.json"
    wrong_id.write_text(json.dumps({"schema": 1, "id": "OTHER"}), encoding="utf-8")
    result = closure.verify(wrong_id)
    assert result["status"] == "fail"
    assert result["fail"] == 1


def test_json_duplicate_keys_and_nonfinite_numbers_are_rejected(tmp_path: Path) -> None:
    for name,raw in (("duplicate.json",b'{"id":"one","id":"two"}'),
                     ("nonfinite.json",b'{"id":"x","value":NaN}')):
        path=tmp_path/name
        path.write_bytes(raw)
        result=closure.verify(path)
        assert result["status"]=="unknown"
        assert result["could_not_run"]==12


def test_fifo_capture_is_opened_nonblocking_and_classified_cnr(tmp_path: Path) -> None:
    path=tmp_path/"capture.json"
    os.mkfifo(path)
    result=closure.verify(path)
    assert result["status"]=="unknown"
    assert result["could_not_run"]==12


def test_capture_under_symlinked_ancestor_is_classified_cnr(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    evidence = real_root / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "capture.json").write_text('{"schema":1,"id":"OTHER"}', encoding="utf-8")
    link = tmp_path / "linked-root"
    link.symlink_to(real_root, target_is_directory=True)

    result = closure.verify(link / "evidence" / "capture.json")

    assert result["status"] == "unknown"
    assert result["could_not_run"] == 12


def test_doc_rejects_parent_traversal_before_open(tmp_path: Path) -> None:
    path=tmp_path/"child"/".."/"capture.json"
    assert closure.verify(path)["status"]=="unknown"


def test_reader_rejects_lexical_escape_and_oversize_artifact(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"parent traversal"):
        closure._read(tmp_path/".."/"outside.json",tmp_path)
    oversized=tmp_path/"oversized.bin"
    with oversized.open("wb") as stream:
        stream.truncate(closure.MAX_BYTES+1)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"byte cap"):
        closure._read(oversized,tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"escapes evidence root"):
        closure._read(oversized,tmp_path/"child")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"malformed"):
        closure._read(tmp_path,tmp_path)


def test_command_receipt_rejects_bad_argv_status_and_truncation(tmp_path: Path) -> None:
    raw=b"apt output\n"
    base={"argv":["apt-config","dump"],"exit_code":0,
          "stdout_truncated":False,"stderr_truncated":False,
          **_artifact(tmp_path,"apt-output",raw)}
    assert closure._captured_command_output({"receipt":base},tmp_path,"receipt",
                                            ["apt-config","dump"],"apt-config") == raw
    invalid=(
        {**base,"argv":["apt-config","--version"]},
        {**base,"exit_code":True},
        {**base,"exit_code":1},
        {**base,"stdout_truncated":True},
        {**base,"stderr_truncated":1},
        None,
    )
    for receipt in invalid:
        with unittest.TestCase().assertRaises(closure.EvidenceMissing):
            closure._captured_command_output({"receipt":receipt},tmp_path,"receipt",
                                            ["apt-config","dump"],"apt-config")


def test_decision_records_require_external_digest_and_full_policy(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"decision record"):
        closure._decision(tmp_path,None,"a"*64)
    row=_artifact(tmp_path,"decision.json",b'{"card_id":"OTHER"}\n')
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"trust binding"):
        closure._decision(tmp_path,row,None)
    with unittest.TestCase().assertRaises(ValueError):
        closure._decision(tmp_path,row,"0"*64)
    with unittest.TestCase().assertRaisesRegex(ValueError,"different card"):
        closure._decision(tmp_path,row,hashlib.sha256(b'{"card_id":"OTHER"}\n').hexdigest())


def test_decision_gate_preserves_cnr_and_binding_failure(tmp_path: Path) -> None:
    gate,decision=closure._decision_gate({},tmp_path,None)
    assert gate["status"]=="could_not_run" and decision is None
    row=_artifact(tmp_path,"wrong-anchor.json",b'{"card_id":"OTHER"}\n')
    gate,decision=closure._decision_gate({"decision_anchor":row},tmp_path,"0"*64)
    assert gate["status"]=="fail" and decision is None


def test_decision_policy_requires_source_and_freshness_arrays(tmp_path: Path) -> None:
    base={"card_id":CARD,"subject":{"manufacturer":"m","product":"p","bios":"b","kernel":"k",
          "architecture":"arm64","apt_version":"a","gpgv_version":"g"},
          "profile":[{"source_id":"repo"}],"freshness":{"repo":{"max_age_seconds":60}}}
    for field,empty,reason in (("profile",[],"nonempty"),("freshness",{},"per-source")):
        decision={**base,field:empty}
        raw=(json.dumps(decision,sort_keys=True)+"\n").encode()
        row=_artifact(tmp_path,f"decision-{field}.json",raw)
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,reason):
            closure._decision(tmp_path,row,hashlib.sha256(raw).hexdigest())


def test_profile_comparison_reports_each_direction_and_malformed_rows() -> None:
    row={"source_id":"one","uri":"https://apt.invalid/","suite":"stable",
         "architecture":"arm64","types":"deb","components":"main","signed_by":"key"}
    assert closure._profile_matches([row],[row])==(True,[])
    ok,errors=closure._profile_matches([row],[{**row,"source_id":"two"}])
    assert not ok and any("unapproved" in error for error in errors) and any("missing" in error for error in errors)
    assert closure._profile_matches([row],[{"source_id":"one"}])[0] is False


def test_read_configured_sources_rejects_architecture_and_missing_source_records(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    assert closure._read_configured_sources(doc,tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"active source files"):
        closure._read_configured_sources({**doc,"sources":[]},tmp_path)
    config=doc["apt_config_dump"]
    wrong_arch=b'APT::Architecture "amd64";\nAcquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";\n'
    config_path=tmp_path/config["path"]
    config_path.write_bytes(wrong_arch)
    config["sha256"]=hashlib.sha256(wrong_arch).hexdigest()
    with unittest.TestCase().assertRaisesRegex(ValueError,"not arm64"):
        closure._read_configured_sources(doc,tmp_path)


def test_source_expansion_rejects_multiple_active_matches_and_ignores_disabled(tmp_path: Path) -> None:
    record=_baseline_source(tmp_path)
    stanza=b"Types: deb\nURIs: https://apt.invalid/repo/\nSuites: fixture\nComponents: main\n"
    stanzas,errors=apt_sources.parse_deb822((stanza+b"\n"+stanza).decode())
    assert not errors
    config=closure.TargetConfig({"deb":{"Packages":{"MetaKey":"$(COMPONENT)/Packages"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"multiple active stanza"):
        closure._expand_sources("fixture",stanzas,record,config)
    disabled=b"Types: deb\nURIs: https://apt.invalid/repo/\nSuites: fixture\nComponents: main\nEnabled: no\n"
    rows,errors=apt_sources.parse_deb822(disabled.decode())
    assert not errors
    assert closure._expand_sources("fixture",rows,record,config)==[]


def test_read_configured_sources_rejects_parse_errors_and_unbound_id(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    source=doc["sources"][0]
    source_path=tmp_path/source["path"]
    malformed=b"Types: deb\nURIs: https://apt.invalid/repo/\nTypes: deb-src\n"
    source_path.write_bytes(malformed)
    source["sha256"]=hashlib.sha256(malformed).hexdigest()
    with unittest.TestCase().assertRaisesRegex(ValueError,"source parse errors"):
        closure._read_configured_sources(doc,tmp_path)


def test_configured_sources_and_expansion_require_bound_ids(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source_id binding"):
        closure._read_configured_sources({**doc,"sources":[{"path":"fixture.sources","sha256":doc["sources"][0]["sha256"]}]},tmp_path)
    record={"source_id":"fixture"}
    config=closure.TargetConfig({"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"exact URI and suite"):
        closure._expand_sources("fixture",[],record,config)
    with unittest.TestCase().assertRaisesRegex(ValueError,"no supported deb type"):
        closure._source_profile_rows("fixture",{"types":"rpm"},"https://apt.invalid/","stable",config)


def test_expected_index_derivation_requires_exact_active_source_and_uri(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    config=doc["apt_config_dump"]
    config_text=(tmp_path/config["path"]).read_text(encoding="utf-8")
    assert closure._expected_index_paths(doc,tmp_path,config_text)=={"fixture":{"main/binary-arm64/Packages"}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"repository id"):
        closure._expected_index_paths({"sources":[{}]},tmp_path,config_text)
    unbound={"sources":[{**doc["sources"][0],"selected_uri":"https://different.invalid/"}]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"does not select exactly one"):
        closure._expected_index_paths(unbound,tmp_path,config_text)


def test_expected_index_derivation_rejects_unavailable_and_empty_target_sets(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    config=(tmp_path/doc["apt_config_dump"]["path"]).read_text(encoding="utf-8")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source bytes unavailable"):
        closure._expected_index_paths({"sources":[]},tmp_path,config)
    no_targets="APT::Architecture \"arm64\";\nAcquire::Languages \"none\";\n"
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"definitions"):
        closure._expected_index_paths(doc,tmp_path,no_targets)
    source=doc["sources"][0]
    targets_disabled=(b"Types: deb\nURIs: https://apt.invalid/repo/\nSuites: fixture\n"
                      b"Components: main\nArchitectures: arm64\nSigned-By: closure-keyring.gpg\n")
    source_path=tmp_path/source["path"]
    source_path.write_bytes(targets_disabled)
    source["sha256"]=hashlib.sha256(targets_disabled).hexdigest()
    config_empty=('APT::Architecture "arm64";\nAcquire::Languages "none";\n'
                  'Acquire::IndexTargets::deb::Packages::DefaultEnabled "true";\n')
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"no enabled index MetaKeys"):
        closure._expected_index_paths(doc,tmp_path,config_empty)


def test_effective_target_derivation_requires_bound_single_active_stanza(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    config=(tmp_path/doc["apt_config_dump"]["path"]).read_text(encoding="utf-8")
    target_config=closure._apt_target_definitions(config)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"identity unavailable"):
        closure._derive_source_target_rows({},tmp_path,target_config)
    source=doc["sources"][0]
    missing_uri={**source,"selected_uri":None}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"exact selected URI"):
        closure._derive_source_target_rows(missing_uri,tmp_path,target_config)
    disabled_source=_artifact(tmp_path,"disabled.sources",b"Types: deb\nURIs: https://apt.invalid/repo/\nSuites: fixture\nComponents: main\nEnabled: no\n")
    disabled_source.update(source_id="fixture",selected_uri="https://apt.invalid/repo/",selected_suite="fixture")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"exactly one enabled stanza"):
        closure._derive_source_target_rows(disabled_source,tmp_path,target_config)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source records required"):
        closure._derive_target_rows({"sources":[]},tmp_path,config)


def test_verified_release_and_index_rows_reject_duplicate_and_unbound_records(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    releases=closure._verified_releases(doc,tmp_path)
    assert set(releases)=={"fixture"}
    with unittest.TestCase().assertRaisesRegex(ValueError,"duplicated"):
        closure._verified_releases({"repositories":[*doc["repositories"],doc["repositories"][0]]},tmp_path)
    observed=closure._verified_index_rows(doc,tmp_path,releases)
    assert observed=={"fixture":{"main/binary-arm64/Packages"}}
    with unittest.TestCase().assertRaisesRegex(ValueError,"duplicate source/index"):
        closure._verified_index_rows({**doc,"indexes":[*doc["indexes"],doc["indexes"][0]]},tmp_path,releases)


def test_verified_indexes_reject_wrong_release_and_malformed_records(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    releases=closure._verified_releases(doc,tmp_path)
    with unittest.TestCase().assertRaisesRegex(ValueError,"not bound to source"):
        closure._verified_index_rows({**doc,"indexes":[{**doc["indexes"][0],"source":"absent"}]},tmp_path,releases)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"must be an object"):
        closure._verified_index_rows({**doc,"indexes":[None]},tmp_path,releases)


def test_coverage_manifest_rejects_missing_duplicate_and_mismatched_records(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    verified=closure._verified_releases(doc,tmp_path)
    observed=closure._verified_index_rows(doc,tmp_path,verified)
    assert closure._coverage_results(doc,tmp_path,verified,observed)[0]["status"]=="pass"
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"records absent"):
        closure._coverage_results({**doc,"coverage":[]},tmp_path,verified,observed)
    duplicate={**doc,"coverage":[*doc["coverage"],doc["coverage"][0]]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"count must match"):
        closure._coverage_results(duplicate,tmp_path,verified,observed)
    wrong={**doc,"coverage":[{**doc["coverage"][0],"expected_meta_keys":["main/other"]}]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"expected index paths differ"):
        closure._coverage_results(wrong,tmp_path,verified,observed)
    wrong_observed={**doc,"coverage":[{**doc["coverage"][0],"observed_meta_keys":[]}]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"observed keys differ"):
        closure._coverage_results(wrong_observed,tmp_path,verified,observed)


def test_effective_target_parser_rejects_bad_uri_unresolved_and_duplicate_rows() -> None:
    prefix="Suite: stable\nArchitecture: arm64\nIdentifier: Packages\nMetaKey: main/Packages\nComponent: main\nTarget-Of: deb\n"
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"invalid repository URI"):
        closure._parse_effective_targets("Repo-URI: not a URI\n"+prefix)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unresolved identity"):
        closure._parse_effective_targets("Repo-URI: https://apt.invalid/$(SOURCE)\n"+prefix)
    duplicate="Repo-URI: https://apt.invalid/repo/\n"+prefix
    with unittest.TestCase().assertRaisesRegex(ValueError,"duplicate effective"):
        closure._parse_effective_targets(duplicate+"\n"+duplicate)


def test_subject_gate_rejects_arm64_subject_mismatch(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    stack_path=tmp_path/doc["subject_stack"]["path"]
    stack=json.loads(stack_path.read_text(encoding="utf-8"))
    stack["architecture"]="amd64"
    raw=(json.dumps(stack,sort_keys=True)+"\n").encode()
    stack_path.write_bytes(raw)
    doc["subject_stack"]["sha256"]=hashlib.sha256(raw).hexdigest()
    result=closure._subject_gate(doc,tmp_path,decision)
    assert result["status"]=="fail" and "not arm64" in result["reason"]


def test_subject_gate_distinguishes_missing_stack_and_fixed_tuple_conflict(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    assert closure._subject_gate(doc,tmp_path,None)["status"]=="could_not_run"
    stack_row=doc["subject_stack"]
    stack_path=tmp_path/stack_row["path"]
    stack=json.loads(stack_path.read_text(encoding="utf-8"))
    del stack["bios"]
    raw=(json.dumps(stack,sort_keys=True)+"\n").encode()
    stack_path.write_bytes(raw)
    stack_row["sha256"]=hashlib.sha256(raw).hexdigest()
    result=closure._subject_gate(doc,tmp_path,decision)
    assert result["status"]=="could_not_run" and "fields incomplete" in result["reason"]

    stack["bios"]="fixture BIOS"
    raw=(json.dumps(stack,sort_keys=True)+"\n").encode()
    stack_path.write_bytes(raw)
    stack_row["sha256"]=hashlib.sha256(raw).hexdigest()
    decision["subject"]["bios"]="different BIOS"
    result=closure._subject_gate(doc,tmp_path,decision)
    assert result["status"]=="fail" and "differs" in result["reason"]


def test_signature_gate_keeps_missing_keyring_cnr_and_allowlist_mismatch_fail(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    missing={**doc,"repositories":[{**doc["repositories"][0],"keyrings":[]}]}
    assert closure._signature_gate(missing,tmp_path,decision)["status"]=="could_not_run"
    mismatch={**doc,"repositories":[{**doc["repositories"][0],"allowed_fingerprints":["0"*40]}]}
    result=closure._signature_gate(mismatch,tmp_path,decision)
    assert result["status"]=="fail" and "allowlist" in result["reason"]


def test_signature_gate_requires_repo_source_coverage_and_bound_approval(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    assert closure._signature_gate({**doc,"repositories":[]},tmp_path,decision)["status"]=="could_not_run"
    duplicate={**doc,"repositories":[*doc["repositories"],doc["repositories"][0]]}
    assert closure._signature_gate(duplicate,tmp_path,decision)["status"]=="could_not_run"
    result=closure._signature_gate(doc,tmp_path,None)
    assert result["status"]=="fail" and "allowlist differs" in result["reason"]


def test_signature_gate_preserves_native_verifier_cnr(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    unavailable=tmp_path/"empty-path"
    unavailable.mkdir()
    with patch.dict(os.environ,{"PATH":str(unavailable)}):
        result=closure._signature_gate(doc,tmp_path,decision)
    assert result["status"]=="could_not_run"


def test_repository_coverage_requires_one_receipt_per_active_source() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"every configured source"):
        closure._check_repository_coverage({"sources":[{"source_id":"one"}]},[])
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"every configured source"):
        closure._check_repository_coverage({"sources":[{"source_id":"one"}]},
                                           [{"source":"one"},{"source":"one"}])


def test_freshness_gate_classifies_malformed_native_clock_as_fail(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    clock=doc["freshness"][0]["clock"]
    clock_path=tmp_path/clock["path"]
    raw=b'{"argv":["date","--utc","--iso-8601=seconds"],"exit_code":0,"stdout":"not-a-time","stdout_truncated":false,"stderr_truncated":false}'
    clock_path.write_bytes(raw)
    clock["sha256"]=hashlib.sha256(raw).hexdigest()
    result=closure._freshness_gate(doc,tmp_path,decision)
    assert result["status"]=="fail" and "Invalid isoformat" in result["reason"]


def test_freshness_gate_requires_policy_exact_source_coverage(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    assert closure._freshness_gate(doc,tmp_path,None)["status"]=="could_not_run"
    assert closure._freshness_gate({**doc,"freshness":[]},tmp_path,decision)["status"]=="could_not_run"
    duplicate={**doc,"freshness":[*doc["freshness"],doc["freshness"][0]]}
    assert closure._freshness_gate(duplicate,tmp_path,decision)["status"]=="could_not_run"
    unapproved={**decision,"freshness":{}}
    result=closure._freshness_gate(doc,tmp_path,unapproved)
    assert result["status"]=="fail" and "not bound to decision" in result["reason"]


def test_native_locale_receipt_requires_exact_success_and_resolved_language(tmp_path: Path) -> None:
    bad=_artifact(tmp_path,"locale-bad.json",b'{"argv":["locale"],"exit_code":0,"stdout":"LANG=POSIX\\n","stdout_truncated":false,"stderr_truncated":false}')
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"did not resolve"):
        closure._resolved_languages({"language_environment":bad},tmp_path,[],True)
    wrong_argv=_artifact(tmp_path,"locale-argv.json",b'{"argv":["env"],"exit_code":0,"stdout":"LANG=en_US.UTF-8\\n"}')
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"successful native locale"):
        closure._resolved_languages({"language_environment":wrong_argv},tmp_path,[],True)


def test_negative_gate_rejects_shared_isolated_roots(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    doc["integrity_negative_canaries"][1]["isolated_root"]=doc["integrity_negative_canaries"][0]["isolated_root"]
    result=closure._negative_gate(doc,tmp_path)
    assert result["status"]=="fail" and "independent isolated roots" in result["reason"]


def test_negative_controls_reject_neutralized_package_and_signature_inputs(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    package=doc["integrity_negative_canaries"][0]
    baseline=next(row for row in doc["indexes"] if row["source"]==package["source_id"])
    package["negative_input"]=baseline["content"]
    with unittest.TestCase().assertRaisesRegex(ValueError,"byte-identical"):
        closure._verify_package_negative(doc,tmp_path,package)

    signature=doc["integrity_negative_canaries"][1]
    repository=doc["repositories"][0]
    damaged=signature["negative_input"]
    signature["negative_input"]=repository["inrelease"]
    with unittest.TestCase().assertRaisesRegex(ValueError,"byte-identical"):
        closure._verify_signature_negative(doc,tmp_path,signature)
    signature["negative_input"]=damaged
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source keyring"):
        closure._verify_signature_negative({**doc,"repositories":[{**repository,"keyrings":[]}]},tmp_path,signature)


def test_integrity_negative_verifier_cnr_stays_unclosed(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    package=doc["integrity_negative_canaries"][0]
    baseline=doc["indexes"][0]
    manifest=_artifact(tmp_path,"malformed-release.txt",b"not a SHA256 manifest\n")
    baseline["release"]=manifest
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"not verified"):
        closure._verify_package_negative(doc,tmp_path,package)
    signature=doc["integrity_negative_canaries"][1]
    unavailable=tmp_path/"empty-path"
    unavailable.mkdir()
    with patch.dict(os.environ,{"PATH":str(unavailable)}):
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"could not conclusively"):
            closure._verify_signature_negative(doc,tmp_path,signature)


def test_safety_gate_fails_when_canary_source_is_not_active_source(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    raw=b"Types: deb\nURIs: https://different.invalid/\nSuites: stable\nComponents: main\n"
    doc["safety"]["source"]=_artifact(tmp_path,"safety-wrong-source.sources",raw)
    result=closure._safety_gate(doc,tmp_path)
    assert result["status"]=="fail" and "do not match active" in result["reason"]


def test_rollback_gate_fails_when_after_state_differs(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["rollback"]["after"]
    path=tmp_path/row["path"]
    state=json.loads(path.read_text(encoding="utf-8"))
    state["package_state"]="0"*64
    raw=(json.dumps(state,sort_keys=True)+"\n").encode()
    path.write_bytes(raw)
    row["sha256"]=hashlib.sha256(raw).hexdigest()
    result=closure._rollback_gate(doc,tmp_path)
    assert result["status"]=="fail" and "digest map differs" in result["reason"]


def test_successful_canary_fails_if_its_temporary_root_remains(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["healthy_canary"]
    canary_root=Path(row["isolated_root"])
    assert not canary_root.exists()
    canary_root.mkdir()
    try:
        result=closure._canary_result(doc,tmp_path,"healthy",row)
        assert result["status"]=="fail" and "root remains" in result["result"]["reason"]
    finally:
        canary_root.rmdir()


def test_canary_fresh_state_rejects_prepopulated_lists_and_missing_window(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["healthy_canary"]
    with unittest.TestCase().assertRaisesRegex(ValueError,"lists were not empty"):
        closure._canary_fresh_state(tmp_path,{**row,"fresh_state":{**row["fresh_state"],"before":row["fresh_state"]["after"]}},"healthy")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"timestamps incomplete"):
        closure._state_window({"started_at":"not-a-time"},"healthy")


def test_canary_window_and_list_timestamps_require_timezone_and_post_update_mtime(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"timestamps incomplete"):
        closure._state_window({"started_at":"2026-10-04T00:00:00","finished_at":"2026-10-04T00:00:01"},"healthy")
    row=_artifact(tmp_path,"list-after",b"index bytes")
    entry={**row,"size":len(b"index bytes"),"mtime":"2026-10-04T00:00:00Z"}
    finished=datetime.fromisoformat("2026-10-04T00:00:01+00:00")
    with unittest.TestCase().assertRaisesRegex(ValueError,"predates"):
        closure._check_list_rows(tmp_path,[entry],"after","healthy",finished)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"lacks timezone"):
        closure._check_list_rows(tmp_path,[{**entry,"mtime":"2026-10-04T00:00:02"}],"after","healthy",finished)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"mtime unavailable"):
        closure._check_list_rows(tmp_path,[{**entry,"mtime":None}],"after","healthy",finished)


def test_healthy_canary_requires_new_list_files_after_update(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    state={**doc["healthy_canary"]["fresh_state"],"after":[]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"did not create"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":state},"healthy")


def test_canary_list_metadata_and_source_hash_mismatches_fail(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["healthy_canary"]
    entry=row["fresh_state"]["after"][0]
    with unittest.TestCase().assertRaisesRegex(ValueError,"size mismatch"):
        closure._check_list_rows(tmp_path,[{**entry,"size":entry["size"]+1}],"after","healthy",datetime.fromisoformat(entry["mtime"]))
    with unittest.TestCase().assertRaisesRegex(ValueError,"source hash binding mismatch"):
        closure._check_canary_source(doc,tmp_path,"healthy",{**row,"source_sha256":"0"*64})


def test_wrong_source_canary_must_differ_and_name_the_incompatible_endpoint(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    active=doc["sources"][0]
    same={"source":active,"source_sha256":active["sha256"]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"reuses unchanged baseline"):
        closure._check_canary_source(doc,tmp_path,"wrong_arm64_source",same)
    wrong_source=_artifact(tmp_path,"wrong-endpoint.sources",b"Types: deb\nURIs: https://other.invalid/repo\nSuites: noble\nComponents: main\n")
    wrong={"source":wrong_source,"source_sha256":wrong_source["sha256"]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"incompatible Ubuntu endpoint"):
        closure._check_canary_source(doc,tmp_path,"wrong_arm64_source",wrong)


def test_cleanup_requires_exact_command_receipt_per_root(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    rollback=doc["rollback"]
    rollback["cleanup_receipts"][0]["expected_absent_path"]="/tmp/unrelated-root"
    with unittest.TestCase().assertRaisesRegex(ValueError,"do not check each exact"):
        closure._verify_cleanup(doc,tmp_path,rollback)


def test_cleanup_gate_reports_missing_row_and_nonzero_absence_check(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    assert closure._rollback_gate({**doc,"rollback":None},tmp_path)["status"]=="could_not_run"
    row=doc["rollback"]
    receipt=row["cleanup_receipts"][0]
    path=tmp_path/receipt["path"]
    command=json.loads(path.read_text(encoding="utf-8"))
    command["exit_code"]=1
    raw=(json.dumps(command,sort_keys=True)+"\n").encode()
    path.write_bytes(raw)
    receipt["sha256"]=hashlib.sha256(raw).hexdigest()
    result=closure._rollback_gate(doc,tmp_path)
    assert result["status"]=="fail" and "successful absent-path" in result["reason"]


def test_canary_gate_distinguishes_missing_inventory_and_invalid_root(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    gates=[]
    closure._canary_gate(gates,{**doc,"healthy_canary":None},tmp_path,(
        "healthy_canary","fresh_isolated_update","healthy"))
    assert gates[-1]["status"]=="could_not_run"
    row={**doc["healthy_canary"],"isolated_root":"/var/tmp/not-an-isolated-apt-root"}
    closure._canary_gate(gates,{**doc,"healthy_canary":row},tmp_path,(
        "healthy_canary","fresh_isolated_update","healthy"))
    assert gates[-1]["status"]=="fail" and "direct child of /tmp" in gates[-1]["reason"]


def test_verify_rejects_schema_version_without_running_gates(tmp_path: Path) -> None:
    path=tmp_path/"unsupported-schema.json"
    path.write_text(json.dumps({"id":CARD,"schema":2}), encoding="utf-8")
    result=closure.verify(path)
    assert result["status"]=="unknown" and result["could_not_run"]==12
    assert all(gate["status"]=="could_not_run" for gate in result["gates"])


def test_cli_exit_codes_distinguish_unknown_from_failed_identity(tmp_path: Path, capsys: Any) -> None:
    missing=tmp_path/"missing.json"
    assert closure.main(["--evidence",str(missing)])==2
    missing_output=json.loads(capsys.readouterr().out)
    assert missing_output["status"]=="unknown" and missing_output["could_not_run"]==12
    wrong=tmp_path/"wrong-card.json"
    wrong.write_text(json.dumps({"schema":1,"id":"OTHER"}), encoding="utf-8")
    assert closure.main(["--evidence",str(wrong)])==1
    failed_output=json.loads(capsys.readouterr().out)
    assert failed_output["status"]=="fail" and failed_output["fail"]==1


def test_source_digest_is_recomputed_not_taken_from_receipt(tmp_path: Path) -> None:
    _artifact(tmp_path, "source.sources", b"Types: deb\nURIs: http://ports.ubuntu.com/ubuntu-ports/\n")
    record = {"path": "source.sources", "sha256": "0" * 64}
    try:
        closure._artifact(tmp_path, record, "source")
    except ValueError as exc:
        assert "SHA256 receipt differs" in str(exc)
    else:
        raise AssertionError("tampered source digest receipt was accepted")


def test_decision_anchor_requires_external_trust_binding(tmp_path: Path) -> None:
    try:
        closure._decision(tmp_path, None, None)
    except closure.EvidenceMissing as exc:
        assert "externally approved profile decision" in str(exc)
    else:
        raise AssertionError("missing human decision anchor was accepted")


def test_keyring_inside_bundle_does_not_supply_external_decision_binding(tmp_path: Path) -> None:
    decision={"card_id":CARD,"profile":[{}],"freshness":{"source":{}},
              "subject":{"manufacturer":"x"}}
    row=_artifact(tmp_path,"decision.json",json.dumps(decision).encode())
    try:
        closure._decision(tmp_path,row,None)
    except closure.EvidenceMissing as exc:
        assert "external profile-decision SHA256" in str(exc)
    else:
        raise AssertionError("bundle-contained decision was treated as trusted")


def test_native_gpgv_helper_rejects_corrupt_manifest_bytes(tmp_path: Path) -> None:
    # gpgv itself is invoked over captured bytes; a JSON status claim cannot override it.
    keyring = Path("/usr/share/keyrings/ubuntu-archive-keyring.gpg")
    if not keyring.is_file():
        keyring = Path("/etc/apt/trusted.gpg")
    assert keyring.is_file()
    manifest = tmp_path / "unsigned.InRelease"
    manifest.write_bytes(b"Origin: fabricated\nSuite: noble\nSHA256:\n")
    result = apt_sources.verify_release_signature(manifest, [keyring])
    assert result["status"] != "pass"
    assert result["validsig_records"] == []


def test_isolated_update_recomputes_receipts_and_detects_negative_control() -> None:
    root = Path("/tmp/bb-apt-test-root")
    config_text = (f'Dir::Etc "{root}/etc";\nDir::State::lists "{root}/lists";\n'
                   f'Dir::Cache "{root}/cache";\nDir::Log "{root}/log";\n'
                   'APT::Update::Error-Mode "any";\nAcquire::AllowInsecureRepositories "0";\n'
                   'APT::Architecture "arm64";\n')
    config = {"argv": ["apt-config", "dump"], "exit_code": 0, "stdout": config_text, "stderr": ""}
    targets = {"argv": ["apt-get", "indextargets", "--format=x"], "exit_code": 0,
               "stdout": "", "stderr": ""}
    update = {"argv": ["apt-get", "update"], "exit_code": 100,
              "stdout": "404 archive.ubuntu.com/ubuntu binary-arm64/Packages", "stderr": ""}
    result = apt_sources.check_isolated_update_control(config, update, targets, root, "wrong_arm64_source")
    assert result["status"] == "pass"
    update["stdout"] = "update completed"
    result = apt_sources.check_isolated_update_control(config, update, targets, root, "wrong_arm64_source")
    assert result["status"] == "block"


def test_positive_healthy_update_and_release_index_are_recomputed() -> None:
    config={"argv":["apt-config","dump"],"exit_code":0,"stdout":"", "stderr":""}
    update={"argv":["apt-get","update"],"exit_code":0,"stdout":"Hit:1 ports.ubuntu.com", "stderr":""}
    targets={"argv":["apt-get","indextargets","--format=x"],"exit_code":0,
             "stdout":"ports.ubuntu.com/ubuntu-ports|noble|arm64|Packages", "stderr":""}
    # Config root validation still applies to a positive receipt.
    root=Path("/tmp/bb-apt-positive")
    config["stdout"]=(f'Dir::Etc "{root}/etc";\nDir::State::lists "{root}/lists";\n'
                      f'Dir::Cache "{root}/cache";\nDir::Log "{root}/log";\n'
                      'APT::Update::Error-Mode "any";\nAcquire::AllowInsecureRepositories "0";\n'
                      'APT::Architecture "arm64";\n')
    assert apt_sources.check_isolated_update_control(config,update,targets,root,"healthy")["status"]=="pass"
    index=b"Package: demo\nVersion: 1\n"
    payload=("SHA256:\n "+hashlib.sha256(index).hexdigest()+f" {len(index)} main/binary-arm64/Packages\n")
    assert apt_sources.check_release_index(payload,"main/binary-arm64/Packages",index)["status"]=="pass"
    assert apt_sources.check_release_index(payload,"main/binary-arm64/Packages",index+b"tampered")["status"]=="block"


def test_signed_policy_digest_alone_does_not_accept_incomplete_subject(tmp_path: Path) -> None:
    decision={"card_id":CARD,"profile":[{}],"freshness":{"source":{}},
              "subject":{"manufacturer":"GIGABYTE"}}
    raw=(json.dumps(decision)+"\n").encode()
    row=_artifact(tmp_path,"decision.json",raw)
    try:
        closure._decision(tmp_path,row,hashlib.sha256(raw).hexdigest())
    except closure.EvidenceMissing as exc:
        assert "complete exact subject/version tuple" in str(exc)
    else:
        raise AssertionError("incomplete exact subject tuple was accepted")


def test_native_target_derivation_includes_translation_dep11_cnf_and_excludes_disabled_icons(tmp_path: Path) -> None:
    source=b"Types: deb\nURIs: https://ports.ubuntu.com/ubuntu-ports\nSuites: noble\nComponents: main restricted\n"
    record=_artifact(tmp_path,"ubuntu.sources",source)
    record.update(source_id="ubuntu",selected_uri="https://ports.ubuntu.com/ubuntu-ports",selected_suite="noble")
    doc={"sources":[record]}
    config='''APT::Architecture "arm64";
APT::Architectures:: "arm64";
Acquire::Languages "en";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
Acquire::IndexTargets::deb::DEP-11::MetaKey "$(COMPONENT)/dep11/Components-$(NATIVE_ARCHITECTURE).yml";
Acquire::IndexTargets::deb::CNF::MetaKey "$(COMPONENT)/cnf/Commands-$(NATIVE_ARCHITECTURE)";
Acquire::IndexTargets::deb::icons-large::MetaKey "$(COMPONENT)/icons-64x64.tar";
Acquire::IndexTargets::deb::icons-large::DefaultEnabled "false";
'''
    derived=closure._expected_index_paths(doc,tmp_path,config)
    assert derived=={"ubuntu":{
        "main/binary-arm64/Packages","restricted/binary-arm64/Packages",
        "main/i18n/Translation-en","restricted/i18n/Translation-en",
        "main/dep11/Components-arm64.yml","restricted/dep11/Components-arm64.yml",
        "main/cnf/Commands-arm64","restricted/cnf/Commands-arm64"}}
    rows=closure._derive_target_rows(doc,tmp_path,config)
    assert {row["identifier"] for row in rows}=={"Packages","Translations","DEP-11","CNF"}
    assert not any("icons" in row["meta_key"] for row in rows)


def test_environment_translation_requires_native_locale_receipt(tmp_path: Path) -> None:
    config='''APT::Architecture "arm64";
Acquire::Languages "environment";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
'''
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"native locale capture"):
        closure._resolved_languages({},tmp_path,[],True)
    record=_artifact(tmp_path,"locale.json",b'{"argv":["locale"],"exit_code":0,"stdout":"LANGUAGE=es:en\\nLC_MESSAGES=es_MX.UTF-8\\n"}')
    assert closure._resolved_languages({"language_environment":record},tmp_path,[],True)==["es","en"]


def test_native_languages_none_disables_translation_target_without_cnr() -> None:
    config='''APT::Architecture "arm64";
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
'''
    target_config=closure._apt_target_definitions(config)
    assert target_config.languages==[] and target_config.environment_mode is False
    selected=closure._target_bindings({"types":"deb","components":"main"},target_config.definitions,target_config.languages,target_config.native_arch,target_config.configured_arches)
    assert set(selected)=={"Packages"}


def test_apt_target_parser_rejects_conflicting_duplicate_fields() -> None:
    config='''APT::Architecture "arm64";
Acquire::IndexTargets::deb::Packages::MetaKey "main/binary-arm64/Packages";
Acquire::IndexTargets::deb::Packages::MetaKey "other/binary-arm64/Packages";
'''
    with unittest.TestCase().assertRaisesRegex(ValueError,"conflicting duplicate"):
        closure._apt_target_definitions(config)


def test_native_arch_and_language_parsers_reject_missing_conflicts_and_unknown_modes() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"native architecture value absent"):
        closure._native_architecture('Acquire::Languages "none";')
    with unittest.TestCase().assertRaisesRegex(ValueError,"conflicting duplicate APT::Architecture"):
        closure._native_architecture('APT::Architecture "arm64";\nAPT::Architecture "amd64";')
    with unittest.TestCase().assertRaisesRegex(ValueError,"conflicting duplicate Acquire::Languages"):
        closure._configured_languages('Acquire::Languages "none";\nAcquire::Languages "en";')
    assert closure._configured_languages('Acquire::Languages "es";\nAcquire::Languages:: "en";') == (["es","en"],"es")


def test_source_targets_add_remove_and_disabled_explicit_selection() -> None:
    definitions={"deb":{
        "Packages":{"DefaultEnabled":"true","MetaKey":"$(COMPONENT)/Packages"},
        "DEP-11":{"DefaultEnabled":"false","MetaKey":"$(COMPONENT)/dep11"},
        "Translations":{"DefaultEnabled":"true","MetaKey":"$(COMPONENT)/Translation"}},
        "deb-src":{}}
    base={"types":"deb","components":"main"}
    assert closure._source_target_selection({**base,"targets-add":"DEP-11",
                                             "targets-remove":"Translations"},definitions)=={"Packages","DEP-11"}
    selected=closure._target_bindings({**base,"targets":"DEP-11"},definitions,[],"arm64",["arm64"])
    assert set(selected)=={"DEP-11"}
    assert selected["DEP-11"][0]["meta_key"]=="main/dep11"


def test_source_target_add_remove_requires_resolved_target_names() -> None:
    definitions={"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"do not resolve"):
        closure._source_target_selection({"types":"deb","targets-add":"MISSING"},definitions)


def test_source_target_selector_rejects_conflicts_and_malformed_tokens() -> None:
    definitions={"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}}
    invalid=(
        ({"types":"deb","targets":"Packages","targets-add":"Packages"},"cannot be combined"),
        ({"types":"deb","targets":"../Packages"},"malformed"),
        ({"types":"deb","targets":""},"empty"),
    )
    for stanza,reason in invalid:
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,reason):
            closure._source_target_selection(stanza,definitions)


def test_source_target_wildcard_is_not_mistaken_for_the_default_enabled_set() -> None:
    definitions={"deb":{"Packages":{"DefaultEnabled":"yes"},
                         "DEP-11":{"DefaultEnabled":"no"}},"deb-src":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"wildcard semantics"):
        closure._source_target_selection({"types":"deb","targets":"*"},definitions)


def test_source_target_unknown_default_state_returns_unknown() -> None:
    definitions={"deb":{"Packages":{"DefaultEnabled":"sometimes"}},"deb-src":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unresolved DefaultEnabled"):
        closure._source_target_selection({"types":"deb","targets-add":"Packages"},definitions)


def test_source_target_identifier_boolean_override_remains_unknown() -> None:
    definitions={"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"per-Identifier boolean"):
        closure._source_target_selection({"types":"deb","packages":"no"},definitions)


def test_target_binding_rejects_unresolved_types_and_unknown_meta_substitution() -> None:
    definitions={"deb":{"Packages":{"MetaKey":"$(COMPONENT)/$(UNSUPPORTED)/Packages"}},"deb-src":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unsupported APT source type"):
        closure._target_bindings({"types":"deb-unknown","components":"main"},definitions,[],"arm64",["arm64"])
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unsupported APT MetaKey"):
        closure._target_bindings({"types":"deb","components":"main"},definitions,[],"arm64",["arm64"])


def test_enabled_targets_rejects_missing_or_invalid_definitions() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"definitions unavailable"):
        closure._enabled_targets({"deb":{}},"deb",None)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unsupported APT source type"):
        closure._enabled_targets({"deb":{"Packages":{}}},"rpm",None)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"unresolved DefaultEnabled"):
        closure._enabled_targets({"deb":{"Packages":{"DefaultEnabled":"maybe"}}},"deb",None)


def test_native_apt_indextargets_confirms_add_remove_and_disabled_explicit_target(tmp_path: Path) -> None:
    apt_get=shutil.which("apt-get")
    assert apt_get is not None, "native APT executable required for source selector semantics test"
    lists=tmp_path/"lists"
    (lists/"partial").mkdir(parents=True)
    isolated_parts=tmp_path/"apt.conf.d"
    isolated_parts.mkdir()
    source=tmp_path/"test.sources"
    config=tmp_path/"apt.conf"
    config.write_text(f'''Dir::Etc::sourcelist "{source}";
Dir::Etc::sourceparts "-";
Dir::Etc::parts "{isolated_parts}";
Dir::State::lists "{lists}";
APT::Architecture "arm64";
APT::Architectures {{ "arm64"; }};
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
Acquire::IndexTargets::deb::DEP-11::MetaKey "$(COMPONENT)/dep11/Components-$(NATIVE_ARCHITECTURE).yml";
Acquire::IndexTargets::deb::DEP-11::DefaultEnabled "false";
''', encoding="utf-8")
    prefix='Types: deb\nURIs: file:/repo\nSuites: stable\nComponents: main\n'

    def target_rows(stanza: str) -> tuple[set[str], dict[str,str]]:
        source.write_text(stanza, encoding="utf-8")
        result=subprocess.run(
            [apt_get,"indextargets","--no-release-info",
             "--format=$(IDENTIFIER)|$(METAKEY)|$(DEFAULTENABLED)"],
            check=False,capture_output=True,text=True,timeout=10,
            env={**os.environ,"APT_CONFIG":str(config)})
        assert result.returncode==0, result.stderr
        return {line.split("|",1)[0] for line in result.stdout.splitlines()}, {
            "types":"deb","components":"main",
            **{key.strip().lower():value.strip() for key,value in
               (line.split(":",1) for line in stanza.splitlines() if ":" in line)}}

    added,added_stanza=target_rows(prefix+"Targets-Add: DEP-11\nTargets-Remove: Translations\n")
    assert "Packages" in added and "DEP-11" in added and "Translations" not in added
    defs={"deb":{"Packages":{"DefaultEnabled":"true"},
                  "Translations":{"DefaultEnabled":"true"},
                  "DEP-11":{"DefaultEnabled":"false"}},"deb-src":{}}
    assert closure._source_target_selection(added_stanza,defs)==added
    explicit,explicit_stanza=target_rows(prefix+"Targets: DEP-11\n")
    assert explicit=={"DEP-11"}
    assert closure._source_target_selection(explicit_stanza,defs)==explicit
    wildcard,wildcard_stanza=target_rows(prefix+"Targets: *\n")
    assert wildcard==set()
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"wildcard semantics"):
        closure._source_target_selection(wildcard_stanza,defs)


def test_native_apt_targets_remove_translations_against_languages_en_baseline(tmp_path: Path) -> None:
    apt_get=shutil.which("apt-get")
    assert apt_get is not None, "native APT executable required for target removal comparison"
    lists=tmp_path/"lists"
    (lists/"partial").mkdir(parents=True)
    parts=tmp_path/"apt.conf.d"
    parts.mkdir()
    source=tmp_path/"test.sources"
    config=tmp_path/"apt.conf"
    config.write_text(f'''Dir::Etc::sourcelist "{source}";
Dir::Etc::sourceparts "-";
Dir::Etc::main "-";
Dir::Etc::parts "{parts}";
Dir::State::lists "{lists}";
APT::Architecture "arm64";
APT::Architectures {{ "arm64"; }};
Acquire::Languages "en";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages";
Acquire::IndexTargets::deb::Translations::MetaKey "$(COMPONENT)/i18n/Translation-$(LANGUAGE)";
Acquire::IndexTargets::deb::DEP-11::MetaKey "$(COMPONENT)/dep11/Components-$(NATIVE_ARCHITECTURE).yml";
Acquire::IndexTargets::deb::DEP-11::DefaultEnabled "false";
''', encoding="utf-8")
    prefix="Types: deb\nURIs: file:/repo\nSuites: stable\nComponents: main\n"
    argv=[apt_get,"indextargets","--no-release-info","--format=$(IDENTIFIER)|$(METAKEY)"]

    source.write_text(prefix, encoding="utf-8")
    baseline=subprocess.run(argv,capture_output=True,text=True,check=False,timeout=10,
                            env={**os.environ,"APT_CONFIG":str(config)})
    assert baseline.returncode==0,baseline.stderr
    baseline_rows=baseline.stdout.splitlines()
    baseline_translations=[line for line in baseline_rows if line.startswith("Translations|")]
    assert baseline_translations, "configured English language must produce the native Translation target"

    source.write_text(prefix+"Targets-Remove: Translations\n", encoding="utf-8")
    removed=subprocess.run(argv,capture_output=True,text=True,check=False,timeout=10,
                           env={**os.environ,"APT_CONFIG":str(config)})
    assert removed.returncode==0,removed.stderr
    removed_rows=removed.stdout.splitlines()
    assert not any(line.startswith("Translations|") for line in removed_rows)
    assert any(line.startswith("Packages|") for line in removed_rows)

    definitions={"deb":{"Packages":{"DefaultEnabled":"true"},
                         "Translations":{"DefaultEnabled":"true"},
                         "DEP-11":{"DefaultEnabled":"false"}},"deb-src":{}}
    stanza={"types":"deb","components":"main","targets-remove":"Translations"}
    assert closure._source_target_selection(stanza,definitions)=={"Packages"}


def test_effective_index_target_parser_rejects_legacy_incomplete_rows() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"lacks required native fields"):
        closure._parse_effective_targets("Identifier: Packages\n")


def test_effective_index_target_parser_binds_all_target_fields() -> None:
    raw="""Repo-URI: https://ports.ubuntu.com/ubuntu-ports/
Suite: noble
Architecture: arm64
Identifier: DEP-11
MetaKey: main/dep11/Components-arm64.yml
Component: main
Target-Of: deb
"""
    rows=closure._parse_effective_targets(raw)
    assert rows==[{"uri":"https://ports.ubuntu.com/ubuntu-ports/","suite":"noble","architecture":"arm64",
                   "identifier":"DEP-11","meta_key":"main/dep11/Components-arm64.yml","component":"main",
                   "target_of":"deb"}]


def test_effective_index_target_parser_rejects_duplicate_fields() -> None:
    text="""Repo-URI: https://apt.invalid/repo/
Suite: stable
Suite: unstable
Architecture: arm64
Identifier: Packages
MetaKey: main/Packages
Component: main
Target-Of: deb
"""
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"malformed or duplicate"):
        closure._parse_effective_targets(text)
    valid="""Repo-URI: https://apt.invalid/repo/
Suite: stable
Architecture: arm64
Identifier: Packages
MetaKey: main/Packages
Component: main
Target-Of: deb
"""
    with unittest.TestCase().assertRaisesRegex(ValueError,"duplicate"):
        closure._parse_effective_targets(valid+"\n"+valid)


def test_decision_requires_nonempty_profile_and_freshness_with_exact_external_binding(tmp_path: Path) -> None:
    base={"card_id":CARD,"subject":{"manufacturer":"A","product":"B","bios":"C",
          "kernel":"D","architecture":"arm64","apt_version":"1","gpgv_version":"2"},
          "profile":[{"source_id":"x"}],"freshness":{"x":{"max_age_seconds":60}}}
    for field,value,reason in (("profile",[],"nonempty approved source profile"),
                               ("freshness",{},"per-source freshness policy")):
        doc={**base,field:value}
        raw=(json.dumps(doc)+"\n").encode()
        row=_artifact(tmp_path,f"decision-{field}.json",raw)
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,reason):
            closure._decision(tmp_path,row,hashlib.sha256(raw).hexdigest())


def test_subject_gate_distinguishes_untrusted_identity_from_missing_stack(tmp_path: Path) -> None:
    decision={"subject":{"manufacturer":"A","product":"B","bios":"C","kernel":"D",
                         "architecture":"arm64","apt_version":"1","gpgv_version":"2"}}
    missing=closure._subject_gate({},tmp_path,decision)
    assert missing["status"]=="could_not_run"
    malformed=_artifact(tmp_path,"bad-stack.json",b"[]")
    invalid=closure._subject_gate({"subject_stack":malformed},tmp_path,decision)
    assert invalid["status"]=="could_not_run" and "JSON object required" in invalid["reason"]
    incomplete=_artifact(tmp_path,"incomplete-stack.json",b'{"architecture":"arm64"}')
    unavailable=closure._subject_gate({"subject_stack":incomplete},tmp_path,decision)
    assert unavailable["status"]=="could_not_run"


def test_source_expansion_rejects_ambiguous_and_inactive_stanzas() -> None:
    config=closure.TargetConfig({"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    source={"selected_uri":"https://apt.invalid/repo","selected_suite":"stable"}
    stanza={"types":"deb","uris":"https://apt.invalid/repo","suites":"stable","components":"main"}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"multiple active stanza"):
        closure._expand_sources("repo",[stanza,stanza],source,config)
    assert closure._expand_sources("repo",[{**stanza,"enabled":"no"}],source,config)==[]
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"exact URI and suite"):
        closure._expand_sources("repo",[stanza],{},config)


def test_index_coverage_binds_exact_manifest_and_reports_missing_sources(tmp_path: Path) -> None:
    release=b"SHA256:\n"
    release_row=_artifact(tmp_path,"release",release)
    source=_baseline_source(tmp_path)
    config_text='''APT::Architecture "arm64";
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/Packages";
'''
    config=_artifact(tmp_path,"apt-config",config_text.encode())
    config.update(argv=["apt-config","dump"],exit_code=0,stdout_truncated=False,stderr_truncated=False)
    with unittest.TestCase().assertRaisesRegex(ValueError,"declared expected index paths"):
        closure._coverage_results({"coverage":[{"source":"repo"}],"apt_config_dump":config,
                                  "sources":[source]},tmp_path,{"repo":release},{"repo":set()})

    derived={"repo":{"main/Packages"}}
    context={"verified":{"repo":release},"observed":{"repo":[]},"derived":derived}
    wrong_manifest=_artifact(tmp_path,"other-release",b"different")
    with unittest.TestCase().assertRaisesRegex(ValueError,"not byte-bound"):
        closure._coverage_row(tmp_path,{"expected_meta_keys":["main/Packages"],
            "observed_meta_keys":[],"release":wrong_manifest},"repo",context)
    # The signed manifest remains explicitly required even for empty observed rows.
    correct={"expected_meta_keys":["main/Packages"],"observed_meta_keys":[],"release":release_row}
    with patch.object(apt_sources,"check_index_coverage",return_value={"status":"pass"}):
        assert closure._coverage_row(tmp_path,correct,"repo",context)["status"]=="pass"


def test_effective_target_derivation_returns_cnr_when_source_record_is_unbound(tmp_path: Path) -> None:
    config=closure.TargetConfig({"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    cases=((None,"source identity unavailable"),
           ({"source_id":"repo"},"artifact path record missing"),
           ({"source_id":"repo","path":"missing","sha256":"0"*64},"artifact unavailable"))
    for record,expected in cases:
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,expected):
            closure._derive_source_target_rows(record,tmp_path,config)


def test_fresh_state_rejects_preexisting_lists_bad_size_and_healthy_empty_result(tmp_path: Path) -> None:
    start="2026-10-04T00:00:00+00:00"
    finish="2026-10-04T00:00:01+00:00"
    state={"started_at":start,"finished_at":finish,"before":[],"after":[]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"required"):
        closure._canary_fresh_state(tmp_path,{},"healthy")
    with unittest.TestCase().assertRaisesRegex(ValueError,"healthy update did not create"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":state},"healthy")
    before=_artifact(tmp_path,"old-list",b"old")
    state_with_before={**state,"before":[{**before,"size":3,"mtime":finish}]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"not empty before"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":state_with_before},"wrong_arm64_source")
    after=_artifact(tmp_path,"bad-size-list",b"bytes")
    state_bad_size={**state,"after":[{**after,"size":4,"mtime":finish}]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"size mismatch"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":state_bad_size},"wrong_arm64_source")


def test_canary_source_binding_rejects_wrong_hash_and_wrong_endpoint(tmp_path: Path) -> None:
    baseline=_baseline_source(tmp_path)
    altered=_artifact(tmp_path,"altered.sources",b"Types: deb\nURIs: https://evil.invalid/\n")
    bad_hash={"source":altered,"source_sha256":"0"*64}
    with unittest.TestCase().assertRaisesRegex(ValueError,"hash binding mismatch"):
        closure._check_canary_source({"sources":[baseline]},tmp_path,"healthy",bad_hash)
    valid_hash={"source":altered,"source_sha256":altered["sha256"]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"differs from captured active"):
        closure._check_canary_source({"sources":[baseline]},tmp_path,"healthy",valid_hash)
    wrong=_wrong_source(tmp_path)
    closure._check_canary_source({"sources":[baseline]},tmp_path,"wrong_arm64_source",
                                 {"source":wrong,"source_sha256":wrong["sha256"]})


def test_canary_result_reports_unclassified_native_update_as_unknown(tmp_path: Path) -> None:
    row={"receipts":{}}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"artifact path record missing"):
        closure._canary_result({},tmp_path,"healthy",row)


def test_canary_fresh_state_bad_timestamp_and_nonhealthy_empty_window(tmp_path: Path) -> None:
    malformed={"started_at":"bad","finished_at":"also bad","before":[],"after":[]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"timestamps incomplete"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":malformed},"wrong_arm64_source")
    no_timezone={"started_at":"2026-10-04T00:00:00","finished_at":"2026-10-04T00:00:01",
                 "before":[],"after":[]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"timestamps incomplete"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":no_timezone},"wrong_arm64_source")


def test_capture_reader_classifies_directory_and_traversal_inputs(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"artifact unavailable"):
        closure._doc(tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"parent traversal"):
        closure._doc(tmp_path/".."/"outside.json")


def test_expected_index_paths_rejects_bad_source_bytes_and_missing_selection(tmp_path: Path) -> None:
    config='''APT::Architecture "arm64";
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/Packages";
'''
    malformed=_artifact(tmp_path,"malformed.sources",b"Types: deb\nTypes: deb\n")
    malformed.update(source_id="repo",selected_uri="https://apt.invalid/repo",selected_suite="stable")
    with unittest.TestCase().assertRaisesRegex(ValueError,"source parse errors"):
        closure._expected_index_paths({"sources":[malformed]},tmp_path,config)
    valid=_baseline_source(tmp_path)
    valid["selected_uri"]="https://other.invalid/"
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"does not select exactly one"):
        closure._expected_index_paths({"sources":[valid]},tmp_path,config)


def test_target_binding_rejects_duplicate_names_across_source_types() -> None:
    definitions={"deb":{"Packages":{"MetaKey":"main/Packages"}},
                 "deb-src":{"Packages":{"MetaKey":"main/source/Packages"}}}
    stanza={"types":"deb deb-src","components":"main"}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"ambiguous across source types"):
        closure._target_bindings(stanza,definitions,[],"arm64",["arm64"])


def test_target_template_rejects_unresolved_language_and_path_escape() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"language list is unresolved"):
        closure._expand_target_template("$(COMPONENT)/Translation-$(LANGUAGE)","Translations",
                                        {"components":"main"},([],"arm64",["arm64"]))
    with unittest.TestCase().assertRaisesRegex(ValueError,"escaped repository-relative path"):
        closure._expand_target_template("../Packages","Packages",{"components":"main"},([],"arm64",["arm64"]))


def test_source_profile_and_target_derivation_reject_malformed_source_record(tmp_path: Path) -> None:
    config=closure.TargetConfig({"deb":{"Packages":{"MetaKey":"main/Packages"}},"deb-src":{}},
                                [],"arm64",["arm64"],False)
    malformed=_artifact(tmp_path,"invalid-source",b"Types: deb\nTypes: deb\n")
    malformed.update(source_id="repo",selected_uri="https://apt.invalid/repo",selected_suite="stable")
    with unittest.TestCase().assertRaisesRegex(ValueError,"source parsing failed"):
        closure._derive_source_target_rows(malformed,tmp_path,config)
    source=_baseline_source(tmp_path)
    source["selected_uri"]="https://other.invalid/"
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"exactly one enabled stanza"):
        closure._derive_source_target_rows(source,tmp_path,config)


def test_negative_control_classifies_unknown_kind_and_requires_both_distinct_roots(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(ValueError,"unsupported integrity negative outcome"):
        closure._verify_negative_input({},tmp_path,{"outcome":"unknown"})
    rows=[{"outcome":"bad_package_hash","isolated_root":"/tmp/same"},
          {"outcome":"bad_release_signature","isolated_root":"/tmp/same"}]
    result=closure._negative_gate({"integrity_negative_canaries":rows},tmp_path)
    assert result["status"]=="fail" and "independent isolated roots" in result["reason"]


def test_bad_package_negative_requires_matching_baseline_and_actual_corruption(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source identity and MetaKey"):
        closure._verify_package_negative({},tmp_path,{})
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"one baseline signed index"):
        closure._verify_package_negative({"indexes":[]},tmp_path,{"source_id":"repo","meta_key":"Packages"})
    doc,anchor=_synthetic_bundle(tmp_path)
    del anchor
    row=doc["integrity_negative_canaries"][0]
    baseline={"source":row["source_id"],"meta_key":row["meta_key"],
              "content":doc["indexes"][0]["content"],"release":doc["indexes"][0]["release"]}
    same={**row,"negative_input":baseline["content"]}
    with unittest.TestCase().assertRaisesRegex(ValueError,"byte-identical"):
        closure._verify_package_negative({**doc,"indexes":[baseline]},tmp_path,same)


def test_signature_and_index_coverage_reject_wrong_source_duplicate_and_missing_artifacts(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"one source-bound"):
        closure._verify_signature_negative({"repositories":[]},tmp_path,{"source_id":"repo"})
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"raw index bytes"):
        closure._verified_index_rows({"indexes":[]},tmp_path,{"repo":b"release"})
    release=_artifact(tmp_path,"signed-release",b"release")
    repositories=[{"source":"repo","inrelease":release},{"source":"repo","inrelease":release}]
    with unittest.TestCase().assertRaisesRegex(ValueError,"malformed or duplicated"):
        closure._verified_releases({"repositories":repositories},tmp_path)


def test_rollback_and_cleanup_fail_on_state_drift_and_existing_isolated_root(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    altered=b'{"apt_config":"changed","keyrings":[],"package_state":"changed","sources":[]}'
    after=_artifact(tmp_path,"state-drift.json",altered)
    result=closure._rollback_gate({**doc,"rollback":{**doc["rollback"],"after":after}},tmp_path)
    assert result["status"]=="fail" and "digest map differs" in result["reason"]
    existing=tmp_path/"still-here"
    existing.mkdir()
    with unittest.TestCase().assertRaisesRegex(ValueError,"isolated APT root remains"):
        closure._verify_cleanup({"healthy_canary":{"isolated_root":str(existing)},
                                 "wrong_source_canary":{"isolated_root":"/tmp/absent"},
                                 "integrity_negative_canaries":[]},tmp_path,{})


def test_signature_gate_distinguishes_unavailable_signer_from_bad_signer(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    malformed={**doc["repositories"][0],"allowed_fingerprints":[]}
    result=closure._signature_gate({**doc,"repositories":[malformed]},tmp_path,decision)
    assert result["status"]=="could_not_run" and "fingerprint list" in result["reason"]
    invalid={**doc["repositories"][0],"allowed_fingerprints":["0"*40]}
    with patch.object(apt_sources,"verify_release_signature",return_value={"status":"pass","validsig_records":[]}):
        result=closure._signature_gate({**doc,"repositories":[invalid]},tmp_path,
                                       {**decision,"profile":[{**decision["profile"][0],
                                                               "allowed_fingerprints":["0"*40]}]})
    assert result["status"]=="fail" and result["sources"][0]["status"]=="fail"
    with patch.object(apt_sources,"verify_release_signature",return_value={"status":"unknown"}):
        result=closure._signature_gate(doc,tmp_path,decision)
    assert result["status"]=="could_not_run"


def test_source_gate_rejects_duplicate_derived_targets_and_empty_native_targets(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    duplicate={**doc,"sources":[doc["sources"][0],doc["sources"][0]]}
    duplicate_source=closure._source_gate(duplicate,tmp_path,decision)
    assert duplicate_source["status"]=="fail" and "duplicate effective target" in duplicate_source["reason"]

    raw=b""
    target=doc["effective_targets"]
    target_path=tmp_path/target["path"]
    target_path.write_bytes(raw)
    empty_targets={**target,"sha256":hashlib.sha256(raw).hexdigest()}
    result=closure._source_gate({**doc,"effective_targets":empty_targets},tmp_path,decision)
    assert result["status"]=="could_not_run" and "output is empty" in result["reason"]


def test_cleanup_and_rollback_report_missing_inventory_as_unknown(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"one raw cleanup verification"):
        closure._verify_cleanup({"healthy_canary":{"isolated_root":"/tmp/absent-a"},
                                 "wrong_source_canary":{"isolated_root":"/tmp/absent-b"},
                                 "integrity_negative_canaries":[]},tmp_path,{"cleanup_receipts":[]})
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source and keyring inventory"):
        closure._state_identity({},tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source keyring inventory"):
        closure._state_identity({"sources":[],"repositories":[]},tmp_path)


def test_canary_fresh_state_requires_array_inputs_and_timezone_aware_mtimes(tmp_path: Path) -> None:
    times={"started_at":"2026-10-04T00:00:00+00:00","finished_at":"2026-10-04T00:00:01+00:00"}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"must be arrays"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":{**times,"before":None,"after":[]}},"wrong_arm64_source")
    row=_artifact(tmp_path,"list",b"list")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"lacks timezone"):
        closure._canary_fresh_state(tmp_path,{"fresh_state":{**times,"before":[],"after":[
            {**row,"size":4,"mtime":"2026-10-04T00:00:02"}]}},"healthy")


def test_subject_gate_fails_for_decided_drift_and_checksum_tampering(tmp_path: Path) -> None:
    subject={"manufacturer":"A","product":"B","bios":"C","kernel":"D",
             "architecture":"arm64","apt_version":"1","gpgv_version":"2"}
    row=_artifact(tmp_path,"stack.json",(json.dumps(subject)+"\n").encode())
    incomplete_decision={"subject":{"manufacturer":"A"}}
    result=closure._subject_gate({"subject_stack":row},tmp_path,incomplete_decision)
    assert result["status"]=="could_not_run" and "fixed subject tuple" in result["reason"]
    drift={**subject,"kernel":"different"}
    decision={"subject":subject}
    drift_row=_artifact(tmp_path,"drift-stack.json",(json.dumps(drift)+"\n").encode())
    result=closure._subject_gate({"subject_stack":drift_row},tmp_path,decision)
    assert result["status"]=="fail" and "differs from externally fixed" in result["reason"]
    bad_receipt={**row,"sha256":"0"*64}
    result=closure._subject_gate({"subject_stack":bad_receipt},tmp_path,decision)
    assert result["status"]=="fail" and "SHA256 receipt differs" in result["reason"]


def test_source_target_helpers_return_unknown_without_required_native_context() -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"definitions required"):
        closure._source_target_selection({"types":"deb","targets-add":"Packages"})
    assert closure._identifier_overrides({"packages":"no"},None)==[]
    assert closure._source_target_selection({"types":"deb"},
            {"deb":{"Packages":{"DefaultEnabled":"true"}},"deb-src":{}}) is None


def test_expected_paths_require_exact_selected_uri_and_suite(tmp_path: Path) -> None:
    config='''APT::Architecture "arm64";
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/Packages";
'''
    source=_baseline_source(tmp_path)
    source.pop("selected_suite")
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"one URI/suite tuple"):
        closure._expected_index_paths({"sources":[source]},tmp_path,config)


def test_locale_receipt_with_nontext_output_stays_unknown(tmp_path: Path) -> None:
    row=_artifact(tmp_path,"locale-invalid.json",b'{"argv":["locale"],"exit_code":0,"stdout":false}')
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"locale output unavailable"):
        closure._resolved_languages({"language_environment":row},tmp_path,[],True)


def test_index_verification_separates_digest_failure_from_unavailable_tool(tmp_path: Path) -> None:
    release=_artifact(tmp_path,"release-index",b"signed release")
    content=_artifact(tmp_path,"index-content",b"index")
    row={"source":"repo","meta_key":"main/Packages","release":release,"content":content}
    with patch.object(apt_sources,"check_release_index",return_value={"status":"block"}):
        with unittest.TestCase().assertRaisesRegex(ValueError,"differs from signed Release"):
            closure._verified_index_rows({"indexes":[row]},tmp_path,{"repo":b"signed release"})
    with patch.object(apt_sources,"check_release_index",return_value={"status":"could_not_run"}):
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"could not run"):
            closure._verified_index_rows({"indexes":[row]},tmp_path,{"repo":b"signed release"})


def test_coverage_records_reject_malformed_and_duplicate_repository_rows(tmp_path: Path) -> None:
    config=_artifact(tmp_path,"apt-config",b'APT::Architecture "arm64";\nAcquire::Languages "none";\nAcquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/Packages";')
    config.update(argv=["apt-config","dump"],exit_code=0,stdout_truncated=False,stderr_truncated=False)
    source=_baseline_source(tmp_path)
    common={"apt_config_dump":config,"sources":[source]}
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"row must be an object"):
        closure._coverage_results({**common,"coverage":[None]},tmp_path,{"fixture":b"rel"},{"fixture":set()})
    with unittest.TestCase().assertRaisesRegex(ValueError,"absent, unexpected, or duplicated"):
        closure._coverage_results({**common,"coverage":[{"source":"unexpected"}]},
                                  tmp_path,{"fixture":b"rel"},{"fixture":set()})


def test_target_derivation_unknown_when_no_target_is_enabled(tmp_path: Path) -> None:
    source=_baseline_source(tmp_path)
    config='''APT::Architecture "arm64";
Acquire::Languages "none";
Acquire::IndexTargets::deb::Packages::MetaKey "$(COMPONENT)/Packages";
Acquire::IndexTargets::deb::Packages::DefaultEnabled "no";
'''
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"no enabled targets"):
        closure._derive_target_rows({"sources":[source]},tmp_path,config)


def test_freshness_gate_rejects_release_rebinding_and_bad_clock_receipts(tmp_path: Path) -> None:
    doc,anchor=_synthetic_bundle(tmp_path)
    decision=closure._decision(tmp_path,doc["decision_anchor"],anchor)
    wrong_release=_artifact(tmp_path,"different-inrelease",b"different")
    row={**doc["freshness"][0],"release":wrong_release}
    result=closure._freshness_gate({**doc,"freshness":[row]},tmp_path,decision)
    assert result["status"]=="fail" and "Release bytes differ" in result["reason"]
    clock=_artifact(tmp_path,"bad-clock.json",b'{"argv":["date"],"exit_code":1,"stdout":"","stdout_truncated":false,"stderr_truncated":false}')
    row={**doc["freshness"][0],"clock":clock}
    result=closure._freshness_gate({**doc,"freshness":[row]},tmp_path,decision)
    assert result["status"]=="could_not_run" and "date command receipt" in result["reason"]


def test_integrity_negative_gate_requires_both_named_control_classes() -> None:
    result=closure._negative_gate({"integrity_negative_canaries":[]},Path("/tmp"))
    assert result["status"]=="could_not_run" and "both package-hash" in result["reason"]


def test_negative_package_and_signature_controls_reject_neutralized_bad_inputs(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["integrity_negative_canaries"][0]
    baseline={"source":row["source_id"],"meta_key":row["meta_key"],
              "content":doc["indexes"][0]["content"],"release":doc["indexes"][0]["release"]}
    with patch.object(apt_sources,"check_release_index",side_effect=[{"status":"pass"},{"status":"pass"}]):
        with unittest.TestCase().assertRaisesRegex(ValueError,"does not conflict"):
            closure._verify_package_negative({**doc,"indexes":[baseline]},tmp_path,row)
    signature_row=doc["integrity_negative_canaries"][1]
    with patch.object(apt_sources,"verify_release_signature",return_value={"status":"pass","validsig_records":[]}):
        with unittest.TestCase().assertRaisesRegex(ValueError,"still verifies"):
            closure._verify_signature_negative(doc,tmp_path,signature_row)


def test_safety_gate_rejects_unsafe_config_and_install_actions(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    safety=doc["safety"]
    unsafe=_artifact(tmp_path,"unsafe-config",b'APT::Update::Pre-Invoke "touch /tmp/unsafe";\n')
    result=closure._safety_gate({**doc,"safety":{**safety,"config":unsafe}},tmp_path)
    assert result["status"]=="fail" and "unsafe isolated config" in result["reason"]

    canary=doc["healthy_canary"]
    receipt=canary["receipts"]["update"]
    command=json.loads((tmp_path/receipt["path"]).read_text(encoding="utf-8"))
    command["argv"]=["apt-get","install","package"]
    raw=(json.dumps(command)+"\n").encode()
    install_receipt=_artifact(tmp_path,"install-command.json",raw)
    altered_canary={**canary,"receipts":{**canary["receipts"],"update":install_receipt}}
    result=closure._safety_gate({**doc,"healthy_canary":altered_canary},tmp_path)
    assert result["status"]=="fail" and "install/upgrade action" in result["reason"]


def test_rollback_gate_requires_complete_state_fields_and_detects_byte_drift(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    rollback=doc["rollback"]
    incomplete=_artifact(tmp_path,"state-incomplete",b'{"sources":[]}')
    result=closure._rollback_gate({**doc,"rollback":{**rollback,"before":incomplete}},tmp_path)
    assert result["status"]=="could_not_run" and "bind source, keyring" in result["reason"]

    state=json.loads((tmp_path/rollback["before"]["path"]).read_text(encoding="utf-8"))
    after=_artifact(tmp_path,"state-format-drift",(json.dumps(state,indent=2)+"\n").encode())
    result=closure._rollback_gate({**doc,"rollback":{**rollback,"after":after}},tmp_path)
    assert result["status"]=="fail" and "host state bytes differ" in result["reason"]


def test_canary_source_requires_baseline_source_inventory(tmp_path: Path) -> None:
    source=_baseline_source(tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"configured source bytes unavailable"):
        closure._check_canary_source({},tmp_path,"wrong_arm64_source",
                                     {"source":source,"source_sha256":source["sha256"]})


def test_empty_configuration_decision_and_canary_receipt_shapes_remain_unknown(tmp_path: Path) -> None:
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"source-to-Release"):
        closure._verified_releases({"repositories":[]},tmp_path)
    with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"apt-config/update/targets"):
        closure._canary_result({},tmp_path,"healthy",{"receipts":None})


def test_document_reader_converts_path_resolution_oserror_to_could_not_run(tmp_path: Path) -> None:
    with patch.object(Path,"absolute",side_effect=OSError("path lookup failed")):
        with unittest.TestCase().assertRaisesRegex(closure.EvidenceMissing,"capture unavailable: OSError"):
            closure._doc(tmp_path/"capture.json")


def test_index_gate_and_safety_gate_preserve_missing_evidence_as_unknown(tmp_path: Path) -> None:
    index=closure._index_gate({"repositories":[]},tmp_path)
    assert index["status"]=="could_not_run"
    safety=closure._safety_gate({},tmp_path)
    assert safety["status"]=="could_not_run" and "safety receipts absent" in safety["reason"]


def test_locale_parser_ignores_unrelated_nonassignment_lines(tmp_path: Path) -> None:
    raw=(json.dumps({"argv":["locale"],"exit_code":0,"stdout":"locale output\nLANGUAGE=fr:en\n"})+"\n").encode()
    row=_artifact(tmp_path,"locale-lines.json",raw)
    assert closure._resolved_languages({"language_environment":row},tmp_path,[],True)==["fr","en"]


def test_canary_result_preserves_block_outcome_without_misreporting_pass(tmp_path: Path) -> None:
    doc,_=_synthetic_bundle(tmp_path)
    row=doc["healthy_canary"]
    with patch.object(apt_sources,"check_isolated_update_control",return_value={"status":"block"}):
        result=closure._canary_result(doc,tmp_path,"healthy",row)
    assert result["status"]=="fail" and result["result"]["status"]=="block"
