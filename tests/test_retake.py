from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))

from director import ShootProtocol, Verdict


def test_history_round_trip():
    """ShootProtocol save/load history round-trips correctly"""
    p1 = ShootProtocol(max_attempts=5)
    p1.record_attempt("s01", Verdict.REGEN, change="seed", note="first try")
    p1.record_attempt("s01", Verdict.KEEP, change="prompt", note="second try")

    with tempfile.TemporaryDirectory() as td:
        hp = Path(td) / "retake_history.json"
        p1.save_history(hp)
        assert hp.is_file()

        p2 = ShootProtocol(max_attempts=5)
        p2.load_history(hp)
        assert p2.remaining("s01") == 3  # 5 - 2
        assert len(p2._history.get("s01", [])) == 2


def test_load_nonexistent_is_noop():
    """Loading non-existent file is a no-op"""
    p = ShootProtocol(max_attempts=5)
    p.load_history(Path("/nonexistent/path.json"))
    assert p.remaining("any") == 5


def test_retake_controller_one_variable_rule():
    """One-variable rule: seed → prompt → style → escalate"""
    from stages.retake import RetakeController
    rc = RetakeController(max_attempts=5)
    prompt = "一个男人走进办公室"
    # Attempt 1: seed
    p1, s1 = rc.apply_one_variable_rule("s01", prompt)
    assert s1 is not None
    # Attempt 2: prompt
    p2, s2 = rc.apply_one_variable_rule("s01", p1, current_seed=s1)
    assert "微调构图" in p2
    # Attempt 3: style
    prompt_with_style = p2 + "\n画风：影视写实"
    p3, s3 = rc.apply_one_variable_rule("s01", prompt_with_style, current_seed=s2)
    assert "画风：" not in p3


def test_retake_budget_exhaustion():
    """should_retry returns False after budget exhausted"""
    from stages.retake import RetakeController
    rc = RetakeController(max_attempts=2)
    assert rc.should_retry("s01", "connection error")
    rc.record("s01", False, "fail 1")
    assert rc.should_retry("s01", "connection error")
    rc.record("s01", False, "fail 2")
    assert not rc.should_retry("s01", "connection error")


def test_retake_controller_get_result():
    """get_result returns correct RetakeResult"""
    from stages.retake import RetakeController
    rc = RetakeController(max_attempts=3)
    rc.record("s01", False, "failed")
    rc.record("s01", True, "succeeded")
    result = rc.get_result("s01")
    assert result.success
    assert result.attempts_used == 2
