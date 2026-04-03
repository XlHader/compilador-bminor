from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .symtab import SemanticScope


@dataclass(frozen=True, slots=True)
class SemanticError:
    message: str
    line: int | str
    column: int | str
    index: int | None
    context: str | None = None


@dataclass(frozen=True, slots=True)
class PrimitiveType:
    name: str


@dataclass(frozen=True, slots=True)
class ErrorType:
    pass


SemanticType = (
    PrimitiveType
    | ErrorType
    | "ArraySemanticType"
    | "FunctionSemanticType"
    | "ClassSemanticType"
)


@dataclass(frozen=True, slots=True)
class ArraySemanticType:
    element_type: SemanticType
    size: int | None = None


@dataclass(frozen=True, slots=True)
class FunctionSemanticType:
    return_type: SemanticType
    parameters: tuple[SemanticType, ...] = ()


@dataclass(frozen=True, slots=True)
class Symbol:
    name: str
    kind: str
    type: SemanticType
    node: object | None
    scope_name: str


@dataclass(frozen=True, slots=True)
class ClassSemanticType:
    name: str
    members: dict[str, Symbol] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "members", MappingProxyType(dict(self.members))
        )


@dataclass(slots=True)
class SemanticResult:
    errors: list[SemanticError] = field(default_factory=list)
    global_scope: SemanticScope | None = None
    node_types: dict[int, SemanticType] = field(default_factory=dict)
    resolved_symbols: dict[int, Symbol] = field(default_factory=dict)


__all__ = [
    "ArraySemanticType",
    "ClassSemanticType",
    "ErrorType",
    "FunctionSemanticType",
    "PrimitiveType",
    "SemanticError",
    "SemanticResult",
    "SemanticType",
    "Symbol",
]
