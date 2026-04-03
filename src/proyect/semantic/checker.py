from __future__ import annotations

from ..parser.models import (
    ArrayInitializer,
    ArrayType,
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDecl,
    ConditionalExpr,
    Decl,
    ExprStmt,
    ForStmt,
    FunctionDecl,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    MemberExpr,
    NewExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from .models import (
    ArraySemanticType,
    ClassSemanticType,
    ErrorType,
    FunctionSemanticType,
    PrimitiveType,
    SemanticError,
    SemanticResult,
    SemanticType,
    Symbol,
)
from .symtab import SemanticScope
from .typesys import (
    are_assignment_compatible,
    are_call_argument_compatible,
    is_binary_operator_applicable,
    is_printable_type,
    is_unary_operator_applicable,
    resolve_type_node,
)


def analyze_semantic(program: Program) -> SemanticResult:
    global_scope = SemanticScope("global")
    _bootstrap_builtins(global_scope)
    result = SemanticResult(global_scope=global_scope)
    _analyze_program(program, global_scope, result)
    _validate_main(global_scope, result)
    return result


def _bootstrap_builtins(scope: SemanticScope) -> None:
    for name in ("integer", "float", "boolean", "char", "string", "void"):
        scope.define_type(name, PrimitiveType(name))
    scope.define_value(
        Symbol(
            name="array_length",
            kind="function",
            type=FunctionSemanticType(PrimitiveType("integer"), ()),
            node=None,
            scope_name=scope.name,
        )
    )


def _analyze_program(
    program: Program, scope: SemanticScope, result: SemanticResult
) -> None:
    for declaration in program.declarations:
        if isinstance(declaration, ClassDecl):
            _register_top_level(declaration, scope, result)
    for declaration in program.declarations:
        if isinstance(declaration, ClassDecl):
            _analyze_class_decl(declaration, scope, result, top_level=True)
    for declaration in program.declarations:
        if isinstance(declaration, FunctionDecl):
            _register_top_level(declaration, scope, result)
    for declaration in program.declarations:
        _analyze_decl(declaration, scope, result, top_level=True)


def _register_top_level(
    declaration: Decl, scope: SemanticScope, result: SemanticResult
) -> None:
    if isinstance(declaration, VarDecl):
        semantic_type = resolve_type_node(declaration.type_node, scope)
        if semantic_type is not None:
            if declaration.name not in scope.value_symbols:
                scope.define_value(
                    Symbol(
                        declaration.name,
                        "variable",
                        semantic_type,
                        declaration,
                        scope.name,
                    )
                )
        return
    if isinstance(declaration, FunctionDecl):
        function_type = resolve_type_node(declaration.function_type, scope)
        if function_type is None:
            if declaration.body is None:
                _error(
                    result,
                    declaration,
                    f"invalid function type for '{declaration.name}'",
                )
            if declaration.name not in scope.value_symbols:
                scope.define_value(
                    Symbol(
                        declaration.name,
                        "function",
                        ErrorType(),
                        declaration,
                        scope.name,
                    )
                )
            else:
                _error(
                    result,
                    declaration,
                    f"redeclaration of '{declaration.name}'",
                )
            return
        existing = scope.lookup_value(declaration.name)
        if existing is None:
            scope.define_value(
                Symbol(
                    declaration.name,
                    "function",
                    function_type,
                    declaration,
                    scope.name,
                )
            )
        elif isinstance(existing.type, ErrorType):
            _error(
                result, declaration, f"redeclaration of '{declaration.name}'"
            )
        elif existing.type != function_type:
            _error(result, declaration, "prototype/definition mismatch")
        else:
            existing_decl = existing.node
            if isinstance(existing_decl, FunctionDecl):
                existing_has_body = existing_decl.body is not None
                current_has_body = declaration.body is not None
                if not existing_has_body and current_has_body:
                    scope.value_symbols[declaration.name] = Symbol(
                        declaration.name,
                        "function",
                        function_type,
                        declaration,
                        scope.name,
                    )
                else:
                    _error(
                        result,
                        declaration,
                        f"redeclaration of '{declaration.name}'",
                    )
        return
    if isinstance(declaration, ClassDecl):
        class_type = ClassSemanticType(declaration.name)
        try:
            scope.define_type(declaration.name, class_type)
        except ValueError:
            _error(
                result, declaration, f"redeclaration of '{declaration.name}'"
            )


def _analyze_decl(
    declaration: Decl,
    scope: SemanticScope,
    result: SemanticResult,
    top_level: bool = False,
) -> None:
    if isinstance(declaration, VarDecl):
        _analyze_var_decl(declaration, scope, result)
    elif isinstance(declaration, FunctionDecl):
        _analyze_function_decl(declaration, scope, result, top_level=top_level)
    elif isinstance(declaration, ClassDecl):
        if not top_level:
            _error(
                result, declaration, "nested class definition is not allowed"
            )


def _analyze_var_decl(
    declaration: VarDecl, scope: SemanticScope, result: SemanticResult
) -> None:
    semantic_type = resolve_type_node(declaration.type_node, scope)
    if semantic_type is None:
        _error(
            result,
            declaration,
            f"undeclared type for variable '{declaration.name}'",
        )
        return
    if isinstance(declaration.type_node, ArrayType):
        semantic_type = _validate_array_decl_type(
            declaration,
            declaration.type_node,
            semantic_type,
            scope,
            result,
        )
    if semantic_type == PrimitiveType("auto"):
        if declaration.initializer is None:
            _error(
                result,
                declaration,
                f"auto variable '{declaration.name}' requires initializer",
            )
            semantic_type = ErrorType()
        else:
            inferred_type = _expr_type(declaration.initializer, scope, result)
            if inferred_type in (PrimitiveType("void"), ErrorType()):
                _error(
                    result,
                    declaration,
                    (
                        f"auto variable '{declaration.name}' "
                        "has invalid initializer"
                    ),
                )
                semantic_type = ErrorType()
            else:
                semantic_type = inferred_type
    elif isinstance(declaration.initializer, ArrayInitializer):
        _validate_array_initializer(
            declaration.initializer,
            semantic_type,
            result,
            scope,
        )
    elif declaration.initializer is not None:
        initializer_type = _expr_type(declaration.initializer, scope, result)
        if not are_assignment_compatible(semantic_type, initializer_type):
            _error(
                result,
                declaration,
                (
                    f"cannot initialize '{declaration.name}' "
                    f"of type {semantic_type} with {initializer_type}"
                ),
            )
    try:
        scope.define_value(
            Symbol(
                declaration.name,
                "variable",
                semantic_type,
                declaration,
                scope.name,
            )
        )
    except ValueError:
        _error(result, declaration, f"redeclaration of '{declaration.name}'")


def _validate_array_decl_type(
    declaration: VarDecl,
    type_node: ArrayType,
    semantic_type: SemanticType,
    scope: SemanticScope,
    result: SemanticResult,
) -> SemanticType:
    if not isinstance(semantic_type, ArraySemanticType):
        return semantic_type
    if type_node.size is None:
        _error(result, declaration, "array variable requires explicit size")
        return ArraySemanticType(semantic_type.element_type, None)
    size_type = _expr_type(type_node.size, scope, result)
    if size_type != PrimitiveType("integer"):
        _error(result, declaration, "array size must be integer")
        return ArraySemanticType(semantic_type.element_type, None)
    size_value = None
    if (
        isinstance(type_node.size, LiteralExpr)
        and type_node.size.literal_type == "integer"
        and isinstance(type_node.size.value, int)
    ):
        size_value = type_node.size.value
    return ArraySemanticType(semantic_type.element_type, size_value)


def _validate_array_initializer(
    initializer: ArrayInitializer,
    semantic_type: SemanticType,
    result: SemanticResult,
    scope: SemanticScope,
) -> None:
    if not isinstance(semantic_type, ArraySemanticType):
        _error(result, initializer, "array initializer requires array type")
        return
    for element in initializer.elements:
        element_type = _expr_type(element, scope, result)
        if not are_assignment_compatible(
            semantic_type.element_type, element_type
        ):
            _error(
                result,
                initializer,
                "array initializer has incompatible element",
            )
    if (
        semantic_type.size is not None
        and len(initializer.elements) > semantic_type.size
    ):
        _error(result, initializer, "array initializer overflow")


def _analyze_class_decl(
    declaration: ClassDecl,
    scope: SemanticScope,
    result: SemanticResult,
    top_level: bool,
) -> None:
    if not top_level:
        return
    members: dict[str, Symbol] = {}
    for member in declaration.members:
        if isinstance(member, VarDecl):
            member_type = resolve_type_node(member.type_node, scope)
            if member_type is None:
                _error(
                    result,
                    member,
                    f"undeclared type for member '{member.name}'",
                )
                continue
            if isinstance(member.type_node, ArrayType):
                member_type = _validate_array_decl_type(
                    member,
                    member.type_node,
                    member_type,
                    scope,
                    result,
                )
            if member.name in members:
                _error(result, member, f"redeclaration of '{member.name}'")
                continue
            members[member.name] = Symbol(
                member.name,
                "field",
                member_type,
                member,
                declaration.name,
            )
        elif isinstance(member, FunctionDecl):
            member_type = resolve_type_node(member.function_type, scope)
            if member_type is None:
                _error(
                    result,
                    member,
                    f"invalid function type for '{member.name}'",
                )
                continue
            if member.name in members:
                if member.name == "init":
                    _error(result, member, "duplicate init in class")
                else:
                    _error(result, member, f"redeclaration of '{member.name}'")
                continue
            if (
                member.name == "init"
                and isinstance(member_type, FunctionSemanticType)
                and member_type.return_type != PrimitiveType("void")
            ):
                _error(result, member, "init must return void")
            members[member.name] = Symbol(
                member.name,
                "method",
                member_type,
                member,
                declaration.name,
            )
    scope.type_symbols[declaration.name] = ClassSemanticType(
        declaration.name,
        members,
    )
    class_scope = SemanticScope(f"class:{declaration.name}", parent=scope)
    for member_symbol in members.values():
        class_scope.define_value(member_symbol)
    for member in declaration.members:
        if isinstance(member, FunctionDecl) and member.name in members:
            _analyze_callable_body(member, class_scope, result)


def _analyze_function_decl(
    declaration: FunctionDecl,
    scope: SemanticScope,
    result: SemanticResult,
    top_level: bool,
) -> None:
    if not top_level:
        _error(
            result, declaration, "nested function definition is not allowed"
        )
        return
    _analyze_callable_body(declaration, scope, result)


def _analyze_callable_body(
    declaration: FunctionDecl,
    parent_scope: SemanticScope,
    result: SemanticResult,
) -> None:
    function_type = resolve_type_node(declaration.function_type, parent_scope)
    if function_type is None:
        _error(
            result,
            declaration,
            f"invalid function type for '{declaration.name}'",
        )
    function_scope = SemanticScope(
        f"function:{declaration.name}", parent=parent_scope
    )
    for parameter in declaration.function_type.parameters:
        parameter_type = resolve_type_node(parameter.type_node, parent_scope)
        if parameter_type is None:
            _error(
                result,
                parameter,
                f"undeclared parameter type '{parameter.type_node}'",
            )
            continue
        try:
            function_scope.define_value(
                Symbol(
                    parameter.name,
                    "parameter",
                    parameter_type,
                    parameter,
                    function_scope.name,
                )
            )
        except ValueError:
            _error(result, parameter, f"redeclaration of '{parameter.name}'")
    if declaration.body is None:
        return
    return_type = (
        function_type.return_type
        if isinstance(function_type, FunctionSemanticType)
        else ErrorType()
    )
    _analyze_block(
        declaration.body,
        function_scope,
        result,
        fresh_scope=False,
        current_return_type=return_type,
    )
    if return_type not in (PrimitiveType("void"), ErrorType()):
        if not _stmt_contains_return(declaration.body):
            _error(
                result,
                declaration,
                f"function '{declaration.name}' is missing return",
            )


def _analyze_block(
    block: BlockStmt,
    scope: SemanticScope,
    result: SemanticResult,
    fresh_scope: bool = True,
    current_return_type: SemanticType | None = None,
) -> None:
    block_scope = (
        SemanticScope("block", parent=scope) if fresh_scope else scope
    )
    for statement in block.statements:
        if isinstance(statement, VarDecl):
            _analyze_var_decl(statement, block_scope, result)
        elif isinstance(statement, BlockStmt):
            _analyze_block(
                statement,
                block_scope,
                result,
                current_return_type=current_return_type,
            )
        elif isinstance(statement, FunctionDecl):
            _error(
                result, statement, "nested function definition is not allowed"
            )
        elif isinstance(statement, ClassDecl):
            _error(result, statement, "nested class definition is not allowed")
        elif isinstance(statement, ExprStmt):
            _analyze_expr(statement.expression, block_scope, result)
        elif isinstance(statement, PrintStmt):
            for expression in statement.expressions:
                expr_type = _expr_type(expression, block_scope, result)
                if not is_printable_type(expr_type):
                    _error(
                        result,
                        statement,
                        f"cannot print value of type {expr_type}",
                    )
        elif isinstance(statement, ReturnStmt):
            _analyze_return_stmt(
                statement,
                block_scope,
                result,
                current_return_type,
            )
        elif isinstance(statement, IfStmt):
            _analyze_if_stmt(
                statement,
                block_scope,
                result,
                current_return_type,
            )
        elif isinstance(statement, WhileStmt):
            _analyze_while_stmt(
                statement,
                block_scope,
                result,
                current_return_type,
            )
        elif isinstance(statement, ForStmt):
            _analyze_for_stmt(
                statement,
                block_scope,
                result,
                current_return_type,
            )


def _analyze_if_stmt(
    statement: IfStmt,
    scope: SemanticScope,
    result: SemanticResult,
    current_return_type: SemanticType | None,
) -> None:
    if statement.condition is None:
        _error(result, statement, "if condition is required")
    else:
        condition_type = _expr_type(statement.condition, scope, result)
        if condition_type != PrimitiveType("boolean"):
            _error(result, statement, "if condition must be boolean")
    _analyze_stmt_branch(
        statement.then_branch, scope, result, current_return_type
    )
    if statement.else_branch is not None:
        _analyze_stmt_branch(
            statement.else_branch,
            scope,
            result,
            current_return_type,
        )


def _analyze_while_stmt(
    statement: WhileStmt,
    scope: SemanticScope,
    result: SemanticResult,
    current_return_type: SemanticType | None,
) -> None:
    if statement.condition is None:
        _error(result, statement, "while condition is required")
    else:
        condition_type = _expr_type(statement.condition, scope, result)
        if condition_type != PrimitiveType("boolean"):
            _error(result, statement, "while condition must be boolean")
    _analyze_stmt_branch(statement.body, scope, result, current_return_type)


def _analyze_for_stmt(
    statement: ForStmt,
    scope: SemanticScope,
    result: SemanticResult,
    current_return_type: SemanticType | None,
) -> None:
    if statement.initializer is not None:
        _expr_type(statement.initializer, scope, result)
    if statement.condition is not None:
        condition_type = _expr_type(statement.condition, scope, result)
        if condition_type != PrimitiveType("boolean"):
            _error(result, statement, "for condition must be boolean")
    if statement.update is not None:
        _expr_type(statement.update, scope, result)
    _analyze_stmt_branch(statement.body, scope, result, current_return_type)


def _analyze_return_stmt(
    statement: ReturnStmt,
    scope: SemanticScope,
    result: SemanticResult,
    current_return_type: SemanticType | None,
) -> None:
    if current_return_type is None:
        return
    if current_return_type == PrimitiveType("void"):
        if statement.value is not None:
            _error(result, statement, "void function cannot return a value")
        return
    if statement.value is None:
        _error(result, statement, "non-void function must return a value")
        return
    value_type = _expr_type(statement.value, scope, result)
    if not are_assignment_compatible(current_return_type, value_type):
        _error(
            result,
            statement,
            f"return type {value_type} does not match {current_return_type}",
        )


def _analyze_stmt_branch(
    statement,
    scope: SemanticScope,
    result: SemanticResult,
    current_return_type: SemanticType | None,
) -> None:
    if isinstance(statement, BlockStmt):
        _analyze_block(
            statement,
            scope,
            result,
            current_return_type=current_return_type,
        )
    else:
        _analyze_block(
            BlockStmt(span=statement.span, statements=[statement]),
            scope,
            result,
            current_return_type=current_return_type,
        )


def _stmt_contains_return(statement) -> bool:
    if isinstance(statement, ReturnStmt):
        return True
    if isinstance(statement, BlockStmt):
        return any(
            _stmt_contains_return(child) for child in statement.statements
        )
    if isinstance(statement, IfStmt):
        return _stmt_contains_return(statement.then_branch) or (
            statement.else_branch is not None
            and _stmt_contains_return(statement.else_branch)
        )
    if isinstance(statement, WhileStmt):
        return _stmt_contains_return(statement.body)
    if isinstance(statement, ForStmt):
        return _stmt_contains_return(statement.body)
    return False


def _analyze_expr(expr, scope: SemanticScope, result: SemanticResult) -> None:
    _expr_type(expr, scope, result)


def _expr_type(
    expr, scope: SemanticScope, result: SemanticResult
) -> SemanticType:
    if isinstance(expr, IdentifierExpr):
        found = scope.lookup_value(expr.name)
        if found is None:
            _error(result, expr, f"undeclared identifier '{expr.name}'")
            return ErrorType()
        result.resolved_symbols[id(expr)] = found
        result.node_types[id(expr)] = found.type
        return found.type
    elif isinstance(expr, BinaryExpr):
        left_type = _expr_type(expr.left, scope, result)
        right_type = _expr_type(expr.right, scope, result)
        binary_type = is_binary_operator_applicable(
            left_type, expr.operator, right_type
        )
        if binary_type is None:
            _error(result, expr, f"invalid binary operator '{expr.operator}'")
            return ErrorType()
        result.node_types[id(expr)] = binary_type
        return binary_type
    elif isinstance(expr, UnaryExpr):
        operand_type = _expr_type(expr.operand, scope, result)
        if expr.operator in {"++", "--"}:
            if not isinstance(
                expr.operand, (IdentifierExpr, IndexExpr, MemberExpr)
            ):
                _error(
                    result, expr, f"operator '{expr.operator}' requires lvalue"
                )
                return ErrorType()
            if operand_type not in (
                PrimitiveType("integer"),
                PrimitiveType("float"),
            ):
                _error(
                    result,
                    expr,
                    f"operator '{expr.operator}' requires numeric operand",
                )
                return ErrorType()
            result.node_types[id(expr)] = operand_type
            return operand_type
        unary_type = is_unary_operator_applicable(expr.operator, operand_type)
        if unary_type is None:
            _error(result, expr, f"invalid unary operator '{expr.operator}'")
            return ErrorType()
        result.node_types[id(expr)] = unary_type
        return unary_type
    elif isinstance(expr, AssignmentExpr):
        if not isinstance(
            expr.target, (IdentifierExpr, IndexExpr, MemberExpr)
        ):
            _error(result, expr, "assignment target must be lvalue")
            return ErrorType()
        target_type = _expr_type(expr.target, scope, result)
        value_type = _expr_type(expr.value, scope, result)
        if expr.operator != "=":
            compound_ops = {
                "+=": "+",
                "-=": "-",
                "*=": "*",
                "/=": "/",
            }
            binary_operator = compound_ops.get(expr.operator)
            compound_result = (
                is_binary_operator_applicable(
                    target_type,
                    binary_operator,
                    value_type,
                )
                if binary_operator is not None
                else None
            )
            if compound_result is None or not are_assignment_compatible(
                target_type, compound_result
            ):
                _error(
                    result,
                    expr,
                    f"invalid compound assignment operator '{expr.operator}'",
                )
                return ErrorType()
        if not are_assignment_compatible(target_type, value_type):
            _error(
                result,
                expr,
                f"cannot assign value of type {value_type} to {target_type}",
            )
            return ErrorType()
        result.node_types[id(expr)] = target_type
        return target_type
    elif isinstance(expr, CallExpr):
        callee_type = _expr_type(expr.callee, scope, result)
        argument_types = [
            _expr_type(argument, scope, result) for argument in expr.arguments
        ]
        callee_symbol = result.resolved_symbols.get(id(expr.callee))
        if (
            isinstance(expr.callee, IdentifierExpr)
            and isinstance(callee_symbol, Symbol)
            and callee_symbol.name == "array_length"
            and callee_symbol.node is None
        ):
            if len(argument_types) != 1:
                _error(result, expr, "array_length expects one argument")
                return ErrorType()
            if not isinstance(argument_types[0], ArraySemanticType):
                _error(result, expr, "array_length expects array argument")
                return ErrorType()
            result.node_types[id(expr)] = PrimitiveType("integer")
            return PrimitiveType("integer")
        if isinstance(callee_type, FunctionSemanticType):
            if len(argument_types) != len(callee_type.parameters):
                _error(
                    result,
                    expr,
                    "call arity does not match function signature",
                )
                return ErrorType()
            for expected, actual in zip(
                callee_type.parameters, argument_types, strict=False
            ):
                if not are_call_argument_compatible(expected, actual):
                    _error(result, expr, "call argument type does not match")
                    return ErrorType()
            result.node_types[id(expr)] = callee_type.return_type
            return callee_type.return_type
        _error(result, expr, "cannot call non-callable expression")
        return ErrorType()
    elif isinstance(expr, IndexExpr):
        collection_type = _expr_type(expr.collection, scope, result)
        index_type = _expr_type(expr.index_expr, scope, result)
        if index_type != PrimitiveType("integer"):
            _error(result, expr, "array index must be integer")
            return ErrorType()
        if not isinstance(collection_type, ArraySemanticType):
            _error(result, expr, "cannot index non-array value")
            return ErrorType()
        result.node_types[id(expr)] = collection_type.element_type
        return collection_type.element_type
    elif isinstance(expr, MemberExpr):
        object_type = _expr_type(expr.object_expr, scope, result)
        if not isinstance(object_type, ClassSemanticType):
            _error(result, expr, "member access requires class value")
            return ErrorType()
        member_symbol = object_type.members.get(expr.member)
        if member_symbol is None:
            _error(result, expr, f"missing member '{expr.member}'")
            return ErrorType()
        result.resolved_symbols[id(expr)] = member_symbol
        result.node_types[id(expr)] = member_symbol.type
        return member_symbol.type
    elif isinstance(expr, ConditionalExpr):
        condition_type = _expr_type(expr.condition, scope, result)
        then_type = _expr_type(expr.then_expr, scope, result)
        else_type = _expr_type(expr.else_expr, scope, result)
        if condition_type != PrimitiveType("boolean"):
            _error(
                result,
                expr,
                "conditional expression requires boolean condition",
            )
            return ErrorType()
        if then_type != else_type:
            _error(
                result, expr, "conditional branches must have the same type"
            )
            return ErrorType()
        result.node_types[id(expr)] = then_type
        return then_type
    elif isinstance(expr, NewExpr):
        class_type = scope.lookup_type(expr.type_name)
        argument_types = [
            _expr_type(argument, scope, result) for argument in expr.arguments
        ]
        if not isinstance(class_type, ClassSemanticType):
            _error(result, expr, f"unknown class '{expr.type_name}'")
            return ErrorType()
        init_symbol = class_type.members.get("init")
        if init_symbol is None:
            if argument_types:
                _error(result, expr, "constructor arguments require init")
                return ErrorType()
            result.node_types[id(expr)] = class_type
            return class_type
        if not isinstance(init_symbol.type, FunctionSemanticType):
            _error(result, expr, "init must be callable")
            return ErrorType()
        if len(argument_types) != len(init_symbol.type.parameters):
            _error(result, expr, "init arity does not match")
            return ErrorType()
        for expected, actual in zip(
            init_symbol.type.parameters, argument_types, strict=False
        ):
            if not are_call_argument_compatible(expected, actual):
                _error(result, expr, "init argument type does not match")
                return ErrorType()
        result.node_types[id(expr)] = class_type
        return class_type
    elif isinstance(expr, ArrayInitializer):
        for element in expr.elements:
            _expr_type(element, scope, result)
        return ErrorType()
    elif isinstance(expr, LiteralExpr):
        literal_type = PrimitiveType(expr.literal_type)
        result.node_types[id(expr)] = literal_type
        return literal_type
    return ErrorType()


def _validate_main(scope: SemanticScope, result: SemanticResult) -> None:
    main_symbol = scope.lookup_value("main")
    if main_symbol is None:
        _error(result, None, "main function is required")
        return
    if isinstance(main_symbol.type, ErrorType):
        return
    if not isinstance(main_symbol.type, FunctionSemanticType):
        _error(result, None, "main function is required")
        return
    if main_symbol.type.return_type not in (
        PrimitiveType("integer"),
        PrimitiveType("void"),
    ):
        _error(result, None, "main return type must be integer or void")
        return
    if (
        isinstance(main_symbol.node, FunctionDecl)
        and main_symbol.node.body is None
    ):
        _error(result, None, "main must have a body")


def _error(result: SemanticResult, node, message: str) -> None:
    span = getattr(node, "span", None)
    result.errors.append(
        SemanticError(
            message,
            getattr(span, "line", 0),
            getattr(span, "column", 0),
            getattr(span, "index", None),
            type(node).__name__ if node is not None else "program",
        )
    )
