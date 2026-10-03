from pathlib import Path
import runpy
import sys

from tools import chat_sse_capture as sse


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
    assert result["done_marker_seen"] is True


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
