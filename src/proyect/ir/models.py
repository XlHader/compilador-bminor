from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IRInstruction:
    op: str
    args: tuple[object, ...] = ()

    def as_tuple(self) -> tuple[object, ...]:
        return (self.op, *self.args)

    def __iter__(self) -> Iterator[object]:
        return iter(self.as_tuple())


@dataclass(frozen=True, slots=True)
class IRDiagnostic:
    message: str
    line: int | str = 0
    column: int | str = 0
    context: str | None = None


@dataclass(slots=True)
class IRResult:
    instructions: list[IRInstruction] = field(default_factory=list)
    diagnostics: list[IRDiagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    def to_tuples(self) -> list[tuple[object, ...]]:
        return [instruction.as_tuple() for instruction in self.instructions]


class RegisterGenerator:
    def __init__(self) -> None:
        self._next = 1

    def new(self) -> str:
        register = f"R{self._next}"
        self._next += 1
        return register


class LabelGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new(self, prefix: str = "L") -> str:
        next_value = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = next_value
        return f"{prefix}{next_value}"


__all__ = [
    "IRDiagnostic",
    "IRInstruction",
    "IRResult",
    "LabelGenerator",
    "RegisterGenerator",
]
