from pathlib import Path

import pytest

from proyect.parser.models import (
    ArrayType,
    BlockStmt,
    ExprStmt,
    FunctionType,
    IdentifierExpr,
    LiteralExpr,
    NamedType,
    Parameter,
    Program,
    ReturnStmt,
    SimpleType,
    SourceSpan,
)
from proyect.semantic import (
    ArraySemanticType,
    ClassSemanticType,
    ErrorType,
    FunctionSemanticType,
    PrimitiveType,
    SemanticError,
    SemanticResult,
    SemanticScope,
    analyze_semantic,
)
from proyect.semantic.models import Symbol
from proyect.semantic.typesys import (
    are_assignment_compatible,
    are_call_argument_compatible,
    is_binary_operator_applicable,
    is_printable_type,
    is_unary_operator_applicable,
    resolve_type_node,
)


def _span() -> SourceSpan:
    return SourceSpan(line=1, column=1, index=0, end=0)


def _program(*declarations) -> Program:
    return Program(span=_span(), declarations=list(declarations))


def _var(name: str, type_node, initializer=None) -> object:
    from proyect.parser.models import VarDecl

    return VarDecl(
        span=_span(),
        name=name,
        type_node=type_node,
        initializer=initializer,
    )


_DEFAULT_BODY = object()


def _func(
    name: str, return_type, parameters=None, body=_DEFAULT_BODY
) -> object:
    from proyect.parser.models import FunctionDecl, FunctionType

    function_type = FunctionType(
        span=_span(),
        return_type=return_type,
        parameters=parameters or [],
    )
    return FunctionDecl(
        span=_span(),
        name=name,
        function_type=function_type,
        body=(
            BlockStmt(span=_span(), statements=[])
            if body is _DEFAULT_BODY
            else body
        ),
    )


def _class(name: str, members=None) -> object:
    from proyect.parser.models import ClassDecl

    return ClassDecl(span=_span(), name=name, members=members or [])


def test_import_analyze_semantic() -> None:
    assert callable(analyze_semantic)


def test_analyze_semantic_returns_bootstrap_result() -> None:
    program = Program(
        span=SourceSpan(line=1, column=1, index=0, end=0),
        declarations=[],
    )

    result = analyze_semantic(program)

    assert isinstance(result, SemanticResult)
    assert result.global_scope is not None


def test_semantic_result_stores_state() -> None:
    errors = [SemanticError("msg", 1, 2, 3, "ctx")]
    global_scope = SemanticScope("global")
    symbol = Symbol(
        name="x",
        kind="variable",
        type=PrimitiveType("integer"),
        node=None,
        scope_name="global",
    )
    node_types = {1: PrimitiveType("integer")}
    resolved_symbols = {1: symbol}

    result = SemanticResult(
        errors=errors,
        global_scope=global_scope,
        node_types=node_types,
        resolved_symbols=resolved_symbols,
    )

    assert result.errors == errors
    assert result.global_scope is global_scope
    assert result.node_types == node_types
    assert result.resolved_symbols == resolved_symbols


def test_semantic_error_exposes_fields() -> None:
    error = SemanticError("msg", 1, 2, 3, "ctx")

    assert error.message == "msg"
    assert error.line == 1
    assert error.column == 2
    assert error.index == 3
    assert error.context == "ctx"


def test_semantic_types_shape() -> None:
    primitive = PrimitiveType("integer")
    array_type = ArraySemanticType(primitive, 3)
    function_type = FunctionSemanticType(
        return_type=primitive, parameters=(primitive,)
    )
    class_type = ClassSemanticType(name="Foo")
    error_type = ErrorType()

    assert primitive.name == "integer"
    assert array_type.element_type is primitive
    assert array_type.size == 3
    assert function_type.parameters == (primitive,)
    assert function_type.return_type is primitive
    assert class_type.name == "Foo"
    assert class_type.members == {}
    assert error_type != primitive


def test_semantic_scope_resolves_parent_value_symbols() -> None:
    primitive = PrimitiveType("integer")
    symbol = Symbol(
        name="x",
        kind="variable",
        type=primitive,
        node=None,
        scope_name="global",
    )
    parent = SemanticScope("global")
    parent.define_value(symbol)
    child = SemanticScope("block", parent=parent)

    assert child.lookup_value("x") is symbol


def test_semantic_scope_rejects_duplicate_value_symbols() -> None:
    primitive = PrimitiveType("integer")
    scope = SemanticScope("global")
    scope.define_value(Symbol("x", "variable", primitive, None, "global"))

    with pytest.raises(ValueError):
        scope.define_value(Symbol("x", "variable", primitive, None, "global"))


def test_semantic_scope_resolves_parent_type_symbols() -> None:
    primitive = PrimitiveType("integer")
    parent = SemanticScope("global")
    parent.define_type("integer", primitive)
    child = SemanticScope("block", parent=parent)

    assert child.lookup_type("integer") is primitive


def test_semantic_scope_rejects_duplicate_type_symbols() -> None:
    primitive = PrimitiveType("integer")
    scope = SemanticScope("global")
    scope.define_type("integer", primitive)

    with pytest.raises(ValueError):
        scope.define_type("integer", primitive)


def test_semantic_scope_separates_type_and_value_namespaces() -> None:
    primitive = PrimitiveType("integer")
    symbol = Symbol("integer", "variable", primitive, None, "global")
    scope = SemanticScope("global")

    scope.define_type("integer", primitive)
    scope.define_value(symbol)

    assert scope.lookup_type("integer") is primitive
    assert scope.lookup_value("integer") is symbol


def test_error_type_differs_from_primitive_type() -> None:
    assert ErrorType() != PrimitiveType("error")


def test_binary_operator_exact_match() -> None:
    integer = PrimitiveType("integer")
    boolean = PrimitiveType("boolean")

    assert is_binary_operator_applicable(integer, "+", integer) == integer
    assert is_binary_operator_applicable(integer, "+", boolean) is None


def test_unary_operator_exact_match() -> None:
    boolean = PrimitiveType("boolean")

    assert is_unary_operator_applicable("!", boolean) == boolean


def test_printable_types_include_string() -> None:
    assert is_printable_type(PrimitiveType("string"))


def test_printable_types_include_float_and_char() -> None:
    assert is_printable_type(PrimitiveType("float"))
    assert is_printable_type(PrimitiveType("char"))


def test_array_compatibility_uses_element_type() -> None:
    left = ArraySemanticType(PrimitiveType("integer"), 2)
    right = ArraySemanticType(PrimitiveType("integer"), 9)
    other = ArraySemanticType(PrimitiveType("boolean"), 2)

    assert are_assignment_compatible(left, right)
    assert are_call_argument_compatible(left, right)
    assert not are_assignment_compatible(left, other)


def test_nested_array_compatibility_ignores_size_metadata_recursively() -> (
    None
):
    left = ArraySemanticType(ArraySemanticType(PrimitiveType("integer"), 2), 4)
    right = ArraySemanticType(
        ArraySemanticType(PrimitiveType("integer"), 9), 7
    )
    other = ArraySemanticType(
        ArraySemanticType(PrimitiveType("boolean"), 9), 7
    )

    assert are_assignment_compatible(left, right)
    assert not are_assignment_compatible(left, other)


def test_binary_operator_matrix_covers_more_exact_cases() -> None:
    integer = PrimitiveType("integer")
    float_type = PrimitiveType("float")
    boolean = PrimitiveType("boolean")
    string = PrimitiveType("string")
    char = PrimitiveType("char")

    assert is_binary_operator_applicable(integer, "-", integer) == integer
    assert is_binary_operator_applicable(integer, "*", integer) == integer
    assert is_binary_operator_applicable(integer, "/", integer) == integer
    assert is_binary_operator_applicable(integer, "%", integer) == integer
    assert is_binary_operator_applicable(integer, "^", integer) == integer
    assert (
        is_binary_operator_applicable(float_type, "+", float_type)
        == float_type
    )
    assert is_binary_operator_applicable(string, "+", string) == string
    assert is_binary_operator_applicable(
        integer, "<", integer
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(char, "<", char) == PrimitiveType(
        "boolean"
    )
    assert is_binary_operator_applicable(
        boolean, "&&", boolean
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        boolean, "||", boolean
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        integer, "<=", integer
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        integer, ">", integer
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        integer, ">=", integer
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        integer, "==", integer
    ) == PrimitiveType("boolean")
    assert is_binary_operator_applicable(
        integer, "!=", integer
    ) == PrimitiveType("boolean")
    assert (
        is_binary_operator_applicable(float_type, "-", float_type)
        == float_type
    )
    assert (
        is_binary_operator_applicable(float_type, "*", float_type)
        == float_type
    )
    assert (
        is_binary_operator_applicable(float_type, "/", float_type)
        == float_type
    )
    assert (
        is_binary_operator_applicable(float_type, "%", float_type)
        == float_type
    )


def test_unary_operator_matrix_covers_numeric_cases() -> None:
    integer = PrimitiveType("integer")
    float_type = PrimitiveType("float")

    assert is_unary_operator_applicable("+", integer) == integer
    assert is_unary_operator_applicable("-", integer) == integer
    assert is_unary_operator_applicable("+", float_type) == float_type
    assert is_unary_operator_applicable("-", float_type) == float_type


def test_resolve_type_node_handles_simple_named_and_array_types() -> None:
    scope = SemanticScope("global")
    scope.define_type("Foo", ClassSemanticType("Foo"))
    span = SourceSpan(line=1, column=1, index=0, end=0)

    assert resolve_type_node(
        SimpleType(span=span, name="integer"), scope
    ) == PrimitiveType("integer")
    assert resolve_type_node(
        NamedType(span=span, name="Foo"), scope
    ) == ClassSemanticType("Foo")
    assert resolve_type_node(
        ArrayType(
            span=span,
            element_type=SimpleType(span=span, name="integer"),
            size=None,
        ),
        scope,
    ) == ArraySemanticType(PrimitiveType("integer"), None)


def test_resolve_type_node_handles_function_types() -> None:
    scope = SemanticScope("global")
    scope.define_type("Foo", ClassSemanticType("Foo"))
    span = SourceSpan(line=1, column=1, index=0, end=0)
    function_type = FunctionType(
        span=span,
        return_type=SimpleType(span=span, name="integer"),
        parameters=[
            Parameter(
                span=span,
                name="x",
                type_node=NamedType(span=span, name="Foo"),
            )
        ],
    )

    assert resolve_type_node(function_type, scope) == FunctionSemanticType(
        return_type=PrimitiveType("integer"),
        parameters=(ClassSemanticType("Foo"),),
    )


def test_semantic_reports_undeclared_identifier() -> None:
    from proyect.parser.models import BlockStmt, ExprStmt, IdentifierExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=IdentifierExpr(span=_span(), name="x"),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("undeclared" in error.message for error in result.errors)


def test_semantic_rejects_redeclaration_in_same_scope() -> None:
    from proyect.parser.models import BlockStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("x", SimpleType(span=_span(), name="integer")),
                    _var("x", SimpleType(span=_span(), name="integer")),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_allows_shadowing_in_nested_block() -> None:
    from proyect.parser.models import BlockStmt

    program = _program(
        _var("x", SimpleType(span=_span(), name="integer")),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    BlockStmt(
                        span=_span(),
                        statements=[
                            _var("x", SimpleType(span=_span(), name="integer"))
                        ],
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_global_use_before_declaration() -> None:
    from proyect.parser.models import ExprStmt, IdentifierExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=IdentifierExpr(span=_span(), name="x"),
                    )
                ],
            ),
        ),
        _var("x", SimpleType(span=_span(), name="integer")),
    )

    result = analyze_semantic(program)

    assert any("undeclared" in error.message for error in result.errors)


def test_semantic_allows_function_use_before_definition() -> None:
    from proyect.parser.models import (
        BlockStmt,
        ExprStmt,
        IdentifierExpr,
        ReturnStmt,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=IdentifierExpr(span=_span(), name="helper"),
                    )
                ],
            ),
        ),
        _func(
            "helper",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=1, literal_type="integer"
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_incompatible_prototype_definition() -> None:
    program = _program(
        _func(
            "helper",
            SimpleType(span=_span(), name="integer"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                )
            ],
            body=None,
        ),
        _func("helper", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any(
        "prototype" in error.message.lower()
        or "definition" in error.message.lower()
        for error in result.errors
    )


def test_semantic_rejects_nested_function_definition() -> None:
    from proyect.parser.models import BlockStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _func("nested", SimpleType(span=_span(), name="void"))
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("nested" in error.message.lower() for error in result.errors)


def test_semantic_rejects_nested_class_definition() -> None:
    from proyect.parser.models import BlockStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(span=_span(), statements=[_class("Inner")]),
        )
    )

    result = analyze_semantic(program)

    assert any("nested" in error.message.lower() for error in result.errors)


def test_semantic_allows_forward_class_reference_in_variable_type() -> None:
    program = _program(
        _var("x", NamedType(span=_span(), name="Foo")),
        _class("Foo"),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_duplicate_function_definition() -> None:
    program = _program(
        _func("main", SimpleType(span=_span(), name="void")),
        _func("helper", SimpleType(span=_span(), name="integer")),
        _func("helper", SimpleType(span=_span(), name="integer")),
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_rejects_prototype_after_definition() -> None:
    program = _program(
        _func("main", SimpleType(span=_span(), name="void")),
        _func("helper", SimpleType(span=_span(), name="integer")),
        _func("helper", SimpleType(span=_span(), name="integer"), body=None),
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_rejects_duplicate_class_definition() -> None:
    program = _program(
        _class("Foo"),
        _class("Foo"),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_allows_class_and_value_same_name() -> None:
    program = _program(
        _class("Foo"),
        _var("Foo", SimpleType(span=_span(), name="integer")),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_global_initializer_use_before_declaration() -> None:
    from proyect.parser.models import IdentifierExpr

    program = _program(
        _var(
            "x",
            SimpleType(span=_span(), name="integer"),
            initializer=IdentifierExpr(span=_span(), name="y"),
        ),
        _var("y", SimpleType(span=_span(), name="integer")),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any(
        "undeclared" in error.message.lower() for error in result.errors
    )


def test_semantic_rejects_composite_global_initializer_forward_ref() -> None:
    from proyect.parser.models import BinaryExpr, IdentifierExpr, LiteralExpr

    program = _program(
        _var(
            "x",
            SimpleType(span=_span(), name="integer"),
            initializer=BinaryExpr(
                span=_span(),
                operator="+",
                left=IdentifierExpr(span=_span(), name="y"),
                right=LiteralExpr(
                    span=_span(), value=1, literal_type="integer"
                ),
            ),
        ),
        _var("y", SimpleType(span=_span(), name="integer")),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any(
        "undeclared" in error.message.lower() for error in result.errors
    )


def test_semantic_requires_main() -> None:
    program = _program(_var("x", SimpleType(span=_span(), name="integer")))

    result = analyze_semantic(program)

    assert any("main" in error.message.lower() for error in result.errors)


def test_semantic_rejects_main_prototype_without_body() -> None:
    program = _program(
        _func("main", SimpleType(span=_span(), name="void"), body=None)
    )

    result = analyze_semantic(program)

    assert any("main" in error.message.lower() for error in result.errors)


def test_semantic_rejects_invalid_main_return_type() -> None:
    program = _program(_func("main", SimpleType(span=_span(), name="string")))

    result = analyze_semantic(program)

    assert any("main" in error.message.lower() for error in result.errors)


def test_semantic_accepts_void_main() -> None:
    program = _program(_func("main", SimpleType(span=_span(), name="void")))

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_accepts_typed_main_parameters() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="argc",
                    type_node=SimpleType(span=_span(), name="integer"),
                ),
                Parameter(
                    span=_span(),
                    name="argv",
                    type_node=NamedType(span=_span(), name="Foo"),
                ),
            ],
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    )
                ],
            ),
        ),
        _class("Foo"),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_local_redeclaration_of_parameter() -> None:
    from proyect.parser.models import BlockStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                )
            ],
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("x", SimpleType(span=_span(), name="integer"))
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_rejects_unknown_type_in_function_signature() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=NamedType(span=_span(), name="Missing"),
                )
            ],
        )
    )

    result = analyze_semantic(program)

    assert any("type" in error.message.lower() for error in result.errors)


def test_semantic_rejects_duplicate_parameter_in_prototype() -> None:
    program = _program(
        _func(
            "helper",
            SimpleType(span=_span(), name="void"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                ),
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                ),
            ],
            body=None,
        ),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_rejects_unknown_type_in_prototype_signature() -> None:
    program = _program(
        _func(
            "helper",
            SimpleType(span=_span(), name="void"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=NamedType(span=_span(), name="Missing"),
                )
            ],
            body=None,
        ),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("type" in error.message.lower() for error in result.errors)


def test_semantic_reserves_name_after_invalid_function_signature() -> None:
    program = _program(
        _func(
            "helper",
            NamedType(span=_span(), name="Missing"),
            body=None,
        ),
        _func("helper", SimpleType(span=_span(), name="void")),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("redecl" in error.message.lower() for error in result.errors)


def test_semantic_rejects_incompatible_assignment() -> None:
    from proyect.parser.models import (
        AssignmentExpr,
        ExprStmt,
        IdentifierExpr,
        LiteralExpr,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("x", SimpleType(span=_span(), name="integer")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="x"),
                            value=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("integer" in error.message.lower() for error in result.errors)


def test_semantic_infers_auto_from_initializer() -> None:
    from proyect.parser.models import LiteralExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "x",
                        SimpleType(span=_span(), name="auto"),
                        initializer=LiteralExpr(
                            span=_span(),
                            value=1,
                            literal_type="integer",
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_auto_without_initializer() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[_var("x", SimpleType(span=_span(), name="auto"))],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("auto" in error.message.lower() for error in result.errors)


def test_semantic_rejects_auto_initialized_from_void_call() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr

    program = _program(
        _func("noop", SimpleType(span=_span(), name="void")),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "x",
                        SimpleType(span=_span(), name="auto"),
                        initializer=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(span=_span(), name="noop"),
                            arguments=[],
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("auto" in error.message.lower() for error in result.errors)


def test_semantic_rejects_increment_on_non_lvalue() -> None:
    from proyect.parser.models import (
        BinaryExpr,
        ExprStmt,
        LiteralExpr,
        UnaryExpr,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=UnaryExpr(
                            span=_span(),
                            operator="++",
                            operand=BinaryExpr(
                                span=_span(),
                                operator="+",
                                left=LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                ),
                                right=LiteralExpr(
                                    span=_span(),
                                    value=2,
                                    literal_type="integer",
                                ),
                            ),
                            position="post",
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("lvalue" in error.message.lower() for error in result.errors)


def test_semantic_rejects_increment_on_boolean() -> None:
    from proyect.parser.models import (
        ExprStmt,
        IdentifierExpr,
        LiteralExpr,
        UnaryExpr,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "flag",
                        SimpleType(span=_span(), name="boolean"),
                        initializer=LiteralExpr(
                            span=_span(),
                            value=True,
                            literal_type="boolean",
                        ),
                    ),
                    ExprStmt(
                        span=_span(),
                        expression=UnaryExpr(
                            span=_span(),
                            operator="++",
                            operand=IdentifierExpr(span=_span(), name="flag"),
                            position="post",
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("numeric" in error.message.lower() for error in result.errors)


def test_semantic_rejects_wrong_argument_count() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr, ReturnStmt

    program = _program(
        _func(
            "f",
            SimpleType(span=_span(), name="integer"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                )
            ],
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=IdentifierExpr(span=_span(), name="x"),
                    )
                ],
            ),
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(span=_span(), name="f"),
                            arguments=[
                                LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                ),
                                LiteralExpr(
                                    span=_span(),
                                    value=2,
                                    literal_type="integer",
                                ),
                            ],
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("arity" in error.message.lower() for error in result.errors)


def test_semantic_accepts_call_to_prototype_without_body() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr, ReturnStmt

    program = _program(
        _func(
            "puts",
            SimpleType(span=_span(), name="void"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="s",
                    type_node=SimpleType(span=_span(), name="string"),
                )
            ],
            body=None,
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(span=_span(), name="puts"),
                            arguments=[
                                LiteralExpr(
                                    span=_span(),
                                    value="hi",
                                    literal_type="string",
                                )
                            ],
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_call_on_non_callable() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("x", SimpleType(span=_span(), name="integer")),
                    ExprStmt(
                        span=_span(),
                        expression=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(span=_span(), name="x"),
                            arguments=[],
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("call" in error.message.lower() for error in result.errors)


def test_semantic_rejects_wrong_argument_type() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr, ReturnStmt

    program = _program(
        _func(
            "f",
            SimpleType(span=_span(), name="integer"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="x",
                    type_node=SimpleType(span=_span(), name="integer"),
                )
            ],
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=IdentifierExpr(span=_span(), name="x"),
                    )
                ],
            ),
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(span=_span(), name="f"),
                            arguments=[
                                LiteralExpr(
                                    span=_span(),
                                    value=True,
                                    literal_type="boolean",
                                )
                            ],
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("argument" in error.message.lower() for error in result.errors)


def test_semantic_rejects_ternary_with_non_boolean_condition() -> None:
    from proyect.parser.models import ConditionalExpr, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=ConditionalExpr(
                            span=_span(),
                            condition=LiteralExpr(
                                span=_span(), value=1, literal_type="integer"
                            ),
                            then_expr=LiteralExpr(
                                span=_span(), value=2, literal_type="integer"
                            ),
                            else_expr=LiteralExpr(
                                span=_span(), value=3, literal_type="integer"
                            ),
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("boolean" in error.message.lower() for error in result.errors)


def test_semantic_rejects_ternary_with_incompatible_branches() -> None:
    from proyect.parser.models import ConditionalExpr, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=ConditionalExpr(
                            span=_span(),
                            condition=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                            then_expr=LiteralExpr(
                                span=_span(), value=1, literal_type="integer"
                            ),
                            else_expr=LiteralExpr(
                                span=_span(),
                                value="x",
                                literal_type="string",
                            ),
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("branch" in error.message.lower() for error in result.errors)


def test_semantic_rejects_non_boolean_if_condition() -> None:
    from proyect.parser.models import IfStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    IfStmt(
                        span=_span(),
                        condition=LiteralExpr(
                            span=_span(), value=1, literal_type="integer"
                        ),
                        then_branch=BlockStmt(span=_span(), statements=[]),
                        else_branch=None,
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("boolean" in error.message.lower() for error in result.errors)


def test_semantic_rejects_missing_if_condition() -> None:
    from proyect.parser.models import IfStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    IfStmt(
                        span=_span(),
                        condition=None,
                        then_branch=BlockStmt(span=_span(), statements=[]),
                        else_branch=None,
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("condition" in error.message.lower() for error in result.errors)


def test_semantic_rejects_missing_while_condition() -> None:
    from proyect.parser.models import ReturnStmt, WhileStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    WhileStmt(
                        span=_span(),
                        condition=None,
                        body=BlockStmt(span=_span(), statements=[]),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("condition" in error.message.lower() for error in result.errors)


def test_semantic_allows_missing_for_condition() -> None:
    from proyect.parser.models import ForStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ForStmt(
                        span=_span(),
                        initializer=None,
                        condition=None,
                        update=None,
                        body=BlockStmt(span=_span(), statements=[]),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_non_boolean_for_condition() -> None:
    from proyect.parser.models import ForStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ForStmt(
                        span=_span(),
                        initializer=None,
                        condition=LiteralExpr(
                            span=_span(), value=1, literal_type="integer"
                        ),
                        update=None,
                        body=BlockStmt(span=_span(), statements=[]),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("boolean" in error.message.lower() for error in result.errors)


def test_semantic_rejects_wrong_return_type() -> None:
    from proyect.parser.models import ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(),
                            value=True,
                            literal_type="boolean",
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("return" in error.message.lower() for error in result.errors)


def test_semantic_rejects_return_value_in_void_function() -> None:
    from proyect.parser.models import ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=1, literal_type="integer"
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("return" in error.message.lower() for error in result.errors)


def test_semantic_rejects_missing_return_in_non_void_function() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(span=_span(), statements=[]),
        )
    )

    result = analyze_semantic(program)

    assert any("return" in error.message.lower() for error in result.errors)


def test_semantic_accepts_print_of_primitives() -> None:
    from proyect.parser.models import PrintStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    PrintStmt(
                        span=_span(),
                        expressions=[
                            LiteralExpr(
                                span=_span(), value=1, literal_type="integer"
                            ),
                            LiteralExpr(
                                span=_span(),
                                value="x",
                                literal_type="string",
                            ),
                            LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ],
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_accepts_empty_print() -> None:
    from proyect.parser.models import PrintStmt, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    PrintStmt(span=_span(), expressions=[]),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_print_of_function_value() -> None:
    from proyect.parser.models import PrintStmt, ReturnStmt

    program = _program(
        _func("f", SimpleType(span=_span(), name="integer")),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    PrintStmt(
                        span=_span(),
                        expressions=[IdentifierExpr(span=_span(), name="f")],
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("print" in error.message.lower() for error in result.errors)


def test_semantic_accumulates_multiple_errors() -> None:
    from proyect.parser.models import (
        AssignmentExpr,
        ExprStmt,
        IdentifierExpr,
        IfStmt,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="x"),
                            value=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                    IfStmt(
                        span=_span(),
                        condition=LiteralExpr(
                            span=_span(), value=1, literal_type="integer"
                        ),
                        then_branch=BlockStmt(span=_span(), statements=[]),
                        else_branch=None,
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=IdentifierExpr(span=_span(), name="foo"),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert len(result.errors) >= 3


def test_semantic_accepts_array_length_intrinsic() -> None:
    from proyect.parser.models import (
        ArrayInitializer,
        CallExpr,
        IdentifierExpr,
        ReturnStmt,
    )

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(), value=3, literal_type="integer"
                            ),
                        ),
                        initializer=ArrayInitializer(
                            span=_span(),
                            elements=[
                                LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                ),
                                LiteralExpr(
                                    span=_span(),
                                    value=2,
                                    literal_type="integer",
                                ),
                                LiteralExpr(
                                    span=_span(),
                                    value=3,
                                    literal_type="integer",
                                ),
                            ],
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(
                                span=_span(), name="array_length"
                            ),
                            arguments=[IdentifierExpr(span=_span(), name="a")],
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_accepts_unsized_array_parameter() -> None:
    from proyect.parser.models import CallExpr, IdentifierExpr, ReturnStmt

    program = _program(
        _func(
            "f",
            SimpleType(span=_span(), name="integer"),
            parameters=[
                Parameter(
                    span=_span(),
                    name="a",
                    type_node=ArrayType(
                        span=_span(),
                        element_type=SimpleType(span=_span(), name="integer"),
                        size=None,
                    ),
                )
            ],
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(
                                span=_span(), name="array_length"
                            ),
                            arguments=[IdentifierExpr(span=_span(), name="a")],
                        ),
                    )
                ],
            ),
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_non_integer_array_index() -> None:
    from proyect.parser.models import IndexExpr, ReturnStmt

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(), value=3, literal_type="integer"
                            ),
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=IndexExpr(
                            span=_span(),
                            collection=IdentifierExpr(span=_span(), name="a"),
                            index_expr=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("index" in error.message.lower() for error in result.errors)


def test_semantic_rejects_unsized_array_variable() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=None,
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("array" in error.message.lower() for error in result.errors)


def test_semantic_rejects_non_integer_array_size() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("size" in error.message.lower() for error in result.errors)


def test_semantic_rejects_incompatible_array_initializer_element() -> None:
    from proyect.parser.models import ArrayInitializer

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(), value=2, literal_type="integer"
                            ),
                        ),
                        initializer=ArrayInitializer(
                            span=_span(),
                            elements=[
                                LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                ),
                                LiteralExpr(
                                    span=_span(),
                                    value=True,
                                    literal_type="boolean",
                                ),
                            ],
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("array" in error.message.lower() for error in result.errors)


def test_semantic_rejects_array_initializer_overflow() -> None:
    from proyect.parser.models import ArrayInitializer

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(), value=1, literal_type="integer"
                            ),
                        ),
                        initializer=ArrayInitializer(
                            span=_span(),
                            elements=[
                                LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                ),
                                LiteralExpr(
                                    span=_span(),
                                    value=2,
                                    literal_type="integer",
                                ),
                            ],
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any("overflow" in error.message.lower() for error in result.errors)


def test_semantic_accepts_valid_global_initializer() -> None:
    from proyect.parser.models import BinaryExpr

    program = _program(
        _var(
            "x",
            SimpleType(span=_span(), name="integer"),
            initializer=BinaryExpr(
                span=_span(),
                operator="+",
                left=LiteralExpr(
                    span=_span(), value=1, literal_type="integer"
                ),
                right=LiteralExpr(
                    span=_span(), value=2, literal_type="integer"
                ),
            ),
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=IdentifierExpr(span=_span(), name="x"),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_invalid_global_initializer() -> None:
    from proyect.parser.models import BinaryExpr

    program = _program(
        _var(
            "x",
            SimpleType(span=_span(), name="integer"),
            initializer=BinaryExpr(
                span=_span(),
                operator="+",
                left=LiteralExpr(
                    span=_span(), value=True, literal_type="boolean"
                ),
                right=LiteralExpr(
                    span=_span(), value=1, literal_type="integer"
                ),
            ),
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    )
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert result.errors


def test_semantic_accepts_new_and_member_call() -> None:
    from proyect.parser.models import (
        AssignmentExpr,
        CallExpr,
        ExprStmt,
        MemberExpr,
        NewExpr,
    )

    program = _program(
        _class(
            "Sieve",
            members=[
                _func(
                    "init",
                    SimpleType(span=_span(), name="void"),
                    parameters=[
                        Parameter(
                            span=_span(),
                            name="n",
                            type_node=SimpleType(span=_span(), name="integer"),
                        )
                    ],
                ),
                _func("run", SimpleType(span=_span(), name="void")),
            ],
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="Sieve")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="s"),
                            value=NewExpr(
                                span=_span(),
                                type_name="Sieve",
                                arguments=[
                                    LiteralExpr(
                                        span=_span(),
                                        value=100,
                                        literal_type="integer",
                                    )
                                ],
                            ),
                        ),
                    ),
                    ExprStmt(
                        span=_span(),
                        expression=CallExpr(
                            span=_span(),
                            callee=MemberExpr(
                                span=_span(),
                                object_expr=IdentifierExpr(
                                    span=_span(), name="s"
                                ),
                                member="run",
                            ),
                            arguments=[],
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_missing_member() -> None:
    from proyect.parser.models import CallExpr, ExprStmt, MemberExpr

    program = _program(
        _class("S"),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="S")),
                    ExprStmt(
                        span=_span(),
                        expression=CallExpr(
                            span=_span(),
                            callee=MemberExpr(
                                span=_span(),
                                object_expr=IdentifierExpr(
                                    span=_span(), name="s"
                                ),
                                member="nope",
                            ),
                            arguments=[],
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("member" in error.message.lower() for error in result.errors)


def test_semantic_rejects_duplicate_init() -> None:
    program = _program(
        _class(
            "S",
            members=[
                _func("init", SimpleType(span=_span(), name="void")),
                _func("init", SimpleType(span=_span(), name="void")),
            ],
        ),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("init" in error.message.lower() for error in result.errors)


def test_semantic_rejects_new_with_args_without_init() -> None:
    from proyect.parser.models import AssignmentExpr, ExprStmt, NewExpr

    program = _program(
        _class("S"),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="S")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="s"),
                            value=NewExpr(
                                span=_span(),
                                type_name="S",
                                arguments=[
                                    LiteralExpr(
                                        span=_span(),
                                        value=1,
                                        literal_type="integer",
                                    )
                                ],
                            ),
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert any("init" in error.message.lower() for error in result.errors)


def test_semantic_rejects_non_void_init() -> None:
    program = _program(
        _class(
            "S",
            members=[_func("init", SimpleType(span=_span(), name="integer"))],
        ),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("init" in error.message.lower() for error in result.errors)


def test_semantic_rejects_unknown_class_type() -> None:
    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="Missing"))
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert result.errors


def test_semantic_rejects_new_of_unknown_class() -> None:
    from proyect.parser.models import ExprStmt, NewExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    ExprStmt(
                        span=_span(),
                        expression=NewExpr(
                            span=_span(),
                            type_name="Missing",
                            arguments=[],
                        ),
                    )
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert result.errors


def test_semantic_accepts_member_field_read_and_assignment() -> None:
    from proyect.parser.models import (
        AssignmentExpr,
        ExprStmt,
        MemberExpr,
        NewExpr,
    )

    program = _program(
        _class(
            "S",
            members=[_var("value", SimpleType(span=_span(), name="integer"))],
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="S")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="s"),
                            value=NewExpr(
                                span=_span(),
                                type_name="S",
                                arguments=[],
                            ),
                        ),
                    ),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=MemberExpr(
                                span=_span(),
                                object_expr=IdentifierExpr(
                                    span=_span(), name="s"
                                ),
                                member="value",
                            ),
                            value=LiteralExpr(
                                span=_span(),
                                value=1,
                                literal_type="integer",
                            ),
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=MemberExpr(
                            span=_span(),
                            object_expr=IdentifierExpr(span=_span(), name="s"),
                            member="value",
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_rejects_member_assignment_with_wrong_type() -> None:
    from proyect.parser.models import (
        AssignmentExpr,
        ExprStmt,
        MemberExpr,
        NewExpr,
    )

    program = _program(
        _class(
            "S",
            members=[_var("value", SimpleType(span=_span(), name="integer"))],
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="S")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="s"),
                            value=NewExpr(
                                span=_span(),
                                type_name="S",
                                arguments=[],
                            ),
                        ),
                    ),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=MemberExpr(
                                span=_span(),
                                object_expr=IdentifierExpr(
                                    span=_span(), name="s"
                                ),
                                member="value",
                            ),
                            value=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=LiteralExpr(
                            span=_span(), value=0, literal_type="integer"
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert result.errors


def test_semantic_accepts_new_without_init_and_no_args() -> None:
    from proyect.parser.models import AssignmentExpr, ExprStmt, NewExpr

    program = _program(
        _class(
            "S",
            members=[_var("value", SimpleType(span=_span(), name="integer"))],
        ),
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var("s", NamedType(span=_span(), name="S")),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="=",
                            target=IdentifierExpr(span=_span(), name="s"),
                            value=NewExpr(
                                span=_span(),
                                type_name="S",
                                arguments=[],
                            ),
                        ),
                    ),
                ],
            ),
        ),
    )

    result = analyze_semantic(program)

    assert not result.errors


def test_semantic_analyzes_class_method_bodies() -> None:
    program = _program(
        _class(
            "Counter",
            members=[
                _func(
                    "run",
                    SimpleType(span=_span(), name="integer"),
                    body=BlockStmt(
                        span=_span(),
                        statements=[
                            ReturnStmt(
                                span=_span(),
                                value=IdentifierExpr(
                                    span=_span(), name="missing"
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
        _func("main", SimpleType(span=_span(), name="void")),
    )

    result = analyze_semantic(program)

    assert any("missing" in error.message.lower() for error in result.errors)


def test_semantic_rejects_invalid_compound_assignment_operator() -> None:
    from proyect.parser.models import AssignmentExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="void"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "flag",
                        SimpleType(span=_span(), name="boolean"),
                        initializer=LiteralExpr(
                            span=_span(),
                            value=True,
                            literal_type="boolean",
                        ),
                    ),
                    ExprStmt(
                        span=_span(),
                        expression=AssignmentExpr(
                            span=_span(),
                            operator="+=",
                            target=IdentifierExpr(span=_span(), name="flag"),
                            value=LiteralExpr(
                                span=_span(),
                                value=True,
                                literal_type="boolean",
                            ),
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any(
        "compound" in error.message.lower() or "+=" in error.message
        for error in result.errors
    )


def test_semantic_respects_shadowing_of_array_length() -> None:
    from proyect.parser.models import ArrayInitializer, CallExpr

    program = _program(
        _func(
            "main",
            SimpleType(span=_span(), name="integer"),
            body=BlockStmt(
                span=_span(),
                statements=[
                    _var(
                        "a",
                        ArrayType(
                            span=_span(),
                            element_type=SimpleType(
                                span=_span(), name="integer"
                            ),
                            size=LiteralExpr(
                                span=_span(),
                                value=1,
                                literal_type="integer",
                            ),
                        ),
                        initializer=ArrayInitializer(
                            span=_span(),
                            elements=[
                                LiteralExpr(
                                    span=_span(),
                                    value=1,
                                    literal_type="integer",
                                )
                            ],
                        ),
                    ),
                    _var(
                        "array_length",
                        SimpleType(span=_span(), name="integer"),
                        initializer=LiteralExpr(
                            span=_span(),
                            value=42,
                            literal_type="integer",
                        ),
                    ),
                    ReturnStmt(
                        span=_span(),
                        value=CallExpr(
                            span=_span(),
                            callee=IdentifierExpr(
                                span=_span(), name="array_length"
                            ),
                            arguments=[IdentifierExpr(span=_span(), name="a")],
                        ),
                    ),
                ],
            ),
        )
    )

    result = analyze_semantic(program)

    assert any(
        "non-callable" in error.message.lower() for error in result.errors
    )


def test_main_prints_semantic_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import sys

    from proyect.main import main

    source_path = tmp_path / "semantic_error.bp"
    source_path.write_text(
        "main: function integer () = { return true; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["proyect.main", str(source_path)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Semantic Errors" in captured.out
    assert "return" in captured.out.lower()
