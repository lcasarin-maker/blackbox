from pathlib import Path
import runpy
import sys

from tools import runtime_provenance as rp


def test_capture_preserves_observed_kv_series_and_exact_mapping() -> None:
    result = rp.parse_capture(
        '# HELP vllm:kv_cache_usage_perc KV-cache usage. 1 means 100 percent usage.\n'
        '# TYPE vllm:kv_cache_usage_perc gauge\n'
        'vllm:kv_cache_usage_perc{engine="0",model_name="m"} 0.45 123\n'
        '# TYPE vllm:num_preemptions_total counter\n'
        'vllm:num_preemptions_total{engine="0"} 3\n',
        "caller-capture.prom",
    )
    assert result["status"] == "observed"
    kv, counter = result["samples"]
    assert kv == {
        "capture_path": "caller-capture.prom",
        "capture_path_provenance": "caller_supplied_unverified",
        "observation_source": "captured_prometheus_text",
        "observed_metric_name": "vllm:kv_cache_usage_perc",
        "sampler_field": "vllm_kv_cache_usage_perc",
        "observed_type": "gauge",
        "type_provenance": "declared",
        "type_interpretation": "observed",
        "observed_help": "KV-cache usage. 1 means 100 percent usage.",
        "semantic_unit_status": "not_declared_in_capture",
        "labels": {"engine": "0", "model_name": "m"},
        "raw_value": "0.45",
        "timestamp_ms": 123,
    }
    assert counter["observed_metric_name"] == "vllm:num_preemptions_total"
    assert counter["observed_type"] == "counter"
    assert counter["raw_value"] == "3"


def test_allowed_prometheus_values_and_optional_untyped_default() -> None:
    result = rp.parse_capture(
        'vllm:kv_cache_usage_perc +Inf -1\n'
        'vllm:num_requests_running 2\n',
        "capture.prom",
    )
    assert result["status"] == "observed"
    assert result["samples"][0]["raw_value"] == "+Inf"
    assert result["samples"][0]["timestamp_ms"] == -1
    assert result["samples"][1]["observed_type"] == "untyped"
    assert result["samples"][1]["type_provenance"] == "default_untyped"


def test_caller_alias_and_unrelated_memory_metric_are_not_mapped() -> None:
    result = rp.parse_capture(
        '# TYPE process_resident_memory_bytes gauge\n'
        'process_resident_memory_bytes 4096\n'
        'kv_cache_bytes 1234\n',
        "caller-label.prom",
    )
    assert result["status"] == "unknown"
    assert result["samples"] == []
    assert result["could_not_run_count"] == 1


def test_malformed_observations_and_duplicate_series_count_could_not_run() -> None:
    result = rp.parse_capture(
        '# TYPE vllm:num_requests_running gauge\n'
        'vllm:num_requests_running{engine="0",engine="1"} 2\n'
        'vllm:num_requests_running{engine="0",note="bad\\t"} 1\n'
        'vllm:num_requests_running{engine="0"} 1\n'
        'vllm:num_requests_running{engine="0"} 1 2\n',
        "capture.prom",
    )
    assert result["status"] == "partial"
    assert len(result["samples"]) == 1
    assert result["unreadable_observation_count"] == 3
    assert result["could_not_run_count"] == 3
    assert result["issues"] == [
        "line 2: invalid labels or timestamp for vllm:num_requests_running",
        "line 3: invalid labels or timestamp for vllm:num_requests_running",
        "line 5: duplicate metric and labels for vllm:num_requests_running",
    ]


def test_malformed_sample_without_valid_sample_is_unknown_with_cnr() -> None:
    result = rp.parse_capture("vllm:kv_cache_usage_perc{broken\n", "capture.prom")
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1
    assert result["unreadable_observation_count"] == 1


def test_duplicate_type_help_and_type_after_sample_preserve_issues() -> None:
    result = rp.parse_capture(
        'vllm:kv_cache_usage_perc 0.5\n'
        '# TYPE vllm:kv_cache_usage_perc gauge\n'
        '# TYPE vllm:kv_cache_usage_perc gauge\n'
        '# HELP vllm:kv_cache_usage_perc usage\n'
        '# HELP vllm:kv_cache_usage_perc usage\n',
        "capture.prom",
    )
    assert result["status"] == "partial"
    assert result["could_not_run_count"] == 0
    assert result["issues"] == [
        "line 2: TYPE declaration after first sample for vllm:kv_cache_usage_perc",
        "line 3: duplicate TYPE declaration for vllm:kv_cache_usage_perc",
        "line 5: duplicate HELP declaration for vllm:kv_cache_usage_perc",
    ]


def test_conflicting_types_make_samples_indeterminate_and_count_could_not_run() -> None:
    result = rp.parse_capture(
        '# TYPE vllm:kv_cache_usage_perc gauge\n'
        'vllm:kv_cache_usage_perc 0.5\n'
        '# TYPE vllm:kv_cache_usage_perc counter\n',
        "capture.prom",
    )
    assert result["status"] == "partial"
    assert result["samples"][0]["type_interpretation"] == "indeterminate"
    assert result["unreadable_observation_count"] == 1
    assert result["could_not_run_count"] == 1
    assert result["issues"] == [
        "line 3: duplicate TYPE declaration for vllm:kv_cache_usage_perc",
        "line 3: conflicting TYPE declaration for vllm:kv_cache_usage_perc",
    ]


def test_sample_after_conflicting_type_is_indeterminate() -> None:
    result = rp.parse_capture(
        '# TYPE vllm:kv_cache_usage_perc gauge\n'
        '# TYPE vllm:kv_cache_usage_perc counter\n'
        'vllm:kv_cache_usage_perc 0.5\n',
        "capture.prom",
    )
    assert result["samples"][0]["type_interpretation"] == "indeterminate"
    assert result["could_not_run_count"] == 1


def test_help_without_docstring_and_escaped_help_are_preserved() -> None:
    result = rp.parse_capture(
        '# HELP vllm:kv_cache_usage_perc\n'
        'vllm:kv_cache_usage_perc 0.5\n',
        "capture.prom",
    )
    assert result["samples"][0]["observed_help"] == ""
    escaped = rp.parse_capture(
        '# HELP vllm:kv_cache_usage_perc raw\\nhelp\\\\tail\n'
        'vllm:kv_cache_usage_perc 0.5\n',
        "capture.prom",
    )
    assert escaped["samples"][0]["observed_help"] == r"raw\nhelp\\tail"


def test_malformed_type_declarations_are_retained() -> None:
    result = rp.parse_capture(
        '# TYPE vllm:kv_cache_usage_perc wrong\n'
        '# TYPE vllm:num_preemptions_total\n'
        'vllm:kv_cache_usage_perc 0.5\n',
        "capture.prom",
    )
    assert result["status"] == "partial"
    assert result["samples"][0]["observed_type"] == "untyped"
    assert result["issues"] == [
        "line 1: malformed TYPE declaration for vllm:kv_cache_usage_perc",
        "line 2: malformed TYPE declaration for vllm:num_preemptions_total",
    ]


def test_sample_timestamp_must_be_int64() -> None:
    result = rp.parse_capture(
        'vllm:kv_cache_usage_perc 0.5 9223372036854775808\n',
        "capture.prom",
    )
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1
    malformed = rp.parse_capture("vllm:kv_cache_usage_perc 0.5 1.5\n", "capture.prom")
    assert malformed["unreadable_observation_count"] == 1


def test_label_escape_and_empty_labels() -> None:
    assert rp._labels(None) == {}
    assert rp._labels("") == {}
    assert rp._labels('name="line\\nquote\\\"slash\\\\"') == {"name": 'line\nquote"slash\\'}
    assert rp._labels('name="x",') == {"name": "x"}
    assert rp._labels('name="x" trailing') is None
    assert rp._labels('name="x", name="y"') is None
    assert rp._labels('name="x\\q"') is None
    assert rp._labels('-name="x"') is None
    assert rp._labels("bad") is None
    assert rp._labels('name "x"') is None
    assert rp._labels("name=1") is None
    assert rp._labels('name = "x"') == {"name": "x"}
    assert rp._labels('name="unterminated') is None


def test_empty_and_non_sample_lines_are_not_synthesized_as_observations() -> None:
    result = rp.parse_capture("\n# EOF\n# HELP other text\nnot-a-sample{broken\n", "capture.prom")
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1


def test_nonnumeric_sample_and_unknown_short_type_metadata_branches() -> None:
    result = rp.parse_capture(
        "# TYPE vllm\n"
        "vllm:kv_cache_usage_perc text\n",
        "capture.prom",
    )
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1
    assert result["issues"] == [
        "line 1: malformed TYPE declaration",
        "line 2: invalid numeric value for vllm:kv_cache_usage_perc",
        "capture contains no recognized vLLM metric samples",
    ]


def test_file_read_failures_report_could_not_run(tmp_path: Path) -> None:
    missing = rp.analyze_file(tmp_path / "missing.prom")
    assert missing["status"] == "unknown"
    assert missing["could_not_run_count"] == 1
    invalid = tmp_path / "invalid.prom"
    invalid.write_bytes(b"\xff")
    assert rp.analyze_file(invalid)["could_not_run_count"] == 1


def test_cli_observed_and_unknown_exit_codes(tmp_path: Path, capsys) -> None:
    capture = tmp_path / "metrics.prom"
    capture.write_text("# TYPE vllm:num_requests_waiting gauge\nvllm:num_requests_waiting 1\n", encoding="utf-8")
    assert rp.main([str(capture)]) == 0
    assert '"status": "observed"' in capsys.readouterr().out
    capture.write_text("unrelated_metric 3\n", encoding="utf-8")
    assert rp.main([str(capture)]) == 2
    assert '"status": "unknown"' in capsys.readouterr().out


def test_module_entry_point_exits_with_cli_status(tmp_path: Path, monkeypatch) -> None:
    capture = tmp_path / "empty.prom"
    capture.write_text("other 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(rp.__file__), str(capture)])
    try:
        runpy.run_path(str(rp.__file__), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("module entry point did not exit")
