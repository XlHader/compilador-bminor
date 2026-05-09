from __future__ import annotations

from .models import IRInstruction, IRResult


def format_instruction(instruction: IRInstruction) -> str:
    if not instruction.args:
        return instruction.op
    args = ", ".join(_format_arg(arg) for arg in instruction.args)
    return f"{instruction.op} {args}"


def format_ir(result: IRResult) -> str:
    return "\n".join(
        format_instruction(instruction) for instruction in result.instructions
    )


def _format_arg(arg: object) -> str:
    if isinstance(arg, tuple):
        return "[" + ", ".join(_format_arg(item) for item in arg) + "]"
    return str(arg)


__all__ = ["format_instruction", "format_ir"]
