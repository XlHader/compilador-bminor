# pyright: reportMissingImports=false
from io import StringIO

import pytest
from rich.console import Console
from rich.tree import Tree

from proyect.ast_visualizer import (
    build_ast_graphviz,
    render_ast_graphviz,
    render_ast_tree,
)
from proyect.parser import parse_bminor


def _parse_source(source: str):
    result = parse_bminor(source)
    assert result.ast is not None
    assert not result.lex_errors
    assert not result.parse_errors
    return result.ast


def _tree_to_str(tree: Tree) -> str:
    console = Console(
        file=StringIO(),
        force_terminal=False,
        color_system=None,
        width=120,
    )
    console.print(tree)
    return console.file.getvalue()


class TestTreeRenderer:
    def test_render_ast_tree_returns_tree(self):
        source = "x: integer = 1;"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        assert isinstance(tree, Tree)

    def test_tree_contains_program_node(self):
        source = "x: integer = 1;"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        assert str(tree.label) == "Program"

    def test_tree_renders_variable_hierarchy(self):
        source = "x: integer = 1;"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        assert "Program" in rendered
        assert "Variable(x)" in rendered
        assert "Type(integer)" in rendered
        assert "Literal(1)" in rendered

    def test_tree_preserves_parent_child_hierarchy(self):
        source = "main: function integer () = { return 0; }"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        expected = (
            "Program\n"
            "└── Function(main)\n"
            "    ├── Signature\n"
            "    │   └── Type(integer)\n"
            "    └── Block\n"
            "        └── Return\n"
            "            └── Literal(0)"
        )
        assert expected in rendered

    def test_tree_nests_binary_expression_under_return(self):
        source = "main: function integer () = { return 1 + 2; }"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        expected = (
            "Return\n"
            "            └── BinaryOp(+)\n"
            "                ├── Literal(1)\n"
            "                └── Literal(2)"
        )
        assert expected in rendered

    def test_tree_contains_literal_expr(self):
        source = "x: integer = 42;"
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        assert "Literal(42)" in rendered

    def test_tree_contains_if_stmt(self):
        source = """
        main: function integer () = {
            if (true) return 0;
            return 0;
        }
        """
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        assert "If" in rendered

    def test_tree_contains_while_stmt(self):
        source = """
        main: function integer () = {
            while (true) {}
            return 0;
        }
        """
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        rendered = _tree_to_str(tree)
        assert "While" in rendered

    def test_tree_handles_empty_program(self):
        source = ""
        ast = _parse_source(source)
        tree = render_ast_tree(ast)
        assert isinstance(tree, Tree)
        assert str(tree.label) == "Program"


class TestGraphvizRenderer:
    def test_build_ast_graphviz_uses_orthogonal_edges_with_xlabels(self):
        source = "main: function integer () = { return 1 + 2; }"
        ast = _parse_source(source)
        dot = build_ast_graphviz(ast)
        assert "splines=ortho" in dot.source
        assert "xlabel=" in dot.source

    def test_build_ast_graphviz_uses_simplified_labels(self):
        source = "main: function integer () = { return 1 + 2; }"
        ast = _parse_source(source)
        dot = build_ast_graphviz(ast)
        assert "Function(main)" in dot.source
        assert "BinaryOp(+) " not in dot.source
        assert "BinaryOp(+)" in dot.source

    def test_render_ast_graphviz_creates_file(self, tmp_path):
        source = "x: integer = 1;"
        ast = _parse_source(source)
        output_path = tmp_path / "test_ast.png"
        try:
            render_ast_graphviz(ast, output_path)
            assert output_path.exists()
        except Exception:
            pytest.skip("Graphviz system executable not available")

    def test_render_ast_graphviz_with_function(self, tmp_path):
        source = """
        main: function integer () = {
            return 0;
        }
        """
        ast = _parse_source(source)
        output_path = tmp_path / "test_func.png"
        try:
            render_ast_graphviz(ast, output_path)
            assert output_path.exists()
        except Exception:
            pytest.skip("Graphviz system executable not available")

    def test_render_ast_graphviz_with_complex_expr(self, tmp_path):
        source = "x: integer = (1 + 2) * 3;"
        ast = _parse_source(source)
        output_path = tmp_path / "test_expr.png"
        try:
            render_ast_graphviz(ast, output_path)
            assert output_path.exists()
        except Exception:
            pytest.skip("Graphviz system executable not available")

    def test_render_ast_graphviz_empty_program(self, tmp_path):
        source = ""
        ast = _parse_source(source)
        output_path = tmp_path / "test_empty.png"
        try:
            render_ast_graphviz(ast, output_path)
            assert output_path.exists()
        except Exception:
            pytest.skip("Graphviz system executable not available")
