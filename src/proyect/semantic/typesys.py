from __future__ import annotations

from ..parser.models import (
    ArrayType,
    FunctionType,
    NamedType,
    SimpleType,
    TypeNode,
)
from .models import (
    ArraySemanticType,
    FunctionSemanticType,
    PrimitiveType,
    SemanticType,
)
from .symtab import SemanticScope

_BOOLEAN = PrimitiveType("boolean")


def _matches_exact_type(left: SemanticType, right: SemanticType) -> bool:
    return left == right


def _is_array_pair(left: SemanticType, right: SemanticType) -> bool:
    return isinstance(left, ArraySemanticType) and isinstance(
        right, ArraySemanticType
    )


def is_binary_operator_applicable(
    left: SemanticType,
    operator: str,
    right: SemanticType,
) -> SemanticType | None:
    integer = PrimitiveType("integer")
    float_type = PrimitiveType("float")
    boolean = PrimitiveType("boolean")
    char = PrimitiveType("char")
    string = PrimitiveType("string")

    if operator in {"+", "-", "*", "/", "%", "^"}:
        if _matches_exact_type(left, integer) and _matches_exact_type(
            right, integer
        ):
            return integer
    if operator in {"+", "-", "*", "/", "%"}:
        if _matches_exact_type(left, float_type) and _matches_exact_type(
            right, float_type
        ):
            return float_type
    if operator == "+" and _matches_exact_type(left, string):
        if _matches_exact_type(right, string):
            return string
    if operator in {"<", "<=", ">", ">="}:
        for primitive in (integer, float_type, char):
            if _matches_exact_type(left, primitive) and _matches_exact_type(
                right, primitive
            ):
                return _BOOLEAN
    if operator in {"==", "!="}:
        for primitive in (integer, float_type, boolean, char, string):
            if _matches_exact_type(left, primitive) and _matches_exact_type(
                right, primitive
            ):
                return _BOOLEAN
    if operator in {"&&", "||"}:
        if _matches_exact_type(left, boolean) and _matches_exact_type(
            right, boolean
        ):
            return _BOOLEAN
    return None


def is_unary_operator_applicable(
    operator: str,
    operand: SemanticType,
) -> SemanticType | None:
    integer = PrimitiveType("integer")
    float_type = PrimitiveType("float")

    if operator in {"+", "-"}:
        if _matches_exact_type(operand, integer):
            return integer
        if _matches_exact_type(operand, float_type):
            return float_type
    if operator == "!" and _matches_exact_type(operand, _BOOLEAN):
        return _BOOLEAN
    return None


def is_printable_type(semantic_type: SemanticType) -> bool:
    return semantic_type in {
        PrimitiveType("integer"),
        PrimitiveType("float"),
        PrimitiveType("boolean"),
        PrimitiveType("char"),
        PrimitiveType("string"),
    }


def are_assignment_compatible(
    expected: SemanticType,
    actual: SemanticType,
) -> bool:
    if _is_array_pair(expected, actual):
        return are_assignment_compatible(
            expected.element_type, actual.element_type
        )
    return expected == actual


def are_call_argument_compatible(
    expected: SemanticType,
    actual: SemanticType,
) -> bool:
    return are_assignment_compatible(expected, actual)


def resolve_type_node(
    type_node: TypeNode, scope: SemanticScope
) -> SemanticType | None:
    if isinstance(type_node, SimpleType):
        if type_node.name in {
            "integer",
            "float",
            "boolean",
            "char",
            "string",
            "void",
            "auto",
        }:
            return PrimitiveType(type_node.name)
        return None
    if isinstance(type_node, NamedType):
        return scope.lookup_type(type_node.name)
    if isinstance(type_node, ArrayType):
        element_type = resolve_type_node(type_node.element_type, scope)
        if element_type is None:
            return None
        return ArraySemanticType(element_type, None)
    if isinstance(type_node, FunctionType):
        return_type = resolve_type_node(type_node.return_type, scope)
        if return_type is None:
            return None
        parameters = []
        for parameter in type_node.parameters:
            parameter_type = resolve_type_node(parameter.type_node, scope)
            if parameter_type is None:
                return None
            parameters.append(parameter_type)
        return FunctionSemanticType(return_type, tuple(parameters))
    return None


__all__ = [
    "are_assignment_compatible",
    "are_call_argument_compatible",
    "is_binary_operator_applicable",
    "is_printable_type",
    "is_unary_operator_applicable",
    "resolve_type_node",
]
