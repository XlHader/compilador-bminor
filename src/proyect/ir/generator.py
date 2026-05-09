from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from proyect.parser.models import (
    ArrayInitializer,
    ArrayType,
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDecl,
    ConditionalExpr,
    Expr,
    ExprStmt,
    ForStmt,
    FunctionDecl,
    FunctionType,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    MemberExpr,
    NamedType,
    NewExpr,
    Parameter,
    PrintStmt,
    Program,
    ReturnStmt,
    SimpleType,
    Stmt,
    TypeNode,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from proyect.semantic.models import (
    ArraySemanticType,
    ClassSemanticType,
    ErrorType,
    FunctionSemanticType,
    PrimitiveType,
    SemanticResult,
    SemanticType,
    Symbol,
)

from .models import (
    IRDiagnostic,
    IRInstruction,
    IRResult,
    LabelGenerator,
    RegisterGenerator,
)
from .opcodes import (
    alloc_opcode,
    load_opcode,
    param_opcode,
    print_opcode,
    store_opcode,
    type_suffix,
    var_opcode,
)


@dataclass(frozen=True, slots=True)
class VariablePlace:
    name: str
    semantic_type: object


@dataclass(frozen=True, slots=True)
class ArrayElementPlace:
    array_register: str
    index_register: str
    semantic_type: object


@dataclass(frozen=True, slots=True)
class FieldPlace:
    object_register: str
    field_name: str
    semantic_type: object


Place = VariablePlace | ArrayElementPlace | FieldPlace


def generate_ir(program: Program, semantic: SemanticResult) -> IRResult:
    if semantic.errors:
        return IRResult(
            diagnostics=[
                IRDiagnostic(
                    "IR generation requires a semantically valid program"
                )
            ]
        )
    generator = _IRGenerator(semantic)
    return generator.generate(program)


class _IRGenerator:
    def __init__(self, semantic: SemanticResult) -> None:
        self.semantic = semantic
        self.result = IRResult()
        self.registers = RegisterGenerator()
        self.labels = LabelGenerator()
        self.current_class: str | None = None
        self.current_function_returns = False
        self.storage_names: dict[int, str] = {}
        self.name_counts: dict[str, int] = {}

    def generate(self, program: Program) -> IRResult:
        for declaration in program.declarations:
            if isinstance(declaration, ClassDecl):
                self._emit_class_decl(declaration)
        for declaration in program.declarations:
            if not isinstance(declaration, ClassDecl):
                self._emit_decl(declaration, top_level=True)
        return self.result

    def _emit(self, op: str, *args: object) -> None:
        self.result.instructions.append(IRInstruction(op, tuple(args)))

    def _emit_decl(self, declaration: object, top_level: bool) -> None:
        if isinstance(declaration, VarDecl):
            self._emit_var_decl(declaration, top_level=top_level)
        elif isinstance(declaration, FunctionDecl):
            self._emit_function_decl(declaration)
        elif isinstance(declaration, ClassDecl):
            self._emit_class_decl(declaration)

    def _emit_class_decl(self, declaration: ClassDecl) -> None:
        previous = self.current_class
        self.current_class = declaration.name
        for member in declaration.members:
            if isinstance(member, FunctionDecl) and member.body is not None:
                self._emit_function_decl(member, class_name=declaration.name)
        self.current_class = previous

    def _emit_function_decl(
        self,
        declaration: FunctionDecl,
        class_name: str | None = None,
    ) -> None:
        if declaration.body is None:
            return
        name = self._function_name(declaration, class_name)
        previous_returns = self.current_function_returns
        previous_class = self.current_class
        self.current_function_returns = False
        if class_name is not None:
            self.current_class = class_name
        return_type = self._type_from_type_node(
            declaration.function_type.return_type
        )
        self._emit("LABEL", name)
        if class_name is not None:
            class_type = self._lookup_class_type(class_name)
            self._emit(param_opcode(class_type), "self")
        for parameter in declaration.function_type.parameters:
            parameter_type = self._type_from_parameter(parameter)
            parameter_name = self._storage_name_for_node(
                parameter,
                parameter.name,
            )
            self._emit(param_opcode(parameter_type), parameter_name)
        self._emit_block(declaration.body)
        if not self._block_definitely_returns(declaration.body):
            self._emit_default_return(return_type)
        self.current_function_returns = previous_returns
        self.current_class = previous_class

    def _emit_var_decl(self, declaration: VarDecl, top_level: bool) -> None:
        semantic_type = self._type_from_var_decl(declaration)
        storage_name = self._storage_name_for_node(
            declaration,
            declaration.name,
        )
        opcode = var_opcode(semantic_type)
        if not top_level:
            opcode = alloc_opcode(semantic_type)
        self._emit(opcode, storage_name)
        if isinstance(declaration.initializer, ArrayInitializer):
            value = self._emit_array_initializer(
                declaration.initializer,
                semantic_type,
            )
            self._emit(store_opcode(semantic_type), value, storage_name)
            return
        if declaration.initializer is not None:
            value = self._emit_value(declaration.initializer)
            self._emit(store_opcode(semantic_type), value, storage_name)
            return
        if isinstance(semantic_type, ArraySemanticType):
            length = self._array_decl_length(declaration.type_node)
            value = self._new_array(semantic_type.element_type, length)
            self._emit(store_opcode(semantic_type), value, storage_name)

    def _emit_block(self, block: BlockStmt) -> None:
        for statement in block.statements:
            if isinstance(statement, VarDecl):
                self._emit_var_decl(statement, top_level=False)
            elif isinstance(statement, ClassDecl | FunctionDecl):
                self._diagnose(statement, "nested declarations cannot lower")
            elif isinstance(statement, Stmt):
                self._emit_stmt(statement)
            else:
                self._diagnose(statement, "unsupported block item")

    def _emit_stmt(self, statement: Stmt) -> None:
        if isinstance(statement, BlockStmt):
            self._emit_block(statement)
        elif isinstance(statement, ExprStmt):
            self._emit_value(statement.expression)
        elif isinstance(statement, PrintStmt):
            for expression in statement.expressions:
                semantic_type = self._node_type(expression)
                value = self._emit_value(expression)
                self._emit(print_opcode(semantic_type), value)
        elif isinstance(statement, ReturnStmt):
            if statement.value is None:
                self._emit("RET")
            else:
                self._emit("RET", self._emit_value(statement.value))
            self.current_function_returns = True
        elif isinstance(statement, IfStmt):
            self._emit_if(statement)
        elif isinstance(statement, WhileStmt):
            self._emit_while(statement)
        elif isinstance(statement, ForStmt):
            self._emit_for(statement)

    def _emit_if(self, statement: IfStmt) -> None:
        then_label = self.labels.new("if_then")
        else_label = self.labels.new("if_else")
        end_label = self.labels.new("if_end")
        condition = self._emit_value(statement.condition)
        self._emit("CBRANCH", condition, then_label, else_label)
        self._emit("LABEL", then_label)
        self._emit_stmt(statement.then_branch)
        self._emit("BRANCH", end_label)
        self._emit("LABEL", else_label)
        if statement.else_branch is not None:
            self._emit_stmt(statement.else_branch)
        self._emit("BRANCH", end_label)
        self._emit("LABEL", end_label)

    def _emit_while(self, statement: WhileStmt) -> None:
        test_label = self.labels.new("while_test")
        body_label = self.labels.new("while_body")
        end_label = self.labels.new("while_end")
        self._emit("LABEL", test_label)
        condition = self._emit_value(statement.condition)
        self._emit("CBRANCH", condition, body_label, end_label)
        self._emit("LABEL", body_label)
        self._emit_stmt(statement.body)
        self._emit("BRANCH", test_label)
        self._emit("LABEL", end_label)

    def _emit_for(self, statement: ForStmt) -> None:
        if statement.initializer is not None:
            self._emit_value(statement.initializer)
        test_label = self.labels.new("for_test")
        body_label = self.labels.new("for_body")
        update_label = self.labels.new("for_update")
        end_label = self.labels.new("for_end")
        self._emit("LABEL", test_label)
        if statement.condition is None:
            self._emit("BRANCH", body_label)
        else:
            condition = self._emit_value(statement.condition)
            self._emit("CBRANCH", condition, body_label, end_label)
        self._emit("LABEL", body_label)
        self._emit_stmt(statement.body)
        self._emit("BRANCH", update_label)
        self._emit("LABEL", update_label)
        if statement.update is not None:
            self._emit_value(statement.update)
        self._emit("BRANCH", test_label)
        self._emit("LABEL", end_label)

    def _emit_value(self, expr: object) -> str:
        if isinstance(expr, LiteralExpr):
            return self._emit_literal(expr)
        if isinstance(expr, IdentifierExpr):
            symbol = self.semantic.resolved_symbols.get(id(expr))
            if symbol is not None and symbol.kind == "function":
                return symbol.name
            return self._load_place(self._emit_place(expr))
        if isinstance(expr, BinaryExpr):
            return self._emit_binary(expr)
        if isinstance(expr, UnaryExpr):
            return self._emit_unary(expr)
        if isinstance(expr, AssignmentExpr):
            return self._emit_assignment(expr)
        if isinstance(expr, CallExpr):
            return self._emit_call(expr)
        if isinstance(expr, IndexExpr):
            return self._load_place(self._emit_place(expr))
        if isinstance(expr, MemberExpr):
            symbol = self.semantic.resolved_symbols.get(id(expr))
            if symbol is not None and symbol.kind == "method":
                return self._method_name(symbol)
            return self._load_place(self._emit_place(expr))
        if isinstance(expr, NewExpr):
            return self._emit_new(expr)
        if isinstance(expr, ConditionalExpr):
            return self._emit_conditional(expr)
        if isinstance(expr, ArrayInitializer):
            return self._emit_array_initializer(expr, self._node_type(expr))
        self._diagnose(expr, f"unsupported expression {type(expr).__name__}")
        return "_"

    def _emit_literal(self, expr: LiteralExpr) -> str:
        target = self.registers.new()
        if expr.literal_type == "float":
            self._emit("MOVF", expr.value, target)
        elif expr.literal_type == "char":
            self._emit("MOVB", expr.value, target)
        elif expr.literal_type == "string":
            self._emit("MOVS", expr.value, target)
        elif expr.literal_type == "boolean":
            self._emit("MOVI", 1 if expr.value else 0, target)
        else:
            self._emit("MOVI", expr.value, target)
        return target

    def _emit_binary(self, expr: BinaryExpr) -> str:
        left = self._emit_value(expr.left)
        right = self._emit_value(expr.right)
        target = self.registers.new()
        result_type = self._node_type(expr)
        operand_type = self._node_type(expr.left)
        if expr.operator in {"<", "<=", ">", ">=", "==", "!="}:
            self._emit(
                f"CMP{type_suffix(operand_type)}",
                expr.operator,
                left,
                right,
                target,
            )
            return target
        if expr.operator in {"&&", "||"}:
            self._emit(
                "AND" if expr.operator == "&&" else "OR", left, right, target
            )
            return target
        if expr.operator == "+" and type_suffix(result_type) == "S":
            self._emit("CONCATS", left, right, target)
            return target
        opcode = self._binary_opcode(expr.operator, result_type)
        self._emit(opcode, left, right, target)
        return target

    def _emit_unary(self, expr: UnaryExpr) -> str:
        if expr.operator in {"++", "--"}:
            place = self._emit_place(expr.operand)
            previous = self._load_place(place)
            one = self._literal_register(1, self._node_type(expr))
            target = self.registers.new()
            opcode = self._binary_opcode(
                "+" if expr.operator == "++" else "-",
                self._node_type(expr),
            )
            self._emit(opcode, previous, one, target)
            self._store_place(place, target)
            return target if expr.position == "prefix" else previous
        operand = self._emit_value(expr.operand)
        semantic_type = self._node_type(expr)
        if expr.operator == "!":
            zero = self._literal_register(0, PrimitiveType("integer"))
            target = self.registers.new()
            self._emit("CMPI", "==", operand, zero, target)
            return target
        if expr.operator == "-":
            zero = self._literal_register(0, semantic_type)
            target = self.registers.new()
            self._emit(
                self._binary_opcode("-", semantic_type), zero, operand, target
            )
            return target
        return operand

    def _emit_assignment(self, expr: AssignmentExpr) -> str:
        place = self._emit_place(expr.target)
        value = self._emit_value(expr.value)
        if expr.operator == "=":
            self._store_place(place, value)
            return value
        previous = self._load_place(place)
        target = self.registers.new()
        operator = {"+=": "+", "-=": "-", "*=": "*", "/=": "/"}[expr.operator]
        self._emit(
            self._binary_opcode(operator, place.semantic_type),
            previous,
            value,
            target,
        )
        self._store_place(place, target)
        return target

    def _emit_call(self, expr: CallExpr) -> str:
        if self._is_array_length(expr):
            array = self._emit_value(expr.arguments[0])
            target = self.registers.new()
            self._emit("ALENGTH", array, target)
            return target
        name, receiver_args = self._callee_name_and_receiver(expr.callee)
        args = [*receiver_args]
        args.extend(self._emit_value(argument) for argument in expr.arguments)
        return_type = self._node_type(expr)
        if return_type == PrimitiveType("void"):
            self._emit("CALL", name, *args, "_")
            return "_"
        target = self.registers.new()
        self._emit("CALL", name, *args, target)
        return target

    def _emit_new(self, expr: NewExpr) -> str:
        target = self.registers.new()
        self._emit("NEWOBJ", expr.type_name, target)
        class_type = self._lookup_class_type(expr.type_name)
        init_symbol = class_type.members.get("init")
        if init_symbol is not None:
            args = [self._emit_value(argument) for argument in expr.arguments]
            self._emit("CALL", f"{expr.type_name}.init", target, *args, "_")
        return target

    def _emit_conditional(self, expr: ConditionalExpr) -> str:
        then_label = self.labels.new("cond_then")
        else_label = self.labels.new("cond_else")
        end_label = self.labels.new("cond_end")
        condition = self._emit_value(expr.condition)
        self._emit("CBRANCH", condition, then_label, else_label)
        self._emit("LABEL", then_label)
        then_value = self._emit_value(expr.then_expr)
        self._emit("BRANCH", end_label)
        self._emit("LABEL", else_label)
        else_value = self._emit_value(expr.else_expr)
        self._emit("BRANCH", end_label)
        self._emit("LABEL", end_label)
        target = self.registers.new()
        incoming = ((then_label, then_value), (else_label, else_value))
        self._emit("PHI", incoming, target)
        return target

    def _emit_place(self, expr: object) -> Place:
        if isinstance(expr, IdentifierExpr):
            symbol = self.semantic.resolved_symbols.get(id(expr))
            semantic_type = self._node_type(expr)
            if symbol is not None and symbol.kind == "field":
                return FieldPlace("self", symbol.name, semantic_type)
            return VariablePlace(
                self._storage_name_for_symbol(symbol, expr.name),
                semantic_type,
            )
        if isinstance(expr, IndexExpr):
            array = self._emit_value(expr.collection)
            index = self._emit_value(expr.index_expr)
            return ArrayElementPlace(array, index, self._node_type(expr))
        if isinstance(expr, MemberExpr):
            object_register = self._emit_value(expr.object_expr)
            symbol = self.semantic.resolved_symbols.get(id(expr))
            field_name = symbol.name if symbol is not None else expr.member
            return FieldPlace(
                object_register,
                field_name,
                self._node_type(expr),
            )
        self._diagnose(expr, "expression is not assignable")
        return VariablePlace("_", ErrorType())

    def _load_place(self, place: Place) -> str:
        target = self.registers.new()
        if isinstance(place, VariablePlace):
            self._emit(load_opcode(place.semantic_type), place.name, target)
        elif isinstance(place, ArrayElementPlace):
            self._emit(
                "ALOAD",
                place.array_register,
                place.index_register,
                target,
            )
        else:
            self._emit(
                "GETFIELD", place.object_register, place.field_name, target
            )
        return target

    def _store_place(self, place: Place, source: str) -> None:
        if isinstance(place, VariablePlace):
            self._emit(store_opcode(place.semantic_type), source, place.name)
        elif isinstance(place, ArrayElementPlace):
            self._emit(
                "ASTORE", source, place.array_register, place.index_register
            )
        else:
            self._emit(
                "SETFIELD", source, place.object_register, place.field_name
            )

    def _emit_array_initializer(
        self,
        initializer: ArrayInitializer,
        semantic_type: object,
    ) -> str:
        element_type = (
            semantic_type.element_type
            if isinstance(semantic_type, ArraySemanticType)
            else PrimitiveType("integer")
        )
        array = self._new_array(element_type, len(initializer.elements))
        for index, element in enumerate(initializer.elements):
            index_register = self._literal_register(
                index,
                PrimitiveType("integer"),
            )
            value = self._emit_value(element)
            self._emit("ASTORE", value, array, index_register)
        return array

    def _new_array(self, element_type: object, length: object) -> str:
        length_value = (
            self._emit_value(length)
            if isinstance(length, Expr)
            else self._literal_register(length, PrimitiveType("integer"))
        )
        target = self.registers.new()
        self._emit(
            "NEWARRAY", self._type_name(element_type), length_value, target
        )
        return target

    def _literal_register(self, value: object, semantic_type: object) -> str:
        target = self.registers.new()
        suffix = type_suffix(semantic_type)
        if suffix == "F":
            self._emit("MOVF", value, target)
        elif suffix == "B":
            self._emit("MOVB", value, target)
        elif suffix == "S":
            self._emit("MOVS", value, target)
        else:
            self._emit("MOVI", value, target)
        return target

    def _emit_default_return(self, semantic_type: object) -> None:
        if semantic_type == PrimitiveType("void"):
            self._emit("RET")
            return
        if semantic_type == PrimitiveType("float"):
            self._emit("RET", self._literal_register(0.0, semantic_type))
            return
        if semantic_type == PrimitiveType("string"):
            self._emit("RET", self._literal_register("", semantic_type))
            return
        if semantic_type == PrimitiveType("char"):
            self._emit("RET", self._literal_register("\0", semantic_type))
            return
        self._emit("RET", self._literal_register(0, PrimitiveType("integer")))

    def _callee_name_and_receiver(
        self,
        callee: object,
    ) -> tuple[str, list[str]]:
        if isinstance(callee, IdentifierExpr):
            symbol = self.semantic.resolved_symbols.get(id(callee))
            if symbol is not None and symbol.kind == "method":
                return self._method_name(symbol), ["self"]
            return (symbol.name if symbol is not None else callee.name), []
        if isinstance(callee, MemberExpr):
            symbol = self.semantic.resolved_symbols.get(id(callee))
            object_register = self._emit_value(callee.object_expr)
            name = (
                self._method_name(symbol)
                if symbol is not None
                else callee.member
            )
            return name, [object_register]
        value = self._emit_value(callee)
        return value, []

    def _is_array_length(self, expr: CallExpr) -> bool:
        if not isinstance(expr.callee, IdentifierExpr):
            return False
        symbol = self.semantic.resolved_symbols.get(id(expr.callee))
        return symbol is not None and symbol.name == "array_length"

    def _binary_opcode(self, operator: str, semantic_type: object) -> str:
        suffix = type_suffix(semantic_type)
        if suffix == "S":
            if operator == "+":
                return "CONCATS"
            return "CMPS"
        roots = {
            "+": "ADD",
            "-": "SUB",
            "*": "MUL",
            "/": "DIV",
            "%": "MOD",
            "^": "POW",
        }
        root = roots.get(operator, "ADD")
        return f"{root}{suffix}"

    def _function_name(
        self,
        declaration: FunctionDecl,
        class_name: str | None,
    ) -> str:
        if class_name is None:
            return declaration.name
        return f"{class_name}.{declaration.name}"

    def _method_name(self, symbol: Symbol | None) -> str:
        if symbol is None:
            return "_"
        return f"{symbol.scope_name}.{symbol.name}"

    def _storage_name_for_symbol(
        self,
        symbol: Symbol | None,
        fallback: str,
    ) -> str:
        if symbol is None or symbol.node is None:
            return fallback
        return self._storage_name_for_node(symbol.node, fallback)

    def _storage_name_for_node(self, node: object, base: str) -> str:
        node_id = id(node)
        stored = self.storage_names.get(node_id)
        if stored is not None:
            return stored
        count = self.name_counts.get(base, 0) + 1
        self.name_counts[base] = count
        name = base if count == 1 else f"{base}${count}"
        self.storage_names[node_id] = name
        return name

    def _node_type(self, node: object) -> SemanticType:
        return self.semantic.node_types.get(id(node), ErrorType())

    def _type_from_parameter(self, parameter: Parameter) -> SemanticType:
        return self._type_from_type_node(parameter.type_node)

    def _type_from_var_decl(self, declaration: VarDecl) -> SemanticType:
        if isinstance(declaration.type_node, SimpleType):
            if declaration.type_node.name == "auto":
                if declaration.initializer is not None:
                    return self._node_type(declaration.initializer)
            return PrimitiveType(declaration.type_node.name)
        return self._type_from_type_node(declaration.type_node)

    def _type_from_type_node(self, type_node: TypeNode) -> SemanticType:
        if isinstance(type_node, SimpleType):
            return PrimitiveType(type_node.name)
        if isinstance(type_node, NamedType):
            if self.semantic.global_scope is not None:
                found = self.semantic.global_scope.lookup_type(type_node.name)
                if found is not None:
                    return cast(SemanticType, found)
            return ClassSemanticType(type_node.name)
        if isinstance(type_node, ArrayType):
            return ArraySemanticType(
                self._type_from_type_node(type_node.element_type),
                self._literal_size(type_node.size),
            )
        if isinstance(type_node, FunctionType):
            return FunctionSemanticType(
                self._type_from_type_node(type_node.return_type),
                tuple(
                    self._type_from_type_node(parameter.type_node)
                    for parameter in type_node.parameters
                ),
            )
        return ErrorType()

    def _lookup_class_type(self, name: str) -> ClassSemanticType:
        if self.semantic.global_scope is not None:
            found = self.semantic.global_scope.lookup_type(name)
            if isinstance(found, ClassSemanticType):
                return found
        return ClassSemanticType(name)

    def _array_decl_length(self, type_node: TypeNode) -> object:
        if isinstance(type_node, ArrayType) and type_node.size is not None:
            return type_node.size
        return 0

    def _literal_size(self, expr: object) -> int | None:
        if isinstance(expr, LiteralExpr) and isinstance(expr.value, int):
            return expr.value
        return None

    def _type_name(self, semantic_type: object) -> str:
        if isinstance(semantic_type, PrimitiveType):
            return semantic_type.name
        if isinstance(semantic_type, ArraySemanticType):
            return f"array[{self._type_name(semantic_type.element_type)}]"
        if isinstance(semantic_type, ClassSemanticType):
            return semantic_type.name
        return str(semantic_type)

    def _diagnose(self, node: object, message: str) -> None:
        span = getattr(node, "span", None)
        self.result.diagnostics.append(
            IRDiagnostic(
                message=message,
                line=getattr(span, "line", 0),
                column=getattr(span, "column", 0),
                context=type(node).__name__,
            )
        )

    def _block_definitely_returns(self, block: BlockStmt) -> bool:
        return any(
            isinstance(statement, Stmt)
            and self._stmt_definitely_returns(statement)
            for statement in block.statements
        )

    def _stmt_definitely_returns(self, statement: Stmt) -> bool:
        if isinstance(statement, ReturnStmt):
            return True
        if isinstance(statement, BlockStmt):
            return self._block_definitely_returns(statement)
        if isinstance(statement, IfStmt):
            return (
                statement.else_branch is not None
                and self._stmt_definitely_returns(statement.then_branch)
                and self._stmt_definitely_returns(statement.else_branch)
            )
        return False


__all__ = ["generate_ir"]
