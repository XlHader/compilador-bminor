from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import graphviz

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
    Node,
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


NODE_COLORS = {
    "program": ("#f8d7da", "#b42318"),
    "decl": ("#dbeafe", "#1d4ed8"),
    "stmt": ("#ffedd5", "#c2410c"),
    "expr": ("#dcfce7", "#15803d"),
    "type": ("#e5e7eb", "#4b5563"),
    "other": ("#f3f4f6", "#6b7280"),
}


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


def _node_category(node: Node) -> str:
    if isinstance(node, Program):
        return "program"
    if isinstance(node, Decl):
        return "decl"
    if isinstance(node, Stmt):
        return "stmt"
    if isinstance(node, Expr):
        return "expr"
    if isinstance(node, TypeNode):
        return "type"
    return "other"


def _edge_label(name: str, index: int | None = None) -> str:
    labels = {
        "declarations": "decl",
        "members": "member",
        "statements": "stmt",
        "parameters": "param",
        "expressions": "expr",
        "elements": "elem",
        "function_type": "signature",
        "type_node": "type",
        "initializer": "init",
        "body": "body",
        "return_type": "returns",
        "condition": "cond",
        "then_branch": "then",
        "else_branch": "else",
        "left": "lhs",
        "right": "rhs",
        "operand": "value",
        "target": "target",
        "value": "value",
        "callee": "callee",
        "arguments": "arg",
        "collection": "collection",
        "index_expr": "index",
        "object_expr": "object",
        "then_expr": "then",
        "else_expr": "else",
        "element_type": "element",
        "size": "size",
        "update": "update",
    }
    base = labels.get(name, name)
    if index is None:
        return base
    return f"{base} {index + 1}"


def _iter_child_nodes(node: Node):
    for field in fields(node):
        if field.name == "span":
            continue
        value = getattr(node, field.name)
        if isinstance(value, Node):
            yield field.name, None, value
            continue
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, Node):
                    yield field.name, index, item


def build_ast_graphviz(ast: Program) -> graphviz.Digraph:
    dot = graphviz.Digraph("ast", comment="AST", format="png")
    dot.attr(
        rankdir="TB",
        splines="ortho",
        nodesep="0.35",
        ranksep="0.45",
        pad="0.25",
        bgcolor="white",
    )
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Helvetica",
        fontsize="11",
        margin="0.12,0.08",
        penwidth="1.2",
    )
    dot.attr(
        "edge",
        color="#94a3b8",
        arrowsize="0.7",
        penwidth="1.0",
        fontname="Helvetica",
        fontsize="10",
    )

    node_ids: dict[int, str] = {}

    def ensure_node(node: Node) -> str:
        existing = node_ids.get(id(node))
        if existing is not None:
            return existing

        node_id = f"n{len(node_ids)}"
        node_ids[id(node)] = node_id

        fillcolor, color = NODE_COLORS[_node_category(node)]
        dot.node(
            node_id,
            label=_node_label(node),
            fillcolor=fillcolor,
            color=color,
            fontcolor=color,
        )
        return node_id

    def visit(node: Node) -> None:
        parent_id = ensure_node(node)
        for field_name, index, child in _iter_child_nodes(node):
            child_id = ensure_node(child)
            dot.edge(
                parent_id,
                child_id,
                xlabel=_edge_label(field_name, index),
            )
            visit(child)

    visit(ast)
    return dot


def render_ast_graphviz(ast: Program, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dot = build_ast_graphviz(ast)
    dot.render(outfile=str(output_path), cleanup=True)
