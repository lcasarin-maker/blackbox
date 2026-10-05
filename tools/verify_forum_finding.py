"""Evidence-gated verifier for individually identified hardware findings."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from tools.hardware_evidence import is_generated_control_id, verify
from tools.forum_finding import SUPPORTED as SUPPORTED_FINDINGS


def verify_forum_finding(finding_id: str, evidence: str | Path | None = None) -> dict[str, object]:
    """Evaluate supported forum findings while preserving missing proof as unknown."""
    if finding_id not in SUPPORTED_FINDINGS and not is_generated_control_id(finding_id):
        return {"status": "fail", "reason": "unsupported forum finding ID", "files": [],
                "fail": 1, "could_not_run": 0}
    if finding_id == "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01":
        return verify(finding_id, evidence,
                      decision_sha256=os.environ.get("BB_APT_APPROVED_DECISION_SHA256"))
    return verify(finding_id, evidence)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    result = verify_forum_finding(args.id, args.evidence)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1 if result["status"] == "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
