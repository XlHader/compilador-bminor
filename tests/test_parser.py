# pyright: reportMissingImports=false

import sys
from pathlib import Path

import pytest

from proyect.main import main
from proyect.parser import (
    BinaryExpr,
    CallExpr,
    ClassDecl,
    ConditionalExpr,
    FunctionDecl,
    IdentifierExpr,
    MemberExpr,
    NewExpr,
    ParseError,
    Program,
    VarDecl,
    parse_bminor,
)

ROOT = Path(__file__).resolve().parents[1]


def test_parse_small_program() -> None:
    source = (
        "x: integer = 3;\n"
        "main: function integer () = {\n"
        '    print "ok", x;\n'
        "    return 0;\n"
        "}\n"
    )

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.parse_errors == []
    assert isinstance(result.ast, Program)
    assert len(result.ast.declarations) == 2
    assert isinstance(result.ast.declarations[0], VarDecl)
    assert isinstance(result.ast.declarations[1], FunctionDecl)
    assert result.ast.declarations[0].name == "x"
    assert result.ast.declarations[1].name == "main"


def test_parse_initializer_precedence() -> None:
    result = parse_bminor("x: integer = 3 + 4 * 2;")

    assert result.lex_errors == []
    assert result.parse_errors == []
    decl = result.ast.declarations[0]
    assert isinstance(decl, VarDecl)
    assert isinstance(decl.initializer, BinaryExpr)
    assert decl.initializer.operator == "+"
    assert isinstance(decl.initializer.right, BinaryExpr)
    assert decl.initializer.right.operator == "*"


def test_parse_reports_line_and_column() -> None:
    source = "x: integer = 3\nmain: function integer () = { return 0; }\n"

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.ast is None
    assert result.parse_errors == [
        ParseError(
            message="Unexpected token ID",
            line=2,
            column=1,
            index=15,
            lexeme="main",
            token_type="ID",
        )
    ]


def test_parse_returns_lex_errors_without_syntax_phase() -> None:
    result = parse_bminor("x: integer = @;")

    assert result.lex_errors
    assert result.parse_errors == []
    assert result.ast is None


def test_main_prints_parse_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path = ROOT / "examples" / "parser.bp"
    monkeypatch.setattr(sys, "argv", ["proyect.main", str(source_path)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Parse successful" in captured.out
    assert "main" in captured.out


def test_main_prints_syntax_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "broken.bp"
    source_path.write_text(
        "main: function integer () = { return 0 }\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["proyect.main", str(source_path)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Syntax Errors" in captured.out
    assert "Line" in captured.out
    assert "Col" in captured.out
    assert "Unexpected token" in captured.out


def test_parse_function_call_statement() -> None:
    source = "main: function integer () = { foo(1, 2); return 0; }"

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.parse_errors == []
    func = result.ast.declarations[0]
    assert isinstance(func, FunctionDecl)
    expr_stmt = func.body.statements[0]
    assert isinstance(expr_stmt.expression.callee, IdentifierExpr)
    assert expr_stmt.expression.callee.name == "foo"


def test_parse_good0_bminor() -> None:
    source = (ROOT / "examples" / "good0.bminor").read_text(encoding="utf-8")

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.parse_errors == []
    assert isinstance(result.ast, Program)
    assert len(result.ast.declarations) == 9


def test_parse_new_member_and_ternary() -> None:
    source = (
        "main: function void () = {\n"
        "    s: Sieve;\n"
        "    s = new Sieve(100);\n"
        "    s.run();\n"
        "    print true ? 1 : 0;\n"
        "}\n"
    )

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.parse_errors == []
    func = result.ast.declarations[0]
    assert isinstance(func, FunctionDecl)
    assign_stmt = func.body.statements[1]
    assert isinstance(assign_stmt.expression.value, NewExpr)
    call_stmt = func.body.statements[2]
    assert isinstance(call_stmt.expression, CallExpr)
    assert isinstance(call_stmt.expression.callee, MemberExpr)
    print_stmt = func.body.statements[3]
    assert isinstance(print_stmt.expressions[0], ConditionalExpr)


def test_parse_sieve_bp() -> None:
    source = (ROOT / "examples" / "sieve.bp").read_text(encoding="utf-8")

    result = parse_bminor(source)

    assert result.lex_errors == []
    assert result.parse_errors == []
    assert isinstance(result.ast, Program)
    assert isinstance(result.ast.declarations[0], ClassDecl)
    assert isinstance(result.ast.declarations[1], ClassDecl)
    assert isinstance(result.ast.declarations[2], FunctionDecl)
