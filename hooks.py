"""
Plugin hook system — register and dispatch hooks for commands, gates, and exports.

Usage:
    from hooks import register_command, on_command

    def my_handler(args):
        return {"result": "ok"}

    register_command("my-command", my_handler)
    result = on_command("my-command", {"arg1": "val"})
"""

# ---------------------------------------------------------------------------
# Registries (dict-based, no decorators)
# ---------------------------------------------------------------------------

_command_registry: dict[str, callable] = {}
_gate_registry: dict[str, callable] = {}
_exporter_registry: dict[str, callable] = {}


# ---------------------------------------------------------------------------
# Registration helpers
# ---------------------------------------------------------------------------

def register_command(name: str, handler: callable) -> None:
    """Register a command handler under *name*."""
    _command_registry[name] = handler


def register_gate(name: str, handler: callable) -> None:
    """Register a gate handler under *name*."""
    _gate_registry[name] = handler


def register_exporter(name: str, handler: callable) -> None:
    """Register an export handler under *name*."""
    _exporter_registry[name] = handler


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------

def on_command(name: str, args: dict) -> dict:
    """Dispatch a command by *name* with *args*.

    Returns the handler's result as a dict.
    Raises KeyError if *name* is not registered.
    """
    handler = _command_registry.get(name)
    if handler is None:
        raise KeyError(f"Unknown command: {name!r} (registered: {list(_command_registry)})")
    return handler(args)


def on_gate(name: str, context: dict) -> dict:
    """Run a gate check by *name* with *context*.

    Returns a dict with keys:
        passed   — bool, whether the gate passed
        errors   — list of error strings
        warnings — list of warning strings
    If *name* is not registered, returns a "pass" by default.
    """
    handler = _gate_registry.get(name)
    if handler is None:
        return {"passed": True, "errors": [], "warnings": []}
    return handler(context)


def on_export(fmt: str, compiled: dict, out_dir: str) -> None:
    """Dispatch an export by format *fmt*.

    Raises KeyError if *fmt* is not registered.
    """
    handler = _exporter_registry.get(fmt)
    if handler is None:
        raise KeyError(f"Unknown export format: {fmt!r} (registered: {list(_exporter_registry)})")
    handler(compiled, out_dir)
