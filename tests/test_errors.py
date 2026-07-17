from __future__ import annotations
import pytest; from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))

from errors import ErrorCode, Severity, ErrorInfo, classify_error, exit_code


def test_known_pattern_classifies_correctly():
    info = classify_error("GRSAI_API_KEY 未配置")
    assert info.code == ErrorCode.PROVIDER_NOT_CONFIGURED
    assert info.severity == Severity.BLOCK


def test_unknown_error_falls_back():
    info = classify_error("something entirely unexpected happened here")
    assert info.code == ErrorCode.GENERATION_FAILED


def test_json_decode_errors():
    info = classify_error("JSONDecodeError: Expecting value: line 5 column 3")
    assert info.code == ErrorCode.FILE_CORRUPT


@pytest.mark.parametrize("msg,expected", [
    ("Permission denied", ErrorCode.FILE_MISSING),
    ("No such file or directory", ErrorCode.FILE_MISSING),
    ("schema validation failed", ErrorCode.SCHEMA_INVALID),
    ("missing required field 'shot_id'", ErrorCode.MISSING_REQUIRED_FIELD),
    ("Connection refused", ErrorCode.PROVIDER_UNAVAILABLE),
    ("prompt rejected by safety filter", ErrorCode.PROMPT_REJECTED),
])
def test_classify_error_parametrized(msg, expected):
    assert classify_error(msg).code == expected


def test_error_info_fields():
    info = classify_error("ConnectionError: timeout after 30s")
    assert info.code == ErrorCode.PROVIDER_UNAVAILABLE
    assert info.severity == Severity.DEGRADED
    assert "网络" in info.recovery


def test_exit_code_mapping():
    block = ErrorInfo(ErrorCode.GATE_BLOCKED, Severity.BLOCK, "blocked", "")
    assert exit_code(block) == 2
    warn = ErrorInfo(ErrorCode.GATE_WARNING, Severity.WARN, "warning", "")
    assert exit_code(warn) == 0
    gen = ErrorInfo(ErrorCode.GENERATION_FAILED, Severity.BLOCK, "fail", "")
    assert exit_code(gen) == 3
