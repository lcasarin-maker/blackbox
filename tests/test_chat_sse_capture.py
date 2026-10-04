from pathlib import Path
import json
import runpy
import subprocess
import sys

from tools import chat_sse_capture as sse

ROOT = Path(__file__).resolve().parents[1]


def test_text_tool_call_fragments_and_finish_reasons_are_preserved() -> None:
    result = sse.parse_capture(
        'data: {"id":"chat-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"hello"},"finish_reason":null}]}\n\n'
        'data: {"id":"chat-1","choices":[{"index":0,"delta":{"tool_calls":[]},"finish_reason":null}]}\n\n'
        'data: {"id":"chat-1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call-1","function":{"name":"search","arguments":"{\\"q\\":"}}]},"finish_reason":null}]}\n\n'
        'data: {"id":"chat-1","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}\n\n'
        'data: [DONE]\n\n',
        "supplied.sse",
    )
    assert result["status"] == "observed"
    assert result["capture_path_provenance"] == "caller_supplied_unverified"
    choices = [chunk["choices"][0] for chunk in result["chunks"]]
    assert choices[0]["content_delta"] == "hello"
    assert choices[0]["tool_calls_present"] is False
    assert choices[1]["tool_calls_present"] is True
    assert choices[1]["tool_calls_delta"] == []
    assert choices[2]["tool_calls_delta"][0]["function"]["arguments"] == '{"q":'
    assert choices[3]["finish_reason"] == "tool_calls"


def test_json_syntax_reconstructed_per_choice_from_content_fragments():
    capture = (
        'data: {"choices":[{"index":0,"delta":{"content":"{\\\"ok\\\":"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"true}"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
        'data: [DONE]\n\n')
    result = sse.parse_capture(capture, "capture.sse")
    assessment = result["json_text_assessments"][0]
    assert assessment["completion_status"] == "complete"
    assert assessment["json_syntax_status"] == "valid_json"
    assert assessment["finish_reason"] == "stop"
    assert assessment["character_count"] == len('{"ok":true}')
    assert "schema" in assessment["scope"]


def test_invalid_json_is_separated_from_valid_json_schema_or_semantics():
    capture = (
        'data: {"choices":[{"index":0,"delta":{"content":"{\\\"ok\\\":}"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
        'data: [DONE]\n\n')
    assessment = sse.parse_capture(capture, "capture.sse")["json_text_assessments"][0]
    assert assessment["completion_status"] == "complete"
    assert assessment["json_syntax_status"] == "invalid_json"
    assert assessment["json_error"] == "JSONDecodeError"
    assert "semantic" in assessment["scope"]


def test_length_refusal_content_filter_tool_calls_and_missing_done_stay_distinct():
    def single(delta, finish, done="data: [DONE]\n\n"):
        chunk = json.dumps({"choices": [{"index": 0, "delta": delta,
                                          "finish_reason": finish}]})
        return f"data: {chunk}\n\n{done}"

    def result(capture):
        return sse.parse_capture(capture, "capture.sse")["json_text_assessments"][0]

    assert result(single({"content": "{}"}, "length"))["completion_status"] == "incomplete"
    refused = result(single({"refusal": "sensitive response"}, "stop"))
    assert refused["completion_status"] == "refusal"
    assert refused["json_syntax_status"] == "not_assessed"
    filtered = result(single({"content": "{}"}, "content_filter"))
    assert filtered["completion_status"] == "content_filtered"
    tool_call = result(single({"tool_calls": [{"index": 0}]}, "tool_calls"))
    assert tool_call["completion_status"] == "tool_calls"
    missing_done = result(single({"content": "{}"}, "stop", done=""))
    assert missing_done["completion_status"] == "incomplete"
    assert missing_done["json_syntax_status"] == "not_assessed"


def test_json_summary_cli_never_prints_response_text(tmp_path):
    capture = tmp_path / "capture.sse"
    capture.write_text(
        'data: {"choices":[{"index":0,"delta":{"content":"{\\\"value\\\":\\\"secret-content\\\"}"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
        'data: [DONE]\n\n', encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "chat_sse_capture.py"),
                             "--json-summary-only", str(capture)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "secret-content" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["json_text_assessments"][0]["completion_status"] == "complete"
    assert len(payload["json_text_assessments"][0]["sha256"]) == 64
    assert "status" in payload and "issues" in payload
    assert "could_not_run_count" in payload


def test_json_assessment_stops_at_finish_per_choice_and_rejects_negative_index():
    frames = [
        {"choices": [{"index": 0, "delta": {"content": "{}"}, "finish_reason": None},
                      {"index": 1, "delta": {"content": "{bad"}, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"},
                      {"index": 1, "delta": {}, "finish_reason": "stop"}]},
        {"choices": [{"index": 0, "delta": {"content": "late"}, "finish_reason": None}]},
        {"choices": [{"index": -1, "delta": {"content": "{}"}, "finish_reason": "stop"}]},
    ]
    capture = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames) + "data: [DONE]\n\n"
    assessments = sse.parse_capture(capture, "capture.sse")["json_text_assessments"]
    by_index = {item["choice_index"]: item for item in assessments if "choice_index" in item}
    assert by_index[0]["completion_status"] == "could_not_run"
    assert "follows terminal finish_reason" in by_index[0]["reason"]
    assert by_index[1]["json_syntax_status"] == "invalid_json"
    assert any(item["completion_status"] == "could_not_run" and
               "index" in item["reason"] for item in assessments if "choice_index" not in item)


def test_json_assessment_surrogate_and_deep_nesting_are_could_not_run():
    def capture_for(content):
        first = json.dumps({"choices": [{"index": 0, "delta": {"content": content},
                                          "finish_reason": None}]})
        end = json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        return f"data: {first}\n\ndata: {end}\n\ndata: [DONE]\n\n"

    lone_surrogate = sse.parse_capture(capture_for("\ud800"), "capture.sse")
    assert lone_surrogate["json_text_assessments"][0]["completion_status"] == "could_not_run"
    deeply_nested = sse.parse_capture(capture_for("[" * 10000 + "]" * 10000), "capture.sse")
    assessment = deeply_nested["json_text_assessments"][0]
    assert assessment["completion_status"] == "could_not_run"
    assert "recursion limit" in assessment["reason"]


def test_json_summary_cli_exit_codes_invalid_incomplete_and_empty(tmp_path):
    def run(name, content, finish, choices=True):
        capture = tmp_path / name
        frames = []
        if choices:
            frames.append({"choices": [{"index": 0, "delta": {"content": content},
                                         "finish_reason": None}]})
            frames.append({"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
        else:
            frames.append({"choices": []})
        raw = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        capture.write_text(raw + "data: [DONE]\n\n", encoding="utf-8")
        return subprocess.run([sys.executable, str(ROOT / "tools" / "chat_sse_capture.py"),
                               "--json-summary-only", str(capture)],
                              capture_output=True, text=True)

    invalid = run("invalid.sse", "{bad", "stop")
    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["json_assessment_counts"]["invalid_json"] == 1
    incomplete = run("incomplete.sse", "{}", "length")
    assert incomplete.returncode == 2
    assert json.loads(incomplete.stdout)["json_assessment_counts"]["incomplete"] == 1
    empty = run("empty.sse", "", "stop", choices=False)
    assert empty.returncode == 2
    payload = json.loads(empty.stdout)
    assert payload["json_assessment_counts"]["could_not_run"] == 1
    assert payload["json_text_assessments"][0]["reason"] == \
        "capture contains no choice response to assess"
    assert "status" in payload and "issues" in payload
    assert payload["could_not_run_count"] == 0


def test_usage_only_chunk_and_multiline_data_frame_are_preserved() -> None:
    result = sse.parse_capture(
        'data: {"id":"chat-2",\n'
        'data: "choices":[{"index":0,"delta":{"content":"x"},"finish_reason":"stop"}]}\n\n'
        'data: {"id":"chat-2","choices":[],"usage":{"total_tokens":3}}\n\n'
        'data: [DONE]\n\n',
        "capture.sse",
    )
    assert result["status"] == "observed"
    assert result["chunks"][1]["choices"] == []
    assert result["chunks"][1]["usage"] == {"total_tokens": 3}


def test_sse_cr_endings_bom_and_unicode_line_separator_inside_json() -> None:
    payload = '{"choices":[{"index":0,"delta":{"content":"a\u2028b\u2029c\u0085d"},"finish_reason":"stop"}]}'
    result = sse.parse_capture(
        "\ufeffdata: " + payload + "\r\rdata: [DONE]\r\r",
        "capture.sse",
    )
    assert result["status"] == "observed"
    assert result["chunks"][0]["choices"][0]["content_delta"] == "a\u2028b\u2029c\u0085d"


def test_sse_crlf_endings_are_delimited() -> None:
    result = sse.parse_capture(
        'data: {"choices":[]}\r\n\r\ndata: [DONE]\r\n\r\n',
        "capture.sse",
    )
    assert result["status"] == "observed"
    assert len(result["chunks"]) == 1


def test_sse_comments_unknown_fields_and_empty_frames_are_ignored() -> None:
    result = sse.parse_capture(
        ': keepalive\n'
        'event: chunk\n'
        'id: stream-1\n\n'
        'data: {"id":"chat-3","choices":[]}\n\n'
        'data: [DONE]\n\n',
        "capture.sse",
    )
    assert result["status"] == "observed"
    assert len(result["chunks"]) == 1


def test_missing_done_marker_is_incomplete_not_classified_as_cancelled() -> None:
    result = sse.parse_capture(
        'data: {"id":"chat-4","choices":[{"index":0,"delta":{"content":"partial"},"finish_reason":null}]}\n\n',
        "capture.sse",
    )
    assert result["status"] == "partial"
    assert result["done_marker_seen"] is False
    assert result["could_not_run_count"] == 1
    assert "termination cause unknown" in result["issues"][-1]


def test_unterminated_frame_is_preserved_as_raw_unparsed_data() -> None:
    raw = '{"id":"chat-5","choices":[]}'
    result = sse.parse_capture(f"data: {raw}\n", "capture.sse")
    assert result["status"] == "unknown"
    assert result["incomplete_frame_data"] == [raw]
    assert result["could_not_run_count"] == 2


def test_malformed_payloads_and_choice_shapes_count_unreadable_observations() -> None:
    result = sse.parse_capture(
        'data: not-json\n\n'
        'data: []\n\n'
        'data: {"choices":{}}\n\n'
        'data: {"choices":[null]}\n\n'
        'data: [DONE]\n\n',
        "capture.sse",
    )
    assert result["status"] == "unknown"
    assert result["unreadable_observation_count"] == 4
    assert result["could_not_run_count"] == 4


def test_non_json_nan_and_infinity_are_rejected_as_unreadable() -> None:
    result = sse.parse_capture(
        'data: {"choices":[],"usage":{"value":NaN}}\n\n'
        'data: {"choices":[],"usage":{"value":Infinity}}\n\n'
        'data: [DONE]\n\n',
        "capture.sse",
    )
    assert result["status"] == "unknown"
    assert result["unreadable_observation_count"] == 2
    assert result["could_not_run_count"] == 2


def test_duplicate_done_and_data_after_done_are_reported() -> None:
    result = sse.parse_capture(
        'data: {"choices":[]}\n\n'
        'data: [DONE]\n\n'
        'data: [DONE]\n\n'
        'data: {"choices":[]}\n\n',
        "capture.sse",
    )
    assert result["status"] == "partial"
    assert result["issues"] == [
        "event 3: duplicate [DONE] marker",
        "event 4: data after [DONE] marker",
    ]
    assert result["could_not_run_count"] == 1


def test_no_payload_returns_unknown_with_could_not_run() -> None:
    result = sse.parse_capture(": comment\n\n", "capture.sse")
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1


def test_read_errors_report_could_not_run(tmp_path: Path) -> None:
    missing = sse.analyze_file(tmp_path / "missing.sse")
    assert missing["status"] == "unknown"
    assert missing["could_not_run_count"] == 1
    invalid = tmp_path / "invalid.sse"
    invalid.write_bytes(b"\xff")
    assert sse.analyze_file(invalid)["could_not_run_count"] == 1


def test_cli_statuses_and_module_entrypoint(tmp_path: Path, capsys, monkeypatch) -> None:
    capture = tmp_path / "complete.sse"
    capture.write_text('data: {"choices":[]}\n\ndata: [DONE]\n\n', encoding="utf-8")
    assert sse.main([str(capture)]) == 0
    assert '"status": "observed"' in capsys.readouterr().out
    capture.write_text(": no chunks\n", encoding="utf-8")
    assert sse.main([str(capture)]) == 2
    assert '"status": "unknown"' in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", [str(sse.__file__), str(capture)])
    try:
        runpy.run_path(str(sse.__file__), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("module entry point did not exit")


def test_json_assessment_rejects_non_text_empty_output_and_missing_finish():
    for delta, finish, completion in [
        ({"content": {"text": "{}"}}, "stop", "could_not_run"),
        ({"content": None}, "stop", "could_not_run"),
        ({"content": ""}, "stop", "could_not_run"),
        ({"content": "{}"}, None, "incomplete"),
    ]:
        chunk = {"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        capture = "data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n"
        row = sse.parse_capture(capture, "fixture.sse")
        assert row["json_text_assessments"][0]["completion_status"] == completion
        assert row["json_assessment_counts"]["could_not_run"] == 1
        assert row["json_assessment_counts"]["valid_json"] == 0
