from __future__ import annotations

from .models import SemanticType, Symbol


class SemanticScope:
    def __init__(self, name: str, parent: SemanticScope | None = None) -> None:
        self.name = name
        self.parent = parent
        self.value_symbols: dict[str, Symbol] = {}
        self.type_symbols: dict[str, SemanticType] = {}

    def define_value(self, symbol: Symbol) -> Symbol:
        if symbol.name in self.value_symbols:
            raise ValueError(f"value symbol '{symbol.name}' already declared")
        self.value_symbols[symbol.name] = symbol
        return symbol

    def lookup_value(self, name: str) -> Symbol | None:
        if name in self.value_symbols:
            return self.value_symbols[name]
        if self.parent is None:
            return None
        return self.parent.lookup_value(name)

    def define_type(
        self, name: str, semantic_type: SemanticType
    ) -> SemanticType:
        if name in self.type_symbols:
            raise ValueError(f"type symbol '{name}' already declared")
        self.type_symbols[name] = semantic_type
        return semantic_type

    def lookup_type(self, name: str) -> SemanticType | None:
        if name in self.type_symbols:
            return self.type_symbols[name]
        if self.parent is None:
            return None
        return self.parent.lookup_type(name)


__all__ = ["SemanticScope"]
