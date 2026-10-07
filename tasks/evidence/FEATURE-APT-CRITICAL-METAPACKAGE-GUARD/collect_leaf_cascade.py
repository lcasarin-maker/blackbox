"""Read-only capture: which single-package removals cascade into DGX OS metapackages.

Every simulation is `apt-get -s` (no lock, nothing applied). The leaf list is generated
from the installed graph, never hand-picked: every installed direct Depends of every
installed `nvidia-system-*` metapackage. Each raw plan is classified by the shared
`tools.preflight.check_apt` with the installed metapackages as the critical list.
Controls: `upgrade` and `remove tree` (a leaf outside the graph) must classify `pass`.

Run from the repo root: python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_leaf_cascade.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.preflight import check_apt

OUT = Path(__file__).resolve().parent
ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
SIM = ["apt-get", "-s", "-o", "Debug::NoLocking=1"]


def run(argv: list[str]) -> dict:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, capture_output=True, text=True, env=ENV, timeout=120)
    return {"argv": argv, "started_at": started, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def installed(names: list[str]) -> dict[str, str]:
    row = run(["dpkg-query", "-W", "-f=${Package}\t${Version}\t${db:Status-Abbrev}\n", *names])
    found = {}
    for line in row["stdout"].splitlines():
        package, version, status = line.split("\t")
        if status.startswith("ii"):
            found[package] = version
    return found


def depends(row: dict) -> list[str]:
    match = re.search(r"^Depends: (.*)$", row["stdout"], re.MULTILINE)
    if not match:
        return []
    names = []
    for clause in match.group(1).split(","):
        alternatives = [alt.strip().split(" ")[0].split(":")[0] for alt in clause.split("|")]
        if len(alternatives) == 1:  # an alternative-satisfied clause does not force removal
            names.append(alternatives[0])
    return names


def main() -> int:
    identity = [run(["cat", "/etc/dgx-release"]),
                run(["cat", "/sys/class/dmi/id/sys_vendor", "/sys/class/dmi/id/product_name"]),
                run(["apt-cache", "show", "nvidia-system-station"])]
    every = run(["dpkg-query", "-W", "-f=${Package}\t${db:Status-Abbrev}\n", "nvidia-system-*"])
    metas = sorted(line.split("\t")[0] for line in every["stdout"].splitlines()
                   if line.split("\t")[1].startswith("ii"))
    graph = {meta: run(["dpkg-query", "-s", meta]) for meta in metas}
    leaves = sorted({dep for meta in metas for dep in depends(graph[meta])} - set(metas))
    leaves = sorted(installed(leaves))
    plans = [run([*SIM, "upgrade"]), run([*SIM, "remove", "tree"])]
    plans += [run([*SIM, "remove", leaf]) for leaf in leaves]
    verdicts = []
    for row in plans:
        outcome = check_apt({"plan": row["stdout"], "critical_packages": metas,
                             "exit_code": row["exit_code"], "stderr": row["stderr"]})
        verdicts.append({"argv": row["argv"], "status": outcome["status"],
                         "findings": outcome["findings"]})
    counts = {status: sum(v["status"] == status for v in verdicts) for status in ("pass", "block", "unknown")}
    document = {
        "scope": "Read-only apt-get -s simulations on the live host; nothing applied.",
        "critical_packages": metas, "leaves_generated_from": "installed direct Depends of installed nvidia-system-* metapackages",
        "identity": identity, "metapackage_status": graph, "plans": plans,
        "verdicts": verdicts, "counts": counts,
    }
    raw = (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()
    (OUT / "leaf-cascade-captures.json").write_bytes(raw)
    (OUT / "leaf-cascade-captures.sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n", encoding="ascii")
    controls = {" ".join(v["argv"][4:]): v["status"] for v in verdicts[:2]}
    print(json.dumps({"critical_packages": metas, "leaves": len(leaves), "counts": counts,
                      "controls": controls}, sort_keys=True))
    return 0 if all(status == "pass" for status in controls.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
