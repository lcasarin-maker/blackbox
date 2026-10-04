"""Evidence-first close selector for the generated APT arm64 source finding.

Bundle paths and command transcripts are caller supplied. The verifier recomputes
all classifications from bounded bytes; SHA receipts establish consistency,
while GPG verification establishes only cryptographic validity under supplied
keyrings. Authority for those keyrings/profile decisions remains external.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys
from typing import Any, NamedTuple

from tools import apt_sources
from tools.capture_io import read_regular_bytes, strict_json_loads

CARD_ID = "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01"
MAX_BYTES = 8 * 1024 * 1024
GATES = (
    "subject_stack", "approved_profile_and_freshness_policy", "configured_source_coverage",
    "signature_key_and_source_binding", "effective_index_integrity_and_coverage",
    "signed_release_freshness", "fresh_isolated_update", "wrong_source_negative",
    "integrity_negatives", "safety_and_input_binding", "rollback_and_cleanup",
    "aggregate_selector",
)
UNIMPLEMENTED_CRITERIA = [
    "The external decision SHA must come from the recorded human approval channel; the CLI verifies that supplied digest but cannot authenticate the person or approval system supplying it.",
    "Canary source/config transcripts are caller-supplied and hash-bound; no trusted host attestation proves the isolated APT process consumed those exact bytes.",
    "The native subject stack capture is caller-supplied; no attestation binds BIOS/stack fields to a measured physical host.",
    "Native UTC command and package-list mtimes are caller-supplied receipts; the verifier binds them but has no external trusted clock authority.",
    "Deb822 per-Identifier boolean target overrides remain could_not_run: the local apt-get 2.8.3 native probe ignored those fields, so the selector refuses to infer their effect.",
]


class EvidenceMissing(Exception):
    pass


class TargetConfig(NamedTuple):
    definitions: dict[str,dict[str,dict[str,str]]]
    languages: list[str]
    native_arch: str
    configured_arches: list[str]
    environment_mode: bool


def _gate(name: str, status: str, reason: str, **details: Any) -> dict[str, Any]:
    return {"gate": name, "status": status, "reason": reason, **details}


def _read(path: Path, root: Path) -> bytes:
    # Keep lexical ancestry: resolve() would silently bless a symlinked root.
    if ".." in path.parts or ".." in root.parts:
        raise EvidenceMissing(f"artifact path contains parent traversal: {path}")
    root_path = Path(path.absolute().anchor) / Path(*root.absolute().parts[1:])
    absolute_path = Path(path.absolute().anchor) / Path(*path.absolute().parts[1:])
    try:
        parts = absolute_path.relative_to(root_path).parts
    except ValueError as exc:
        raise EvidenceMissing(f"artifact escapes evidence root: {path}") from exc
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise EvidenceMissing(f"artifact path is malformed: {path}")
    try:
        raw = read_regular_bytes(absolute_path, MAX_BYTES)
    except OSError as exc:
        raise EvidenceMissing(f"artifact unavailable: {path}: {type(exc).__name__}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise EvidenceMissing(f"artifact exceeds {MAX_BYTES} byte cap: {path}")
    return raw


def _artifact(root: Path, row: Any, label: str) -> tuple[bytes, Path]:
    if not isinstance(row, dict) or not isinstance(row.get("path"), str):
        raise EvidenceMissing(f"{label}: artifact path record missing")
    path = root / row["path"]
    raw = _read(path, root)
    digest = hashlib.sha256(raw).hexdigest()
    if row.get("sha256") != digest:
        raise ValueError(f"{label}: SHA256 receipt differs from captured bytes")
    return raw, path


def _captured_command_output(doc: dict[str,Any], root: Path, field: str,
                            argv: list[str], label: str) -> bytes:
    row=doc.get(field)
    if not isinstance(row,dict) or row.get("argv")!=argv:
        raise EvidenceMissing(f"{label}: exact native command argv receipt required")
    if type(row.get("exit_code")) is not int or row["exit_code"]!=0:
        raise EvidenceMissing(f"{label}: command must have successful integer return code")
    if type(row.get("stdout_truncated")) is not bool or type(row.get("stderr_truncated")) is not bool:
        raise EvidenceMissing(f"{label}: explicit truncation booleans required")
    if row["stdout_truncated"] or row["stderr_truncated"]:
        raise EvidenceMissing(f"{label}: truncated command output cannot support a closure decision")
    raw,_=_artifact(root,row,label)
    return raw


def _json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise EvidenceMissing(f"{label}: malformed JSON: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise EvidenceMissing(f"{label}: JSON object required")
    return value


def _doc(path: Path) -> tuple[dict[str, Any], Path]:
    try:
        absolute = Path(path.absolute().anchor) / Path(*path.absolute().parts[1:])
        if ".." in path.parts:
            raise EvidenceMissing("capture path contains parent traversal")
        root = absolute.parent
        raw = _read(absolute, root)
    except (OSError, RecursionError) as exc:
        raise EvidenceMissing(f"capture unavailable: {type(exc).__name__}: {exc}") from exc
    return _json_bytes(raw, "capture"), root


def _decision(root: Path, row: Any, anchor_sha256: str | None) -> dict[str, Any]:
    """Bind the decision bytes to a digest from the external approval channel."""
    if not isinstance(row, dict):
        raise EvidenceMissing("externally approved profile decision record required")
    if not isinstance(anchor_sha256,str) or re.fullmatch(r"[0-9a-f]{64}",anchor_sha256) is None:
        raise EvidenceMissing("external profile-decision SHA256 trust binding required")
    raw,_=_artifact(root,row,"profile decision")
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(),anchor_sha256):
        raise ValueError("profile decision bytes differ from external trust binding")
    decision=_json_bytes(raw,"profile decision")
    if not isinstance(decision, dict) or decision.get("card_id") != CARD_ID:
        raise ValueError("profile decision is bound to a different card")
    required_subject={"manufacturer","product","bios","kernel","architecture","apt_version","gpgv_version"}
    subject=decision.get("subject")
    if not isinstance(subject,dict) or set(subject)!=required_subject or any(not isinstance(value,str) or not value.strip() for value in subject.values()):
        raise EvidenceMissing("external decision lacks the complete exact subject/version tuple")
    if not isinstance(decision.get("profile"), list) or not decision["profile"]:
        raise EvidenceMissing("signed decision lacks a nonempty approved source profile")
    if not isinstance(decision.get("freshness"), dict) or not decision["freshness"]:
        raise EvidenceMissing("signed decision lacks per-source freshness policy")
    return decision


def _profile_matches(actual: list[dict[str, Any]], approved: list[Any]) -> tuple[bool, list[str]]:
    keys = ("source_id", "uri", "suite", "architecture", "types", "components", "signed_by")
    errors: list[str] = []
    if any(not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in keys) for row in approved):
        return False, ["approved profile rows malformed"]
    normalize = lambda rows: {tuple(row.get(k, "") for k in keys) for row in rows}
    unexpected, missing = normalize(actual) - normalize(approved), normalize(approved) - normalize(actual)
    if unexpected:
        errors.append(f"unapproved configured source tuples: {len(unexpected)}")
    if missing:
        errors.append(f"approved source tuples missing: {len(missing)}")
    return not errors, errors


def _subject_gate(doc: dict[str, Any], root: Path, decision: dict[str, Any] | None) -> dict[str, Any]:
    try:
        if decision is None:
            raise EvidenceMissing("external exact subject/version decision unavailable")
        raw, _ = _artifact(root, doc.get("subject_stack"), "native subject stack")
        stack = _json_bytes(raw, "native subject stack")
        fields = ("manufacturer", "product", "bios", "kernel", "architecture", "apt_version", "gpgv_version")
        if any(not isinstance(stack.get(key), str) or not stack[key].strip() for key in fields):
            raise EvidenceMissing("native stack identity/version fields incomplete")
        if stack["architecture"] != "arm64":
            return _gate("subject_stack", "fail", "captured host architecture is not arm64", observed=stack)
        fixed = decision.get("subject")
        if not isinstance(fixed,dict) or set(fixed)!=set(fields):
            raise EvidenceMissing("trusted decision lacks complete fixed subject tuple")
        if any(stack.get(key)!=fixed.get(key) for key in fields):
            return _gate("subject_stack", "fail", "native stack differs from externally fixed exact subject", observed=stack)
        return _gate("subject_stack", "pass", "native stack bytes and exact subject fields match", observed=stack)
    except EvidenceMissing as exc:
        return _gate("subject_stack", "could_not_run", str(exc))
    except ValueError as exc:
        return _gate("subject_stack", "fail", str(exc))


def _decision_gate(doc: dict[str, Any], root: Path, anchor_sha256: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        decision = _decision(root, doc.get("decision_anchor"),anchor_sha256)
        return _gate("approved_profile_and_freshness_policy", "pass", "decision bytes match external trust binding"), decision
    except EvidenceMissing as exc:
        return _gate("approved_profile_and_freshness_policy", "could_not_run", str(exc)), None
    except ValueError as exc:
        return _gate("approved_profile_and_freshness_policy", "fail", str(exc)), None


def _read_configured_sources(doc: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    config=_captured_command_output(doc,root,"apt_config_dump",["apt-config","dump"],"apt-config dump")
    config_text=config.decode("utf-8")
    target_config=_apt_target_definitions(config_text)
    if target_config.native_arch!="arm64":
        raise ValueError("apt-config native architecture is not arm64")
    records = doc.get("sources")
    if not isinstance(records, list) or not records:
        raise EvidenceMissing("active source files and raw bytes required")
    actual=[]
    for record in records:
        source_id=record.get("source_id") if isinstance(record,dict) else None
        if not isinstance(source_id,str) or not source_id:
            raise EvidenceMissing("configured source artifact must carry a source_id binding")
        raw,_=_artifact(root,record,"configured source")
        stanzas,errors=apt_sources.parse_deb822(raw.decode("utf-8"))
        if errors:
            raise ValueError("configured source parse errors: "+"; ".join(errors))
        actual.extend(_expand_sources(source_id,stanzas,record,target_config))
    return actual


def _expand_sources(source_id: str, stanzas: list[dict[str,str]], record: dict[str,Any],
                    target_config: TargetConfig) -> list[dict[str,Any]]:
    selected_uri=record.get("selected_uri")
    selected_suite=record.get("selected_suite")
    if not isinstance(selected_uri,str) or not isinstance(selected_suite,str):
        raise EvidenceMissing("each source artifact must bind one exact URI and suite")
    selected=[stanza for stanza in stanzas if stanza.get("enabled","yes").lower()!="no"
              and selected_uri in stanza.get("uris","").split()
              and selected_suite in stanza.get("suites","").split()]
    if len(selected)>1:
        raise EvidenceMissing("source record selects multiple active stanza definitions")
    return _source_profile_rows(source_id,selected[0],selected_uri,selected_suite,
                                 target_config) if selected else []


def _source_profile_rows(source_id: str, stanza: dict[str,str], uri: str, suite: str,
                          target_config: TargetConfig) -> list[dict[str,Any]]:
    types=stanza.get("types","").split()
    if not set(types).intersection({"deb","deb-src"}):
        raise ValueError("active source has no supported deb type")
    targets=_source_target_selection(stanza,target_config.definitions)
    configured_arches=target_config.configured_arches
    architectures=stanza.get("architectures","").split() or configured_arches
    architectures=sorted((set(architectures)|set(stanza.get("architectures-add","").split()))-
                         set(stanza.get("architectures-remove","").split()))
    return [{"source_id":source_id,"uri":apt_sources._safe_uri(uri) or uri,
             "suite":suite,"architecture":arch,"types":" ".join(types),
             "components":" ".join(stanza.get("components","").split()),
             "signed_by":stanza.get("signed-by",""),"target_names":targets}
            for arch in architectures]


def _expected_index_paths(doc: dict[str, Any], root: Path, config_text: str) -> dict[str,set[str]]:
    """Derive enabled MetaKey paths per source using native APT target definitions."""
    records=doc.get("sources")
    if not isinstance(records,list) or not records:
        raise EvidenceMissing("source bytes unavailable for deriving expected index paths")
    target_config=_apt_target_definitions(config_text)
    languages=_resolved_languages(doc,root,target_config.languages,target_config.environment_mode)
    expected:dict[str,set[str]]={}
    for record in records:
        source_id=record.get("source_id") if isinstance(record,dict) else None
        if not isinstance(source_id,str) or not source_id:
            raise EvidenceMissing("source artifact must bind its exact repository id")
        raw,_=_artifact(root,record,"configured source")
        stanzas,errors=apt_sources.parse_deb822(raw.decode("utf-8"))
        if errors:
            raise ValueError("source parse errors prevent index derivation")
        selected_uri=record.get("selected_uri")
        selected_suite=record.get("selected_suite")
        if not isinstance(selected_uri,str) or not isinstance(selected_suite,str):
            raise EvidenceMissing("source record must name one URI/suite tuple")
        selected=[stanza for stanza in stanzas if stanza.get("enabled","yes").lower()!="no"
                  and selected_uri in stanza.get("uris","").split()
                  and selected_suite in stanza.get("suites","").split()]
        if len(selected)!=1:
            raise EvidenceMissing("source record does not select exactly one active stanza")
        expected.setdefault(source_id,set()).update(
            key for keys in _enabled_meta_keys(selected[0],target_config.definitions,languages,
                                               target_config.native_arch,target_config.configured_arches).values()
            for key in keys
        )
    if not expected or any(not paths for paths in expected.values()):
        raise EvidenceMissing("no enabled index MetaKeys could be derived")
    return expected


def _source_target_selection(
    stanza: dict[str,str],
    definitions: dict[str,dict[str,dict[str,str]]] | None = None,
) -> set[str] | None:
    """Resolve source target set using APT's multivalue default/add/remove rules.

    Explicit Targets replaces the default set and can enable DefaultEnabled=no
    entries. Targets-Add/Remove modify the configured default set. Their
    combination with explicit Targets and per-Identifier boolean fields remains
    unknown until this APT version exposes unambiguous native semantics.
    """
    raw=stanza.get("targets")
    added=stanza.get("targets-add","").split()
    removed=stanza.get("targets-remove","").split()
    identifiers=_identifier_overrides(stanza,definitions)
    if identifiers:
        raise EvidenceMissing("per-Identifier boolean target overrides require a native semantic binding")
    if raw is None and not added and not removed:
        return None
    if raw is not None and raw.strip()=="*":
        raise EvidenceMissing("APT Targets wildcard semantics produce no native rows in the local version")
    explicit=None if raw is None else raw.split()
    if explicit is not None and (added or removed):
        raise EvidenceMissing("APT Targets cannot be combined with Targets-Add/Targets-Remove without captured native precedence")
    tokens=[*(explicit or []),*added,*removed]
    if any(not re.fullmatch(r"[A-Za-z0-9._+-]+",item) for item in tokens):
        raise EvidenceMissing("APT Targets selector value is malformed")
    if explicit is not None and not explicit:
        raise EvidenceMissing("APT Targets selector is empty")
    if definitions is None:
        raise EvidenceMissing("apt-config definitions required to resolve Targets-Add/Targets-Remove")
    kinds=stanza.get("types","").split()
    available={name for kind in kinds for name in definitions.get(kind,{})}
    if set(tokens)-available:
        raise EvidenceMissing("APT target selector names do not resolve in captured apt-config definitions")
    if explicit is not None:
        return set(explicit)
    return (_default_enabled_targets(kinds,definitions)|set(added))-set(removed)


def _identifier_overrides(
    stanza: dict[str,str], definitions: dict[str,dict[str,dict[str,str]]] | None,
) -> list[str]:
    if definitions is None:
        return []
    identifiers={name.casefold() for per_type in definitions.values() for name in per_type}
    return [name for name in stanza if name.casefold() in identifiers]


def _default_enabled_targets(
    kinds: list[str], definitions: dict[str,dict[str,dict[str,str]]],
) -> set[str]:
    enabled=set()
    allowed=("true","yes","1","false","no","0")
    for kind in kinds:
        for name,fields in definitions.get(kind,{}).items():
            value=fields.get("DefaultEnabled","true").lower()
            if value not in allowed:
                raise EvidenceMissing(f"APT target {name} has unresolved DefaultEnabled value")
            if value in ("true","yes","1"):
                enabled.add(name)
    return enabled


def _apt_target_definitions(config_text: str) -> TargetConfig:
    definitions=_parse_target_definitions(config_text)
    languages,language_mode=_configured_languages(config_text)
    if language_mode == "none":
        languages=[]
        for targets in definitions.values():
            for name,fields in targets.items():
                if "Translation" in name:
                    fields["DefaultEnabled"]="false"
    elif language_mode and language_mode not in ("environment", "default"):
        languages=list(dict.fromkeys([*languages,language_mode]))
    native=_native_architecture(config_text)
    architectures=re.findall(r'^APT::Architectures:: "([^"]+)";$',config_text,re.MULTILINE) or [native]
    return TargetConfig(definitions,languages,native,architectures,
                        language_mode in ("environment", "default"))


def _parse_target_definitions(config_text: str) -> dict[str,dict[str,dict[str,str]]]:
    definitions:dict[str,dict[str,dict[str,str]]] = {"deb":{},"deb-src":{}}
    pattern=re.compile(r'^Acquire::IndexTargets::(deb(?:-src)?)::([^:]+)::([^:]+) "(.*)";$')
    for line in config_text.splitlines():
        match=pattern.fullmatch(line)
        if match:
            source_type,name,key,value=match.groups()
            fields=definitions[source_type].setdefault(name,{})
            if key in fields and fields[key]!=value:
                raise ValueError(f"conflicting duplicate apt-config target value: {source_type}/{name}/{key}")
            fields[key]=value
    if not any(definitions.values()):
        raise EvidenceMissing("raw apt-config dump lacks Acquire::IndexTargets definitions")
    return definitions


def _native_architecture(config_text: str) -> str:
    values=re.findall(r'^APT::Architecture "([^"]+)";$',config_text,re.MULTILINE)
    if not values:
        raise EvidenceMissing("apt-config native architecture value absent")
    if len(set(values))!=1:
        raise ValueError("conflicting duplicate APT::Architecture values")
    return values[0]

def _configured_languages(config_text: str) -> tuple[list[str],str]:
    languages=[]
    modes=[]
    for line in config_text.splitlines():
        match=re.fullmatch(r'Acquire::Languages:: "([^"]+)";',line)
        if match:
            languages.append(match.group(1))
            continue
        match=re.fullmatch(r'Acquire::Languages "([^"]+)";',line)
        if match:
            modes.append(match.group(1))
    if len(set(modes))>1:
        raise ValueError("conflicting duplicate Acquire::Languages values")
    language_mode=modes[0] if modes else ""
    if language_mode=="none":
        return [],language_mode
    if language_mode and language_mode not in ("environment","default"):
        return list(dict.fromkeys([language_mode,*languages])),language_mode
    return languages,language_mode


def _resolved_languages(doc: dict[str,Any], root: Path, languages: list[str], environment_mode: bool) -> list[str]:
    if not environment_mode:
        return languages
    record=doc.get("language_environment")
    if not isinstance(record,dict):
        raise EvidenceMissing("native locale capture required to resolve APT environment translation targets")
    raw,_=_artifact(root,record,"native locale")
    capture=_json_bytes(raw,"native locale")
    if capture.get("argv") != ["locale"] or type(capture.get("exit_code")) is not int or capture["exit_code"]!=0:
        raise EvidenceMissing("successful native locale command receipt required")
    stdout=capture.get("stdout")
    if not isinstance(stdout,str):
        raise EvidenceMissing("native locale output unavailable")
    values={}
    for line in stdout.splitlines():
        key,separator,value=line.partition("=")
        if separator and key in ("LANGUAGE","LC_MESSAGES","LANG"):
            values[key]=value.strip().strip('"')
    selected=values.get("LANGUAGE","").split(":")
    if not selected or not selected[0]:
        locale=values.get("LC_MESSAGES",values.get("LANG",""))
        selected=[locale.split(".")[0].split("_")[0]] if locale else []
    selected=[item for item in selected if re.fullmatch(r"[A-Za-z]{2,3}(?:_[A-Za-z]{2,3})?",item)]
    if not selected:
        raise EvidenceMissing("native locale did not resolve an APT translation language")
    return list(dict.fromkeys([*selected,*languages]))


def _enabled_meta_keys(stanza: dict[str,str], definitions: dict[str,dict[str,dict[str,str]]],
                       languages: list[str], native_arch: str, configured_arches: list[str]) -> dict[str,set[str]]:
    return {name:{row["meta_key"] for row in bindings}
            for name,bindings in _target_bindings(stanza,definitions,languages,native_arch,configured_arches).items()}


def _target_bindings(stanza: dict[str,str], definitions: dict[str,dict[str,dict[str,str]]],
                     languages: list[str], native_arch: str, configured_arches: list[str]) -> dict[str,list[dict[str,str]]]:
    metas:dict[str,list[dict[str,str]]]={}
    # _source_target_selection validates every explicit/add/remove name against
    # this same stanza type set before it returns a selection.
    selected=_source_target_selection(stanza,definitions)
    for kind in stanza.get("types","").split():
        for name,fields in _enabled_targets(definitions,kind,selected):
            template=fields.get("MetaKey")
            if template:
                if name in metas:
                    raise EvidenceMissing(f"APT target identifier {name} is ambiguous across source types")
                metas[name]=[{**binding,"target_of":kind} for binding in
                             _expand_target_template(template,name,stanza,(languages,native_arch,configured_arches))]
    return metas


def _enabled_targets(definitions: dict[str,dict[str,dict[str,str]]], kind: str,
                     selected: set[str] | None) -> list[tuple[str,dict[str,str]]]:
    if kind not in ("deb","deb-src"):
        raise EvidenceMissing(f"unsupported APT source type {kind}")
    if not definitions.get(kind):
        raise EvidenceMissing(f"apt-config target definitions unavailable for source type {kind}")
    output=[]
    for name,fields in definitions.get(kind,{}).items():
        enabled=fields.get("DefaultEnabled","true").lower()
        if selected is not None:
            if name in selected:
                output.append((name,fields))
            continue
        if enabled in ("false","no","0"):
            continue
        if enabled not in ("true","yes","1"):
            raise EvidenceMissing(f"APT target {name} has unresolved DefaultEnabled value")
        output.append((name,fields))
    return output


def _expand_target_template(template: str, name: str, stanza: dict[str,str],
                            context: tuple[list[str],str,list[str]]) -> list[dict[str,str]]:
    languages,native_arch,configured_arches=context
    target_languages=languages if "$(LANGUAGE)" in template else [""]
    if "$(LANGUAGE)" in template and not target_languages:
        raise EvidenceMissing("APT translation target is enabled but its language list is unresolved")
    components=stanza.get("components","").split() or [""]
    architectures=stanza.get("architectures","").split() or configured_arches
    architectures=sorted((set(architectures)|set(stanza.get("architectures-add","").split()))-
                         set(stanza.get("architectures-remove","").split()))
    rows=[]
    for component in components:
        for arch in architectures if "$(ARCHITECTURE)" in template else [native_arch]:
            for language in target_languages:
                value=template.replace("$(COMPONENT)",component).replace("$(ARCHITECTURE)",arch)
                value=value.replace("$(NATIVE_ARCHITECTURE)",native_arch).replace("$(LANGUAGE)",language)
                if re.search(r"\$\([^)]+\)",value):
                    raise EvidenceMissing(f"unsupported APT MetaKey substitution in {name}")
                if value.startswith("/") or ".." in Path(value).parts:
                    raise ValueError("APT MetaKey escaped repository-relative path")
                rows.append({"meta_key":value,"architecture":arch,"component":component})
    return rows


def _verified_releases(doc: dict[str, Any], root: Path) -> dict[str,bytes]:
    rows=doc.get("repositories")
    if not isinstance(rows,list) or not rows:
        raise EvidenceMissing("source-to-Release signature binding records absent")
    releases={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get("source"),str) or row["source"] in releases:
            raise ValueError("repository source identities are malformed or duplicated")
        releases[row["source"]]=_artifact(root,row.get("inrelease"),"verified source InRelease")[0]
    return releases


def _verified_index_rows(doc: dict[str, Any], root: Path, releases: dict[str,bytes]) -> dict[str,set[str]]:
    rows=doc.get("indexes")
    if not isinstance(rows,list) or not rows:
        raise EvidenceMissing("raw index bytes and signed Release manifests required")
    observed:dict[str,set[str]]={source:set() for source in releases}
    identities:set[tuple[str,str]]=set()
    for row in rows:
        if not isinstance(row,dict):
            raise EvidenceMissing("index record must be an object")
        source=row.get("source")
        meta_key=row.get("meta_key")
        release,_=_artifact(root,row.get("release"),"index Release manifest")
        if not isinstance(source,str) or releases.get(source)!=release or not isinstance(meta_key,str) or not meta_key:
            raise ValueError("index record is not bound to source and verified Release bytes")
        if (source,meta_key) in identities:
            raise ValueError("duplicate source/index record")
        identities.add((source,meta_key))
        content,_=_artifact(root,row.get("content"),"index content")
        result=apt_sources.check_release_index(release.decode("utf-8"),meta_key,content)
        if result.get("status")=="block":
            raise ValueError("captured index content digest/size differs from signed Release")
        if result.get("status")!="pass":
            raise EvidenceMissing("index digest verification could not run")
        observed[source].add(meta_key)
    return observed


def _source_gate(doc: dict[str, Any], root: Path, decision: dict[str, Any] | None) -> dict[str, Any]:
    try:
        actual = _read_configured_sources(doc,root)
        if decision is None:
            return _gate("configured_source_coverage", "could_not_run", "trusted profile decision unavailable")
        matches, errors = _profile_matches(actual, decision["profile"])
        if not matches:
            return _gate("configured_source_coverage", "fail", "; ".join(errors))
        target_raw=_captured_command_output(doc,root,"effective_targets",["apt-get","indextargets"],
                                            "effective apt indextargets")
        observed=_parse_effective_targets(target_raw.decode("utf-8"))
        config_raw=_captured_command_output(doc,root,"apt_config_dump",["apt-config","dump"],"apt-config dump")
        expected=_derive_target_rows(doc,root,config_raw.decode("utf-8"))
        fields=("uri","suite","architecture","identifier","meta_key","component","target_of")
        expected_keys={tuple(row[key] for key in fields) for row in expected}
        observed_keys={tuple(row[key] for key in fields) for row in observed}
        if len(expected_keys)!=len(expected):
            raise ValueError("active sources derive duplicate effective target identities")
        if not observed:
            raise EvidenceMissing("effective index-target output is empty")
        missing=expected_keys-observed_keys
        unexpected=observed_keys-expected_keys
        if missing or unexpected:
            return _gate("configured_source_coverage","fail","effective APT targets disagree with the active source stanzas and native target definitions",
                         missing=sorted(missing),unexpected=sorted(unexpected))
        return _gate("configured_source_coverage","pass","all enabled binary/source, translation, DEP-11, CNF and other derived targets match native indextargets")
    except EvidenceMissing as exc:
        return _gate("configured_source_coverage", "could_not_run", str(exc))
    except (ValueError, UnicodeError) as exc:
        return _gate("configured_source_coverage", "fail", str(exc))


def _signature_gate(doc: dict[str, Any], root: Path, decision: dict[str, Any] | None) -> dict[str, Any]:
    try:
        rows = doc.get("repositories")
        if not isinstance(rows, list) or not rows:
            raise EvidenceMissing("per-source Release bytes and keyrings required")
        results=[]
        _check_repository_coverage(doc,rows)
        for repo in rows:
            release, path = _artifact(root, repo.get("inrelease"), "InRelease")
            key_records = repo.get("keyrings")
            if not isinstance(key_records, list) or not key_records:
                raise EvidenceMissing("source signing keyring absent")
            key_paths=[_artifact(root, item, "source keyring")[1] for item in key_records]
            check=apt_sources.verify_release_signature(path, key_paths)
            expected=repo.get("allowed_fingerprints")
            if (not isinstance(expected,list) or not expected or
                    any(not isinstance(value,str) or re.fullmatch(r"[0-9A-Fa-f]{40,64}",value) is None
                        for value in expected)):
                raise EvidenceMissing("allowed signer fingerprint list missing or malformed")
            profile=decision.get("profile", []) if decision else []
            approved=[item for item in profile if isinstance(item,dict) and item.get("source_id")==repo.get("source")]
            if len(approved)!=1 or approved[0].get("allowed_fingerprints")!=expected:
                raise ValueError("signer allowlist differs from signed profile decision")
            found={line.split()[2] for line in check.get("validsig_records",[]) if isinstance(line,str) and len(line.split())>2}
            status=check.get("status")
            if status=="block" or status=="pass" and not found.intersection(expected):
                outcome="fail"
            elif status!="pass":
                outcome="could_not_run"
            else:
                outcome="pass"
            results.append({"source":repo.get("source"),"status":outcome,"signers":sorted(found),
                            "inrelease_sha256":hashlib.sha256(release).hexdigest()})
        overall="fail" if any(r["status"]=="fail" for r in results) else "could_not_run" if any(r["status"]!="pass" for r in results) else "pass"
        return _gate("signature_key_and_source_binding", overall, "gpgv verified captured InRelease bytes against bound keyrings", sources=results)
    except EvidenceMissing as exc:
        return _gate("signature_key_and_source_binding", "could_not_run", str(exc))
    except ValueError as exc:
        return _gate("signature_key_and_source_binding", "fail", str(exc))


def _check_repository_coverage(doc: dict[str,Any], rows: list[Any]) -> None:
    repo_ids=[row.get("source") for row in rows if isinstance(row,dict)]
    source_records=doc.get("sources")
    source_ids=[row.get("source_id") for row in source_records if isinstance(row,dict)] if isinstance(source_records,list) else []
    if len(set(repo_ids))!=len(repo_ids) or set(repo_ids)!=set(source_ids):
        raise EvidenceMissing("signature records must cover every configured source exactly once")


def _parse_effective_targets(text: str) -> list[dict[str,str]]:
    required=("Repo-URI","Suite","Architecture","Identifier","MetaKey","Component","Target-Of")
    rows=[]
    identities=set()
    for record_number,paragraph in enumerate(text.strip().split("\n\n"),1):
        if not paragraph.strip():
            continue
        captured={}
        for line in paragraph.splitlines():
            key,separator,value=line.partition(":")
            if not separator or key in captured:
                raise EvidenceMissing(f"indextargets paragraph {record_number} has malformed or duplicate fields")
            captured[key]=value.strip()
        nonempty_fields=set(required)-{"Component"}
        if any(not isinstance(captured.get(field),str) or not captured[field] for field in nonempty_fields):
            raise EvidenceMissing(f"indextargets paragraph {record_number} lacks required native fields")
        uri=apt_sources._safe_uri(captured["Repo-URI"])
        if uri is None:
            raise EvidenceMissing(f"indextargets paragraph {record_number} has an invalid repository URI")
        row={"uri":uri,"suite":captured["Suite"],"architecture":captured["Architecture"],
             "identifier":captured["Identifier"],"meta_key":captured["MetaKey"],
             "component":captured["Component"],"target_of":captured["Target-Of"]}
        if "$" in " ".join(row.values()):
            raise EvidenceMissing(f"indextargets paragraph {record_number} has unresolved identity fields")
        key=tuple(row[field] for field in ("uri","suite","architecture","identifier","meta_key","component","target_of"))
        if key in identities:
            raise ValueError("duplicate effective indextarget row")
        identities.add(key)
        rows.append(row)
    return rows


def _derive_target_rows(doc: dict[str,Any], root: Path, config_text: str) -> list[dict[str,str]]:
    target_config=_apt_target_definitions(config_text)
    target_config=target_config._replace(languages=_resolved_languages(
        doc,root,target_config.languages,target_config.environment_mode))
    source_records=doc.get("sources")
    if not isinstance(source_records,list) or not source_records:
        raise EvidenceMissing("configured source records required for target derivation")
    rows=[row for record in source_records for row in _derive_source_target_rows(record,root,target_config)]
    if not rows:
        raise EvidenceMissing("APT configuration produced no enabled targets")
    return rows


def _derive_source_target_rows(record: Any, root: Path, target_config: TargetConfig) -> list[dict[str,str]]:
    if not isinstance(record,dict) or not isinstance(record.get("source_id"),str):
        raise EvidenceMissing("source identity unavailable for effective target derivation")
    raw,_=_artifact(root,record,"configured source")
    stanzas,errors=apt_sources.parse_deb822(raw.decode("utf-8"))
    if errors:
        raise ValueError("source parsing failed while deriving effective targets")
    uri=record.get("selected_uri")
    suite=record.get("selected_suite")
    if not isinstance(uri,str) or not isinstance(suite,str):
        raise EvidenceMissing("source record must bind exact selected URI and suite")
    matches=[item for item in stanzas if item.get("enabled","yes").lower()!="no"
             and uri in item.get("uris","").split() and suite in item.get("suites","").split()]
    if len(matches)!=1:
        raise EvidenceMissing("source record must bind exactly one enabled stanza for its URI and suite")
    stanza=matches[0]
    targets=_target_bindings(stanza,target_config.definitions,target_config.languages,
                             target_config.native_arch,target_config.configured_arches)
    return [{"source_id":record["source_id"],"uri":apt_sources._safe_uri(uri) or uri,
             "suite":suite,"architecture":binding["architecture"],"identifier":target,
             "meta_key":binding["meta_key"],"component":binding["component"],
             "target_of":binding["target_of"]}
            for target,bindings in targets.items() for binding in bindings]


def _coverage_results(doc: dict[str, Any], root: Path, verified: dict[str,bytes],
                      observed: dict[str,set[str]]) -> list[dict[str, Any]]:
    coverage=doc.get("coverage")
    if not isinstance(coverage,list) or not coverage:
        raise EvidenceMissing("per-source expected-vs-observed index coverage records absent")
    if len(coverage)!=len(verified):
        raise EvidenceMissing("coverage record count must match every configured repository")
    config_raw=_captured_command_output(doc,root,"apt_config_dump",["apt-config","dump"],"apt-config dump")
    derived=_expected_index_paths(doc,root,config_raw.decode("utf-8"))
    coverage_ids:set[str]=set()
    results=[]
    context={"verified":verified,"observed":observed,"derived":derived}
    for row in coverage:
        if not isinstance(row,dict):
            raise EvidenceMissing("coverage row must be an object")
        source=row.get("source")
        if not isinstance(source,str) or source not in verified or source in coverage_ids:
            raise ValueError("coverage source identity is absent, unexpected, or duplicated")
        coverage_ids.add(source)
        results.append(_coverage_row(root,row,source,context))
    # Count equality plus membership checks above and duplicate rejection makes
    # set equality an invariant; a second guard here would be unreachable.
    return results


def _coverage_row(root: Path, row: dict[str, Any], source: str, context: dict[str,Any]) -> dict[str,Any]:
    verified=context["verified"]
    observed=context["observed"]
    derived=context["derived"]
    declared=row.get("expected_meta_keys")
    if (not isinstance(declared,list) or any(not isinstance(item,str) for item in declared)
            or len(set(declared))!=len(declared) or set(declared)!=derived.get(source)):
        raise ValueError("declared expected index paths differ from paths derived from active source bytes")
    actual_observed=sorted(observed[source])
    if row.get("observed_meta_keys")!=actual_observed:
        raise ValueError("coverage observed keys differ from raw indexes whose digests were verified")
    release,_=_artifact(root,row.get("release"),"coverage Release")
    if verified.get(source)!=release:
        raise ValueError("coverage manifest is not byte-bound to verified source Release")
    return apt_sources.check_index_coverage(release.decode("utf-8"),declared,actual_observed)


def _index_gate(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    try:
        verified=_verified_releases(doc,root)
        observed=_verified_index_rows(doc,root,verified)
        complete=_coverage_results(doc,root,verified,observed)
        status="fail" if any(x.get("fail") for x in complete) else "could_not_run" if any(x.get("status")!="pass" for x in complete) else "pass"
        return _gate("effective_index_integrity_and_coverage",status,"index bytes and per-source missing-index manifest semantics recomputed",indexes={k:sorted(v) for k,v in observed.items()},coverage=complete)
    except EvidenceMissing as exc:
        return _gate("effective_index_integrity_and_coverage","could_not_run",str(exc))
    except (ValueError,UnicodeError,TypeError) as exc:
        return _gate("effective_index_integrity_and_coverage","fail",str(exc))


def _freshness_gate(doc: dict[str, Any], root: Path, decision: dict[str, Any] | None) -> dict[str, Any]:
    try:
        rows=doc.get("freshness")
        if decision is None or not isinstance(rows,list) or not rows:
            raise EvidenceMissing("signed freshness policy decision and per-source captures required")
        from datetime import datetime
        repo_rows=doc.get("repositories",[])
        releases={r.get("source"):_artifact(root,r.get("inrelease"),"repository InRelease")[0]
                  for r in repo_rows if isinstance(r,dict)}
        row_sources=[r.get("source") for r in rows if isinstance(r,dict)]
        if len(row_sources)!=len(releases) or set(row_sources)!=set(releases):
            raise EvidenceMissing("freshness records must cover every configured repository exactly")
        results=[]
        for row in rows:
            if not isinstance(row,dict) or row.get("source") not in decision["freshness"]:
                raise ValueError("freshness observation not bound to decision")
            payload,_=_artifact(root,row.get("release"),"freshness Release")
            if releases.get(row["source"])!=payload:
                raise ValueError("freshness Release bytes differ from the signature-verified source artifact")
            clock_raw,_=_artifact(root,row.get("clock"),"native UTC clock command")
            clock=_json_bytes(clock_raw,"native UTC clock command")
            if (clock.get("argv") not in (["date","--utc","--iso-8601=seconds"],["date","-u","--iso-8601=seconds"])
                    or type(clock.get("exit_code")) is not int or clock.get("exit_code")!=0
                    or not isinstance(clock.get("stdout"),str)
                    or type(clock.get("stdout_truncated")) is not bool or clock["stdout_truncated"]
                    or type(clock.get("stderr_truncated")) is not bool or clock["stderr_truncated"]):
                raise EvidenceMissing("native date command receipt is absent or malformed")
            observed=datetime.fromisoformat(clock["stdout"].strip())
            policy=decision["freshness"][row["source"]]
            maximum=policy.get("max_age_seconds") if isinstance(policy,dict) else None
            results.append(apt_sources.check_release_freshness(payload.decode(),observed,maximum))
        status="fail" if any(r.get("status")=="block" for r in results) else "could_not_run" if any(r.get("status")!="pass" for r in results) else "pass"
        return _gate("signed_release_freshness",status,"signed dates checked against externally decided per-source policy and captured native UTC clock receipts",results=results)
    except EvidenceMissing as exc:
        return _gate("signed_release_freshness","could_not_run",str(exc))
    except (ValueError,UnicodeError,TypeError) as exc:
        return _gate("signed_release_freshness","fail",str(exc))


def _negative_gate(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    try:
        rows=doc.get("integrity_negative_canaries")
        expected={"bad_package_hash","bad_release_signature"}
        if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):
            raise EvidenceMissing("both integrity negative canaries must be complete object records")
        if {r.get("outcome") for r in rows}!=expected:
            raise EvidenceMissing("both package-hash and release-signature negative controls required")
        roots=[r.get("isolated_root") for r in rows if isinstance(r,dict)]
        if len(set(roots))!=len(roots):
            raise ValueError("integrity negative controls must use independent isolated roots")
        for row in rows:
            _verify_negative_input(doc,root,row)
        results=[_canary_result(doc,root,r["outcome"],r) for r in rows]
        status="fail" if any(r["status"]=="fail" for r in results) else "could_not_run" if any(r["status"]!="pass" for r in results) else "pass"
        return _gate("integrity_negatives",status,"isolated negative controls recomputed from raw command and source receipts",results=results)
    except EvidenceMissing as exc:
        return _gate("integrity_negatives","could_not_run",str(exc))
    except (ValueError,TypeError,UnicodeError) as exc:
        return _gate("integrity_negatives","fail",str(exc))


def _verify_negative_input(doc: dict[str,Any], root: Path, row: dict[str,Any]) -> None:
    outcome=row.get("outcome")
    if outcome=="bad_package_hash":
        _verify_package_negative(doc,root,row)
        return
    if outcome=="bad_release_signature":
        _verify_signature_negative(doc,root,row)
        return
    raise ValueError("unsupported integrity negative outcome")


def _verify_package_negative(doc: dict[str,Any], root: Path, row: dict[str,Any]) -> None:
    source=row.get("source_id")
    meta_key=row.get("meta_key")
    if not isinstance(source,str) or not isinstance(meta_key,str):
        raise EvidenceMissing("bad-hash canary source identity and MetaKey required")
    baseline=[item for item in doc.get("indexes",[]) if isinstance(item,dict)
              and item.get("source")==source and item.get("meta_key")==meta_key]
    if len(baseline)!=1:
        raise EvidenceMissing("bad-hash canary requires one baseline signed index by source and MetaKey")
    expected_raw,_=_artifact(root,baseline[0].get("content"),"baseline signed index")
    release_raw,_=_artifact(root,baseline[0].get("release"),"baseline index Release")
    if apt_sources.check_release_index(release_raw.decode("utf-8"),meta_key,expected_raw).get("status")!="pass":
        raise EvidenceMissing("baseline package index is not verified against signed Release bytes")
    damaged_raw,_=_artifact(root,row.get("negative_input"),"corrupted package negative input")
    if damaged_raw==expected_raw:
        raise ValueError("bad-hash negative input is byte-identical to the valid baseline")
    if apt_sources.check_release_index(release_raw.decode("utf-8"),meta_key,damaged_raw).get("status")!="block":
        raise ValueError("bad-hash negative input does not conflict with the signed digest and size")
    row["_baseline_input_sha256"]=hashlib.sha256(expected_raw).hexdigest()
    row["_damaged_input_sha256"]=hashlib.sha256(damaged_raw).hexdigest()


def _verify_signature_negative(doc: dict[str,Any], root: Path, row: dict[str,Any]) -> None:
    source=row.get("source_id")
    repositories=[item for item in doc.get("repositories",[]) if isinstance(item,dict) and item.get("source")==source]
    if len(repositories)!=1:
        raise EvidenceMissing("bad-signature canary requires one source-bound signed Release baseline")
    repo=repositories[0]
    baseline,_=_artifact(root,repo.get("inrelease"),"baseline signed InRelease")
    damaged,damaged_path=_artifact(root,row.get("negative_input"),"corrupted InRelease negative input")
    if damaged==baseline:
        raise ValueError("bad-signature negative input is byte-identical to the signed baseline")
    keys=[_artifact(root,item,"repository keyring")[1] for item in repo.get("keyrings",[])]
    if not keys:
        raise EvidenceMissing("bad-signature negative requires the baseline source keyring")
    check=apt_sources.verify_release_signature(damaged_path,keys)
    if check.get("status")=="pass":
        raise ValueError("bad-signature negative InRelease still verifies under the source keyring")
    if check.get("status")!="block":
        raise EvidenceMissing("gpgv could not conclusively classify the corrupted InRelease")
    row["_baseline_input_sha256"]=hashlib.sha256(baseline).hexdigest()
    row["_damaged_input_sha256"]=hashlib.sha256(damaged).hexdigest()


def _safety_gate(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    try:
        safety=doc.get("safety")
        if not isinstance(safety,dict):
            raise EvidenceMissing("canary source/config raw bytes and safety receipts absent")
        source,_=_artifact(root,safety.get("source"),"safety source")
        config,_=_artifact(root,safety.get("config"),"safety config")
        active=[_artifact(root,r,"active source")[0] for r in doc.get("sources",[])]
        if source not in active:
            raise ValueError("canary source bytes do not match active source bytes")
        errors=apt_sources._isolated_config_errors(config.decode(),Path(safety.get("isolated_root","/invalid")))
        if errors:
            raise ValueError("unsafe isolated config: "+"; ".join(errors))
        canaries=[doc.get("healthy_canary"),doc.get("wrong_source_canary"),*doc.get("integrity_negative_canaries",[])]
        for canary in canaries:
            if not isinstance(canary,dict) or not isinstance(canary.get("receipts"),dict):
                raise EvidenceMissing("raw isolated command inventory absent")
            for kind in ("config","update","targets"):
                raw,_=_artifact(root,canary["receipts"].get(kind),"isolated command")
                command=_json_bytes(raw,"isolated command")
                argv=command.get("argv")
                if not isinstance(argv,list) or any(token in argv for token in ("install","upgrade","dist-upgrade","full-upgrade")):
                    raise ValueError("isolated command inventory contains an install/upgrade action")
        return _gate("safety_and_input_binding","pass","captured source/config bytes bound to isolated APT configuration")
    except EvidenceMissing as exc:
        return _gate("safety_and_input_binding","could_not_run",str(exc))
    except (ValueError,UnicodeError,TypeError) as exc:
        return _gate("safety_and_input_binding","fail",str(exc))


def _rollback_gate(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    try:
        row=doc.get("rollback")
        if not isinstance(row,dict):
            raise EvidenceMissing("before/after source, keyring and package-state captures required")
        before,_=_artifact(root,row.get("before"),"before state")
        after,_=_artifact(root,row.get("after"),"after state")
        before_doc=_json_bytes(before,"before host state")
        after_doc=_json_bytes(after,"after host state")
        state_fields={"sources","keyrings","apt_config","package_state"}
        if set(before_doc)!=state_fields or set(after_doc)!=state_fields:
            raise EvidenceMissing("before/after state must bind source, keyring, APT config and package state")
        expected=_state_identity(doc,root)
        if before_doc!=expected or after_doc!=expected:
            raise ValueError("before/after state digest map differs from captured source, keyring, config and package state bytes")
        if before!=after:
            return _gate("rollback_and_cleanup","fail","host state bytes differ before/after")
        _verify_cleanup(doc,root,row)
        return _gate("rollback_and_cleanup","pass","before/after host state matches and isolated roots are absent")
    except EvidenceMissing as exc:
        return _gate("rollback_and_cleanup","could_not_run",str(exc))
    except ValueError as exc:
        return _gate("rollback_and_cleanup","fail",str(exc))


def _verify_cleanup(doc: dict[str,Any], root: Path, rollback: dict[str,Any]) -> None:
    roots=[doc.get("healthy_canary",{}).get("isolated_root"),doc.get("wrong_source_canary",{}).get("isolated_root")]
    roots.extend(r.get("isolated_root") for r in doc.get("integrity_negative_canaries",[]) if isinstance(r,dict))
    if any(not isinstance(path,str) or Path(path).exists() for path in roots):
        raise ValueError("isolated APT root remains")
    cleanup=rollback.get("cleanup_receipts")
    if not isinstance(cleanup,list) or len(cleanup)!=len(roots):
        raise EvidenceMissing("one raw cleanup verification receipt per isolated root required")
    expected_paths=set(roots)
    receipt_paths=[item.get("expected_absent_path") for item in cleanup if isinstance(item,dict)]
    if len(receipt_paths)!=len(cleanup) or set(receipt_paths)!=expected_paths:
        raise ValueError("cleanup receipts do not check each exact isolated root")
    for receipt in cleanup:
        raw,_=_artifact(root,receipt,"cleanup command receipt")
        command=_json_bytes(raw,"cleanup command receipt")
        path=receipt.get("expected_absent_path") if isinstance(receipt,dict) else None
        if not isinstance(path,str) or command.get("argv")!=["test","!","-e",path] or command.get("exit_code")!=0:
            raise ValueError("cleanup receipt does not show a successful absent-path check")


def _state_identity(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    source_rows=doc.get("sources")
    repositories=doc.get("repositories")
    if not isinstance(source_rows,list) or not isinstance(repositories,list):
        raise EvidenceMissing("source and keyring inventory required for before/after state binding")
    source_hashes=sorted(hashlib.sha256(_artifact(root,row,"source state")[0]).hexdigest() for row in source_rows)
    key_rows=[key for repo in repositories if isinstance(repo,dict) for key in repo.get("keyrings",[])]
    if not key_rows:
        raise EvidenceMissing("source keyring inventory required for rollback binding")
    key_hashes=sorted(hashlib.sha256(_artifact(root,row,"keyring state")[0]).hexdigest() for row in key_rows)
    config=hashlib.sha256(_artifact(root,doc.get("apt_config_dump"),"APT config state")[0]).hexdigest()
    package_state=hashlib.sha256(_artifact(root,doc.get("package_state"),"package state")[0]).hexdigest()
    return {"sources":source_hashes,"keyrings":key_hashes,"apt_config":config,"package_state":package_state}


def _run_gates(doc: dict[str, Any], root: Path, decision_sha256: str | None) -> list[dict[str, Any]]:
    decision_gate,decision=_decision_gate(doc,root,decision_sha256)
    gates=[_subject_gate(doc,root,decision)]
    gates.extend([decision_gate,_source_gate(doc,root,decision),_signature_gate(doc,root,decision),
                  _index_gate(doc,root),_freshness_gate(doc,root,decision)])
    _canary_gate(gates,doc,root,("healthy_canary","fresh_isolated_update","healthy"))
    _canary_gate(gates,doc,root,("wrong_source_canary","wrong_source_negative","wrong_arm64_source"))
    gates.extend([_negative_gate(doc,root),_safety_gate(doc,root),_rollback_gate(doc,root)])
    states=[item["status"] for item in gates]
    status="fail" if "fail" in states else "could_not_run" if any(value!="pass" for value in states) else "pass"
    gates.append(_gate("aggregate_selector",status,"all twelve gates aggregated without hiding failures or CNR",gate_count=12))
    return gates


def _canary_result(doc: dict[str, Any], root: Path, outcome: str, row: dict[str, Any]) -> dict[str, Any]:
    receipt=row.get("receipts")
    if not isinstance(receipt,dict):
        raise EvidenceMissing(f"{outcome}: apt-config/update/targets raw receipts missing")
    values=[]
    for name in ("config","update","targets"):
        raw,_=_artifact(root,receipt.get(name),f"{outcome} {name}")
        values.append(_json_bytes(raw,f"{outcome} {name}"))
    fresh_state=_canary_fresh_state(root,row,outcome)
    canary_root=Path(row.get("isolated_root","/invalid"))
    if not canary_root.is_absolute() or canary_root.parent != Path("/tmp"):
        raise ValueError(f"{outcome}: isolated root must be a direct child of /tmp")
    result=apt_sources.check_isolated_update_control(values[0], values[1], values[2], canary_root, outcome)
    _check_canary_source(doc,root,outcome,row)
    if result.get("status")=="pass":
        if canary_root.exists():
            return {"status":"fail","outcome":outcome,
                    "result":{"reason":"isolated update root remains after recorded cleanup"}}
    return {"status":"pass" if result.get("status")=="pass" else "fail" if result.get("status")=="block" else "could_not_run",
            "outcome":outcome,"result":result,"fresh_state":fresh_state}


def _canary_fresh_state(root: Path, row: dict[str, Any], outcome: str) -> dict[str, Any]:
    """Bind before/after list captures and mtime to the actual isolated update window."""
    state=row.get("fresh_state")
    if not isinstance(state,dict):
        raise EvidenceMissing(f"{outcome}: fresh isolated-list before/after capture is required")
    started,finished=_state_window(state,outcome)
    before=state.get("before")
    after=state.get("after")
    if not isinstance(before,list) or not isinstance(after,list):
        raise EvidenceMissing(f"{outcome}: list state records must be arrays")
    _check_list_rows(root,before,"before",outcome,finished)
    _check_list_rows(root,after,"after",outcome,finished)
    if before:
        raise ValueError(f"{outcome}: isolated lists were not empty before the fresh update")
    if outcome=="healthy" and not after:
        raise ValueError("healthy update did not create any fresh list files")
    return {"started_at":started.isoformat(),"finished_at":finished.isoformat(),
            "before_count":len(before),"after_count":len(after)}


def _state_window(state: dict[str, Any], outcome: str) -> tuple[Any, Any]:
    from datetime import datetime
    try:
        started=datetime.fromisoformat(state["started_at"])
        finished=datetime.fromisoformat(state["finished_at"])
        if started.tzinfo is None or finished.tzinfo is None or started>finished:
            raise ValueError("invalid update time window")
    except (KeyError,TypeError,ValueError) as exc:
        raise EvidenceMissing(f"{outcome}: update start/end timestamps incomplete") from exc
    return started,finished


def _check_list_rows(root: Path, rows: list[Any], label: str, outcome: str, finished: Any) -> None:
    from datetime import datetime
    for entry in rows:
        raw,_=_artifact(root,entry,f"{outcome} {label} list artifact")
        if entry.get("size") != len(raw):
            raise ValueError(f"{outcome}: {label} list artifact size mismatch")
        try:
            mtime=datetime.fromisoformat(entry.get("mtime",""))
        except (TypeError,ValueError) as exc:
            raise EvidenceMissing(f"{outcome}: {label} list mtime unavailable") from exc
        if mtime.tzinfo is None:
            raise EvidenceMissing(f"{outcome}: {label} list mtime lacks timezone")
        if label=="after" and mtime<finished:
            raise ValueError(f"{outcome}: list file predates isolated update completion")


def _check_canary_source(doc: dict[str, Any], root: Path, outcome: str, row: dict[str, Any]) -> None:
    source_raw,_=_artifact(root,row.get("source"),f"{outcome} source")
    if row.get("source_sha256") != hashlib.sha256(source_raw).hexdigest():
        raise ValueError(f"{outcome}: source hash binding mismatch")
    baseline=doc.get("sources")
    if not isinstance(baseline,list):
        raise EvidenceMissing("configured source bytes unavailable for canary comparison")
    baseline_bytes=[_artifact(root,r,"active source")[0] for r in baseline]
    if outcome in ("healthy","bad_package_hash","bad_release_signature") and source_raw not in baseline_bytes:
        raise ValueError("healthy/integrity canary source differs from captured active source bytes")
    if outcome=="wrong_arm64_source":
        if source_raw in baseline_bytes:
            raise ValueError("wrong-source negative reuses unchanged baseline bytes")
        if "archive.ubuntu.com/ubuntu" not in source_raw.decode():
            raise ValueError("wrong-source bytes lack the incompatible Ubuntu endpoint")


def _canary_gate(gates: list[dict[str, Any]], doc: dict[str, Any], root: Path,
                 spec: tuple[str, str, str]) -> None:
    row_name,gate_name,outcome=spec
    try:
        row=doc.get(row_name)
        if not isinstance(row,dict):
            raise EvidenceMissing(f"{row_name} raw evidence missing")
        result=_canary_result(doc,root,outcome,row)
        gates.append(_gate(gate_name,result["status"],"isolated update receipts and source inputs independently recomputed",result=result))
    except EvidenceMissing as exc:
        gates.append(_gate(gate_name,"could_not_run",str(exc)))
    except (ValueError, UnicodeError, TypeError) as exc:
        gates.append(_gate(gate_name,"fail",str(exc)))


def verify(evidence: Path, decision_sha256: str | None = None) -> dict[str, Any]:
    """Evaluate a JSON bundle whose paths are relative to its directory."""
    try:
        doc,root=_doc(evidence)
    except EvidenceMissing as exc:
        empty=[_gate(name,"could_not_run",str(exc)) for name in GATES[:-1]]
        empty.append(_gate("aggregate_selector","could_not_run","bundle unavailable",gate_count=11))
        return {"id":CARD_ID,"status":"unknown","could_not_run":12,"fail":0,"gates":empty,
                "complete":False,"provenance":"caller-supplied evidence; hashes do not authenticate host or command origin",
                "criteria_unimplemented":UNIMPLEMENTED_CRITERIA}
    if doc.get("id") != CARD_ID:
        return {"id":CARD_ID,"status":"fail","could_not_run":0,"fail":1,
                "gates":[_gate("aggregate_selector","fail","card identity/schema mismatch")],"complete":True}
    if type(doc.get("schema")) is not int or doc.get("schema") != 1:
        empty=[_gate(name,"could_not_run","capture schema version 1 is required") for name in GATES[:-1]]
        empty.append(_gate("aggregate_selector","could_not_run","capture schema unavailable",gate_count=11))
        return {"id":CARD_ID,"status":"unknown","could_not_run":12,"fail":0,"gates":empty,
                "complete":True,"provenance":"caller-supplied evidence; hashes do not authenticate host or command origin",
                "criteria_unimplemented":UNIMPLEMENTED_CRITERIA}
    gates=_run_gates(doc,root,decision_sha256)
    aggregate=gates[-1]["status"]
    return {"id":CARD_ID,"status":"pass" if aggregate=="pass" else "fail" if aggregate=="fail" else "unknown",
            "could_not_run":sum(g["status"]=="could_not_run" for g in gates),
            "fail":sum(g["status"]=="fail" for g in gates),"gates":gates,"complete":True,
            "provenance":"caller-supplied evidence; hashes do not authenticate host or command origin",
            "criteria_unimplemented":UNIMPLEMENTED_CRITERIA}


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",required=True,type=Path)
    parser.add_argument("--decision-sha256",help="exact SHA256 from the external profile/freshness approval channel")
    args=parser.parse_args(argv)
    result=verify(args.evidence,args.decision_sha256)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["status"]=="pass" and result["could_not_run"]==0 else 1 if result["status"]=="fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
