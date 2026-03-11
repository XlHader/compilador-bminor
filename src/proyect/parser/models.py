from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass

from ..lexer.models import LexError


@dataclass(frozen=True, slots=True)
class SourceSpan:
    line: int
    column: int
    index: int
    end: int


@dataclass(frozen=True, slots=True)
class Node:
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class TypeNode(Node):
    pass


@dataclass(frozen=True, slots=True)
class Expr(Node):
    pass


@dataclass(frozen=True, slots=True)
class Stmt(Node):
    pass


@dataclass(frozen=True, slots=True)
class Decl(Node):
    pass


@dataclass(frozen=True, slots=True)
class SimpleType(TypeNode):
    name: str


@dataclass(frozen=True, slots=True)
class NamedType(TypeNode):
    name: str


@dataclass(frozen=True, slots=True)
class ArrayType(TypeNode):
    element_type: TypeNode
    size: Expr | None


@dataclass(frozen=True, slots=True)
class Parameter(Node):
    name: str
    type_node: TypeNode


@dataclass(frozen=True, slots=True)
class FunctionType(TypeNode):
    return_type: TypeNode
    parameters: list[Parameter]


@dataclass(frozen=True, slots=True)
class Program(Node):
    declarations: list[Decl]


@dataclass(frozen=True, slots=True)
class BlockStmt(Stmt):
    statements: list[Stmt | Decl]


@dataclass(frozen=True, slots=True)
class VarDecl(Decl, Stmt):
    name: str
    type_node: TypeNode
    initializer: Expr | ArrayInitializer | BlockStmt | None


@dataclass(frozen=True, slots=True)
class FunctionDecl(Decl):
    name: str
    function_type: FunctionType
    body: BlockStmt | None


@dataclass(frozen=True, slots=True)
class ClassDecl(Decl):
    name: str
    members: list[Decl]


@dataclass(frozen=True, slots=True)
class ExprStmt(Stmt):
    expression: Expr


@dataclass(frozen=True, slots=True)
class PrintStmt(Stmt):
    expressions: list[Expr]


@dataclass(frozen=True, slots=True)
class ReturnStmt(Stmt):
    value: Expr | None


@dataclass(frozen=True, slots=True)
class IfStmt(Stmt):
    condition: Expr | None
    then_branch: Stmt
    else_branch: Stmt | None


@dataclass(frozen=True, slots=True)
class WhileStmt(Stmt):
    condition: Expr | None
    body: Stmt


@dataclass(frozen=True, slots=True)
class ForStmt(Stmt):
    initializer: Expr | None
    condition: Expr | None
    update: Expr | None
    body: Stmt


@dataclass(frozen=True, slots=True)
class IdentifierExpr(Expr):
    name: str


@dataclass(frozen=True, slots=True)
class LiteralExpr(Expr):
    value: object
    literal_type: str


@dataclass(frozen=True, slots=True)
class BinaryExpr(Expr):
    operator: str
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class UnaryExpr(Expr):
    operator: str
    operand: Expr
    position: str


@dataclass(frozen=True, slots=True)
class AssignmentExpr(Expr):
    operator: str
    target: Expr
    value: Expr


@dataclass(frozen=True, slots=True)
class CallExpr(Expr):
    callee: Expr
    arguments: list[Expr]


@dataclass(frozen=True, slots=True)
class IndexExpr(Expr):
    collection: Expr
    index_expr: Expr


@dataclass(frozen=True, slots=True)
class MemberExpr(Expr):
    object_expr: Expr
    member: str


@dataclass(frozen=True, slots=True)
class NewExpr(Expr):
    type_name: str
    arguments: list[Expr]


@dataclass(frozen=True, slots=True)
class ConditionalExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr


@dataclass(frozen=True, slots=True)
class ArrayInitializer(Node):
    elements: list[Expr]


@dataclass(frozen=True, slots=True)
class ParseError:
    message: str
    line: int | str
    column: int | str
    index: int | None
    lexeme: str
    token_type: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    ast: Program | None
    lex_errors: list[LexError]
    parse_errors: list[ParseError]


def ast_to_dict(node: object) -> object:
    if isinstance(node, list):
        return [ast_to_dict(item) for item in node]
    if isinstance(node, tuple):
        return [ast_to_dict(item) for item in node]
    if is_dataclass(node):
        return {
            field.name: ast_to_dict(getattr(node, field.name))
            for field in fields(node)
        }
    return node


__all__ = [
    "ArrayInitializer",
    "ArrayType",
    "AssignmentExpr",
    "BinaryExpr",
    "BlockStmt",
    "CallExpr",
    "ClassDecl",
    "ConditionalExpr",
    "Decl",
    "Expr",
    "ExprStmt",
    "ForStmt",
    "FunctionDecl",
    "FunctionType",
    "IdentifierExpr",
    "IfStmt",
    "IndexExpr",
    "LiteralExpr",
    "MemberExpr",
    "NamedType",
    "NewExpr",
    "Node",
    "Parameter",
    "ParseError",
    "ParseResult",
    "PrintStmt",
    "Program",
    "ReturnStmt",
    "SimpleType",
    "SourceSpan",
    "Stmt",
    "TypeNode",
    "UnaryExpr",
    "VarDecl",
    "WhileStmt",
    "ast_to_dict",
]
