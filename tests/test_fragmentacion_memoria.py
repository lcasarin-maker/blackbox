import json
from pathlib import Path
import os
import subprocess
import sys

from tools import incident_report as ir


BALDY_BEFORE = """Node 0, zone DMA32 0 0 0 0 0 0 0 0 90 91 92
Node 0, zone Normal 30 30 30 30 30 30 30 30 2 4 7
Node 1, zone Normal 60 60 60 60 60 60 60 60 1 3 5
"""
PAGETYPE_BEFORE = """Page block order: 9
Pages per block: 512
Free pages count per migrate type at order 0 1 2 3 4 5 6 7 8 9 10
Node 0, zone Normal, type Unmovable 0 1 2 3 4 5 6 7 8 9 10
Number of blocks type Unmovable Reclaimable Movable HighAtomic CMA Isolate
Node 0, zone Normal 11 12 13 14 15 16
Number of mixed blocks Unmovable Reclaimable Movable HighAtomic CMA Isolate
Node 0, zone Normal 99 98 97 96 95 94
Page block order: 9
Pages per block: 512
Free pages count per migrate type at order 0 1 2 3 4 5 6 7 8 9 10
Node 1, zone Normal, type Unmovable 0 1 2 3 4 5 6 7 8 9 10
Number of blocks type Unmovable Reclaimable Movable HighAtomic CMA Isolate
Node 1, zone Normal 1 2 3 4 5 6
Number of mixed blocks Unmovable Reclaimable Movable HighAtomic CMA Isolate
Node 1, zone Normal 99 98 97 96 95 94
"""
PAGETYPE_AFTER = PAGETYPE_BEFORE.replace("11 12 13 14 15 16", "18 12 6 18 20 22").replace(
    "1 2 3 4 5 6", "1 2 3 4 5 6"
)


def test_buddy_nodes_and_orders_are_summed_as_blocks():
    result = ir.parse_buddyinfo(BALDY_BEFORE)
    assert result["status"] == "ok"
    assert result["nodes"]["0"] == {"order_8_plus": 13, "order_10_plus": 7}
    assert result["nodes"]["1"] == {"order_8_plus": 9, "order_10_plus": 5}
    assert result["sum"] == {"order_8_plus": 22, "order_10_plus": 12}


def test_pageblocks_reads_blocks_table_and_ignores_previous_and_mixed_tables():
    result = ir.parse_pagetypeinfo(PAGETYPE_BEFORE)
    assert result["status"] == "ok"
    assert result["sum"] == {"Unmovable": 12, "Reclaimable": 14, "Movable": 16,
                              "HighAtomic": 18, "CMA": 20, "Isolate": 22}


def test_pageblocks_multinode_repeated_headers_without_mixed_are_complete():
    text = """Page block order: 9
Free pages count per migrate type at order 0 1
Node 0, zone Normal, type Unmovable 1 2
Number of blocks type Unmovable Reclaimable Movable
Node 0, zone Normal 3 4 5
Page block order: 9
Free pages count per migrate type at order 0 1
Node 1, zone Normal, type Unmovable 9 8
Number of blocks type Unmovable Reclaimable Movable
Node 1, zone Normal 5 6 7
"""
    got = ir.parse_pagetypeinfo(text)
    assert got["status"] == "ok"
    assert got["nodes"] == {"0": {"Normal": {"Unmovable": 3, "Reclaimable": 4, "Movable": 5}},
                            "1": {"Normal": {"Unmovable": 5, "Reclaimable": 6, "Movable": 7}}}
    assert got["sum"] == {"Unmovable": 8, "Reclaimable": 10, "Movable": 12}


def test_pageblocks_duplicate_rows_and_inconsistent_headers_fail_closed():
    header = "Number of blocks type Unmovable Reclaimable Movable\n"
    duplicate = header + "Node 0, zone Normal 1 2 3\nNode 0, zone Normal 3 4 5\n"
    inconsistent = header + "Node 0, zone Normal 1 2 3\nPage block order: 9\nNumber of blocks type Unmovable Reclaimable Movable HighAtomic\nNode 1, zone Normal 3 4 5 6\n"
    assert ir.parse_pagetypeinfo(duplicate)["status"] == "COLLECTION_FAILED"
    assert ir.parse_pagetypeinfo(inconsistent)["status"] == "COLLECTION_FAILED"
    missing = "Number of blocks type Unmovable Reclaimable Reserve Isolate\nNode 0, zone Normal 1 2 3 4\n"
    assert ir.parse_pagetypeinfo(missing)["status"] == "COLLECTION_FAILED"


def test_valid_non_normal_only_section_counts_for_completeness_without_affecting_normal():
    text = """Number of blocks type Unmovable Reclaimable Movable
Node 0, zone Normal 10 20 30
Number of blocks type Unmovable Reclaimable Movable
Node 0, zone DMA32 99 98 97
"""
    result = ir.parse_pagetypeinfo(text)
    assert result["status"] == "ok"
    assert result["nodes"] == {"0": {"Normal": {"Unmovable": 10, "Reclaimable": 20, "Movable": 30}}}


def test_missing_and_zero_are_distinct_and_malformed_is_failed(tmp_path):
    assert ir.collect_fragmentation(tmp_path)["buddyinfo"]["status"] == "NOT_COLLECTED"
    assert ir.collect_fragmentation(tmp_path)["pagetypeinfo"]["status"] == "NOT_COLLECTED"
    (tmp_path / "buddyinfo").write_text("Node 0, zone Normal " + " ".join(["0"] * 11))
    assert ir.collect_fragmentation(tmp_path)["buddyinfo"]["sum"]["order_8_plus"] == 0
    assert ir.collect_fragmentation(tmp_path)["pagetypeinfo"]["status"] == "NOT_COLLECTED"
    assert ir.parse_buddyinfo("Node 0 zone Normal 0 1")["status"] == "COLLECTION_FAILED"
    assert ir.parse_buddyinfo("Node 0, zone Normal 0 1 2 3 4 5 6 7 8")["status"] == "COLLECTION_FAILED"


def test_unreadable_symlink_is_not_followed(tmp_path):
    target = tmp_path / "target"
    target.write_text("Node 0, zone Normal " + " ".join(["0"] * 11))
    (tmp_path / "buddyinfo").symlink_to(target)
    assert ir.collect_fragmentation(tmp_path)["buddyinfo"]["status"] == "COLLECTION_FAILED"


def test_extreme_counter_fails_only_its_source(tmp_path):
    (tmp_path / "buddyinfo").write_text(
        "Node 0, zone Normal " + "0 " * 10 + "9" * 4500 + "\n"
    )
    (tmp_path / "pagetypeinfo").write_text(
        "Number of blocks type Unmovable Reclaimable Movable\nNode 0, zone Normal 1 2 3\n"
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(Path.cwd()))
    result = json.loads(subprocess.check_output(
        [sys.executable, "-m", "tools.incident_report", "--fragmentacion", "--proc-root", str(tmp_path)],
        env=env, text=True,
    ))
    assert result["buddyinfo"]["status"] == "COLLECTION_FAILED"
    assert result["pagetypeinfo"]["status"] == "ok"


def test_cli_rejects_empty_final_pageblock_section_and_keeps_buddy(tmp_path):
    (tmp_path / "buddyinfo").write_text(
        "Node 0, zone Normal " + " ".join(["0"] * 11) + "\n"
    )
    base = (
        "Number of blocks type Unmovable Reclaimable Movable\n"
        "Node 0, zone Normal 1 2 3\n"
        "Number of blocks type Unmovable Reclaimable Movable\n"
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(Path.cwd()))
    cmd = [sys.executable, "-m", "tools.incident_report", "--fragmentacion", "--proc-root", str(tmp_path)]
    for suffix in ("", "Page block order: 9\n"):
        (tmp_path / "pagetypeinfo").write_text(base + suffix)
        result = json.loads(subprocess.check_output(cmd, env=env, text=True))
        assert result["buddyinfo"]["status"] == "ok"
        assert result["pagetypeinfo"]["status"] == "COLLECTION_FAILED"


def test_synthetic_before_after_changes_counts():
    before = ir.parse_buddyinfo(BALDY_BEFORE)
    after = ir.parse_buddyinfo(BALDY_BEFORE.replace("2 4 7", "0 1 0").replace("1 3 5", "0 0 0"))
    assert before["sum"] != after["sum"]
    assert ir.parse_pagetypeinfo(PAGETYPE_BEFORE)["sum"] != ir.parse_pagetypeinfo(PAGETYPE_AFTER)["sum"]


def test_incident_selects_exact_boot_and_time_only():
    expected = {"schema": "bb-fragmentacion/1", "buddyinfo": {"status": "ok"}}
    rows = [
        {"boot_id": "11111111-1111-1111-1111-111111111111", "ts": "2026-01-01T00:00:01+00:00", "fragmentacion_memoria": {"bad": 1}},
        {"boot_id": "abcdef12-3456-7890-abcd-ef1234567890", "ts": "2026-01-01T00:00:02+00:00", "fragmentacion_memoria": expected},
        {"boot_id": "abcdef12-3456-7890-abcd-ef1234567890", "ts": "2026-01-01T00:02:00+00:00", "fragmentacion_memoria": {"future": 1}},
        {"boot_id": "abcdef12-3456-7890-abcd-ef1234567890", "ts": ["bad"], "fragmentacion_memoria": {"bad_ts": 1}},
    ]
    got = ir.muestra_fragmentacion_del_boot(rows, "abcdef12-3456-7890-abcd-ef1234567890", 1767225600, 1767225660)
    assert got == expected


def test_incident_additive_fields_preserve_sentinels_when_no_sample_matches():
    fields = ir.campos_aditivos_1358([], "abcdef12-3456-7890-abcd-ef1234567890", 0, 1)
    assert fields["fragmentacion_memoria_en_ultima_muestra"]["buddyinfo"]["status"] == "NOT_COLLECTED"
    assert fields["fragmentacion_memoria_en_ultima_muestra"]["pagetypeinfo"]["status"] == "NOT_COLLECTED"
    assert fields["uefi_after_power_loss"] == "NOT_COLLECTED"
    assert fields["kernel_panic_on_rcu_stall"] == "NOT_COLLECTED"


def test_real_cli_json_changes_for_synthetic_proc_input(tmp_path):
    (tmp_path / "buddyinfo").write_text("Node 0, zone Normal 0 0 0 0 0 0 0 0 1 2 3\n")
    (tmp_path / "pagetypeinfo").write_text(
        "Number of blocks type Unmovable Reclaimable Movable\nNode 0, zone Normal 4 5 6\n"
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(Path.cwd()))
    cmd = [sys.executable, "-m", "tools.incident_report", "--fragmentacion", "--proc-root", str(tmp_path)]
    before = json.loads(subprocess.check_output(cmd, env=env, text=True))
    (tmp_path / "buddyinfo").write_text("Node 0, zone Normal 0 0 0 0 0 0 0 0 0 0 0\n")
    after = json.loads(subprocess.check_output(cmd, env=env, text=True))
    assert before["buddyinfo"]["sum"]["order_8_plus"] == 6
    assert after["buddyinfo"]["sum"]["order_8_plus"] == 0
    assert before["pagetypeinfo"]["sum"] == after["pagetypeinfo"]["sum"]


def test_production_module_cli_collects_from_repo_cwd(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "buddyinfo").write_text("Node 0, zone Normal " + " ".join(["0"] * 8 + ["2", "3", "4"]))
    (proc / "pagetypeinfo").write_text(
        "Number of blocks type Unmovable Reclaimable Movable\nNode 0, zone Normal 1 2 3\n"
    )
    cmd = [sys.executable, "-m", "tools.incident_report", "--fragmentacion", "--proc-root", str(proc)]
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
    got = json.loads(subprocess.check_output(cmd, cwd=Path.cwd(), env=env, text=True))
    assert got["buddyinfo"]["sum"] == {"order_8_plus": 9, "order_10_plus": 4}
    assert got["pagetypeinfo"]["status"] == "ok"
