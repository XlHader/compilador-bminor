from __future__ import annotations

from dataclasses import fields

from rich.text import Text
from rich.tree import Tree

from ..parser.models import (
    ArrayInitializer,
    ArrayType,
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDecl,
    ConditionalExpr,
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
    Node,
    Parameter,
    PrintStmt,
    Program,
    ReturnStmt,
    SimpleType,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)

NODE_STYLES: dict[type[Node], str] = {
    Program: "bold white",
    FunctionDecl: "bold blue",
    VarDecl: "bold blue",
    ClassDecl: "bold blue",
    FunctionType: "cyan",
    SimpleType: "cyan",
    NamedType: "cyan",
    ArrayType: "cyan",
    Parameter: "cyan",
    BlockStmt: "magenta",
    ExprStmt: "magenta",
    PrintStmt: "magenta",
    ReturnStmt: "magenta",
    IfStmt: "magenta",
    WhileStmt: "magenta",
    ForStmt: "magenta",
    BinaryExpr: "green",
    UnaryExpr: "green",
    LiteralExpr: "green",
    IdentifierExpr: "green",
    AssignmentExpr: "green",
    CallExpr: "green",
    IndexExpr: "green",
    MemberExpr: "green",
    NewExpr: "green",
    ConditionalExpr: "green",
    ArrayInitializer: "green",
}


def _node_style(node: Node) -> str:
    return NODE_STYLES.get(type(node), "white")


def _literal_value(value: object) -> str:
    if isinstance(value, str):
        return repr(value)
    return str(value)


def _node_label(node: Node) -> str:
    if isinstance(node, Program):
        return "Program"
    if isinstance(node, FunctionDecl):
        return f"Function({node.name})"
    if isinstance(node, VarDecl):
        return f"Variable({node.name})"
    if isinstance(node, ClassDecl):
        return f"Class({node.name})"
    if isinstance(node, FunctionType):
        return "Signature"
    if isinstance(node, (SimpleType, NamedType)):
        return f"Type({node.name})"
    if isinstance(node, ArrayType):
        return "ArrayType"
    if isinstance(node, Parameter):
        return f"Parameter({node.name})"
    if isinstance(node, BlockStmt):
        return "Block"
    if isinstance(node, ExprStmt):
        return "Expression"
    if isinstance(node, PrintStmt):
        return "Print"
    if isinstance(node, ReturnStmt):
        return "Return"
    if isinstance(node, IfStmt):
        return "If"
    if isinstance(node, WhileStmt):
        return "While"
    if isinstance(node, ForStmt):
        return "For"
    if isinstance(node, BinaryExpr):
        return f"BinaryOp({node.operator})"
    if isinstance(node, UnaryExpr):
        return f"UnaryOp({node.operator})"
    if isinstance(node, LiteralExpr):
        return f"Literal({_literal_value(node.value)})"
    if isinstance(node, IdentifierExpr):
        return f"Identifier({node.name})"
    if isinstance(node, AssignmentExpr):
        return f"Assign({node.operator})"
    if isinstance(node, CallExpr):
        return "Call"
    if isinstance(node, IndexExpr):
        return "Index"
    if isinstance(node, MemberExpr):
        return f"Member({node.member})"
    if isinstance(node, NewExpr):
        return f"New({node.type_name})"
    if isinstance(node, ConditionalExpr):
        return "Ternary"
    if isinstance(node, ArrayInitializer):
        return "ArrayInit"
    return type(node).__name__


def _node_text(node: Node) -> Text:
    return Text(_node_label(node), style=_node_style(node))


def _iter_child_nodes(node: Node):
    for field in fields(node):
        if field.name == "span":
            continue
        value = getattr(node, field.name)
        if isinstance(value, Node):
            yield value
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Node):
                    yield item


def _add_subtree(parent: Tree, node: Node) -> None:
    branch = parent.add(_node_text(node))
    for child in _iter_child_nodes(node):
        _add_subtree(branch, child)


def render_ast_tree(ast: Program) -> Tree:
    tree = Tree(_node_text(ast))
    for child in _iter_child_nodes(ast):
        _add_subtree(tree, child)
    return tree
