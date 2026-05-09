from __future__ import annotations

from proyect.semantic.models import (
    ArraySemanticType,
    ClassSemanticType,
    FunctionSemanticType,
    PrimitiveType,
)


def type_suffix(semantic_type: object) -> str:
    if isinstance(semantic_type, PrimitiveType):
        if semantic_type.name in {"integer", "boolean"}:
            return "I"
        if semantic_type.name == "float":
            return "F"
        if semantic_type.name == "char":
            return "B"
        if semantic_type.name == "string":
            return "S"
    if isinstance(
        semantic_type,
        (ArraySemanticType, ClassSemanticType, FunctionSemanticType),
    ):
        return "REF"
    return "REF"


def load_opcode(semantic_type: object) -> str:
    return f"LOAD{type_suffix(semantic_type)}"


def store_opcode(semantic_type: object) -> str:
    return f"STORE{type_suffix(semantic_type)}"


def var_opcode(semantic_type: object) -> str:
    return f"VAR{type_suffix(semantic_type)}"


def alloc_opcode(semantic_type: object) -> str:
    return f"ALLOC{type_suffix(semantic_type)}"


def param_opcode(semantic_type: object) -> str:
    return f"PARAM{type_suffix(semantic_type)}"


def print_opcode(semantic_type: object) -> str:
    return f"PRINT{type_suffix(semantic_type)}"


__all__ = [
    "alloc_opcode",
    "load_opcode",
    "param_opcode",
    "print_opcode",
    "store_opcode",
    "type_suffix",
    "var_opcode",
]
