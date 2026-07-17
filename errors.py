"""Unified error codes with severity and recovery mapping.

Leaf module — imports nothing from the project. Every other module
can import from here without creating cycles.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    BLOCK = "block"
    DEGRADED = "degraded"
    WARN = "warn"


class ErrorCode(str, Enum):
    # File/IO
    FILE_MISSING = "E001"
    FILE_CORRUPT = "E002"
    # Contract/validation
    CONTRACT_VIOLATION = "E010"
    SCHEMA_INVALID = "E011"
    MISSING_REQUIRED_FIELD = "E012"
    # Generation
    GENERATION_FAILED = "E020"
    PROVIDER_UNAVAILABLE = "E021"
    PROMPT_REJECTED = "E022"
    IMAGE_INVALID = "E023"
    VIDEO_INVALID = "E024"
    AUDIO_INVALID = "E025"
    # Gate
    GATE_BLOCKED = "E030"
    GATE_WARNING = "E031"
    # Retake
    RETRY_BUDGET_EXHAUSTED = "E040"
    ONE_VARIABLE_VIOLATION = "E041"
    # Config
    PROVIDER_NOT_CONFIGURED = "E050"
    INVALID_PROVIDER = "E051"


_SEVERITY_MAP: dict[ErrorCode, Severity] = {
    ErrorCode.FILE_MISSING: Severity.BLOCK,
    ErrorCode.FILE_CORRUPT: Severity.BLOCK,
    ErrorCode.CONTRACT_VIOLATION: Severity.BLOCK,
    ErrorCode.SCHEMA_INVALID: Severity.BLOCK,
    ErrorCode.MISSING_REQUIRED_FIELD: Severity.BLOCK,
    ErrorCode.GENERATION_FAILED: Severity.BLOCK,
    ErrorCode.PROVIDER_UNAVAILABLE: Severity.DEGRADED,
    ErrorCode.PROMPT_REJECTED: Severity.BLOCK,
    ErrorCode.IMAGE_INVALID: Severity.BLOCK,
    ErrorCode.VIDEO_INVALID: Severity.BLOCK,
    ErrorCode.AUDIO_INVALID: Severity.BLOCK,
    ErrorCode.GATE_BLOCKED: Severity.BLOCK,
    ErrorCode.GATE_WARNING: Severity.WARN,
    ErrorCode.RETRY_BUDGET_EXHAUSTED: Severity.DEGRADED,
    ErrorCode.ONE_VARIABLE_VIOLATION: Severity.WARN,
    ErrorCode.PROVIDER_NOT_CONFIGURED: Severity.BLOCK,
    ErrorCode.INVALID_PROVIDER: Severity.BLOCK,
}

_ERROR_PATTERNS: list[tuple[str, ErrorCode, str]] = [
    ("GRSAI_API_KEY", ErrorCode.PROVIDER_NOT_CONFIGURED,
     "设置 GRSAI_API_KEY 环境变量"),
    ("GEMINI_API_KEY", ErrorCode.PROVIDER_NOT_CONFIGURED,
     "设置 GEMINI_API_KEY 环境变量"),
    ("RUNNINGHUB_API_KEY", ErrorCode.PROVIDER_NOT_CONFIGURED,
     "设置 RUNNINGHUB_API_KEY 环境变量"),
    ("No such file", ErrorCode.FILE_MISSING,
     "检查文件路径是否正确"),
    ("Permission denied", ErrorCode.FILE_MISSING,
     "检查文件读写权限"),
    ("JSONDecodeError", ErrorCode.FILE_CORRUPT,
     "JSON 文件格式损坏，需要修复或重新生成"),
    ("schema validation failed", ErrorCode.SCHEMA_INVALID,
     "检查数据是否符合 schema 规范"),
    ("missing required field", ErrorCode.MISSING_REQUIRED_FIELD,
     "补充必填字段"),
    ("Connection refused", ErrorCode.PROVIDER_UNAVAILABLE,
     "Provider 服务不可用，稍后重试"),
    ("ConnectionError", ErrorCode.PROVIDER_UNAVAILABLE,
     "网络连接失败，检查网络并重试"),
    ("safety filter", ErrorCode.PROMPT_REJECTED,
     "提示词被安全过滤，修改敏感词汇"),
    ("retry budget exhausted", ErrorCode.RETRY_BUDGET_EXHAUSTED,
     "已达最大重试次数，考虑修改上游内容"),
    ("gate blocked", ErrorCode.GATE_BLOCKED,
     "通过对应门控检查后再重试"),
    ("invalid provider", ErrorCode.INVALID_PROVIDER,
     "检查 PROVIDER 配置是否合法"),
]


@dataclass
class ErrorInfo:
    code: ErrorCode
    severity: Severity
    message: str
    recovery: str = ""


def classify_error(exc: Exception | str) -> ErrorInfo:
    """Classify an exception or error string into a structured ErrorInfo."""
    msg = str(exc)
    for pattern, code, recovery in _ERROR_PATTERNS:
        if pattern.lower() in msg.lower():
            return ErrorInfo(
                code=code,
                severity=_SEVERITY_MAP.get(code, Severity.BLOCK),
                message=msg,
                recovery=recovery,
            )
    return ErrorInfo(
        code=ErrorCode.GENERATION_FAILED,
        severity=Severity.BLOCK,
        message=msg,
        recovery="查看详细日志或 generate_log.json 排查原因",
    )


def exit_code(info: ErrorInfo) -> int:
    """Map ErrorInfo to a POSIX exit code."""
    if info.severity == Severity.WARN:
        return 0
    if info.code in (ErrorCode.GENERATION_FAILED, ErrorCode.PROVIDER_UNAVAILABLE):
        return 3
    if info.code in (ErrorCode.GATE_BLOCKED, ErrorCode.SCHEMA_INVALID,
                     ErrorCode.CONTRACT_VIOLATION):
        return 2
    return 1
