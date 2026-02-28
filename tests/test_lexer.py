# pyright: reportMissingImports=false

from pathlib import Path

import pytest

from proyect.lexer import tokenize_bminor

ROOT = Path(__file__).resolve().parents[1]


def _types(source: str) -> list[str]:
    return [t.type for t in tokenize_bminor(source).tokens]


def test_tokenize_small_snippet() -> None:
    result = tokenize_bminor(
        "x: integer = 3; y: float = .25; z: boolean = true;"
    )
    assert [t.type for t in result.tokens] == [
        "ID",
        "COLON",
        "INTEGER",
        "ASSIGN",
        "INTEGER_LITERAL",
        "SEMI",
        "ID",
        "COLON",
        "FLOAT",
        "ASSIGN",
        "FLOAT_LITERAL",
        "SEMI",
        "ID",
        "COLON",
        "BOOLEAN",
        "ASSIGN",
        "TRUE",
        "SEMI",
    ]
    assert result.tokens[4].value == 3
    assert result.tokens[10].value == pytest.approx(0.25)
    assert result.tokens[16].value is True
    assert result.errors == []


def test_tokenize_test_bp() -> None:
    src = (ROOT / "examples" / "test.bp").read_text(encoding="utf-8")
    result = tokenize_bminor(src)
    assert [t.type for t in result.tokens] == [
        "ID",
        "ASSIGN",
        "INTEGER_LITERAL",
        "PLUS",
        "INTEGER_LITERAL",
        "TIMES",
        "LPAREN",
        "ID",
        "MINUS",
        "ID",
        "RPAREN",
    ]
    assert result.errors == []


def test_tokenize_sieve_bp() -> None:
    src = (ROOT / "examples" / "sieve.bp").read_text(encoding="utf-8")
    result = tokenize_bminor(src)
    assert len(result.tokens) > 50
    assert result.errors == []


@pytest.mark.parametrize(
    ("source", "expected_types"),
    [
        ("", []),
        ("// hello\n/* world */\n", []),
    ],
)
def test_empty_and_comment_only_inputs(
    source: str, expected_types: list[str]
) -> None:
    result = tokenize_bminor(source)
    assert [t.type for t in result.tokens] == expected_types
    assert result.errors == []


def test_unterminated_multiline_comment() -> None:
    result = tokenize_bminor("x = 1; /* never closes")
    assert any(
        e.message == "Unterminated block comment" for e in result.errors
    )


def test_unterminated_string() -> None:
    result = tokenize_bminor('print "hello\n')
    assert any(
        e.message == "Unterminated string literal" for e in result.errors
    )


@pytest.mark.parametrize("source", ['"abc\\', '"abc\\\n'])
def test_unterminated_string_with_trailing_backslash(
    source: str,
) -> None:
    result = tokenize_bminor(source)
    assert [e.message for e in result.errors] == [
        "Unterminated string literal"
    ]


@pytest.mark.parametrize(
    "source",
    ["c: char = '';", "c: char = 'ab';", r"c: char = '\q';"],
)
def test_invalid_chars(source: str) -> None:
    result = tokenize_bminor(source)
    assert result.errors


@pytest.mark.parametrize("source", ["'a\\", "'a\\\n"])
def test_unterminated_char_with_trailing_backslash(
    source: str,
) -> None:
    result = tokenize_bminor(source)
    assert [e.message for e in result.errors] == ["Unterminated char literal"]


def test_invalid_escape_sequences() -> None:
    result = tokenize_bminor("s: string = \"bad\\q\"; c: char = '\\0xG0';")
    assert any(e.message == "Invalid escape sequence" for e in result.errors)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("12.34", 12.34),
        (".123", 0.123),
        ("89e-2", 0.89),
        ("5.67E1", 56.7),
    ],
)
def test_valid_floats(literal: str, expected: float) -> None:
    result = tokenize_bminor(f"x: float = {literal};")
    float_token = next(t for t in result.tokens if t.type == "FLOAT_LITERAL")
    assert float_token.value == pytest.approx(expected)
    assert result.errors == []


@pytest.mark.parametrize("literal", ["11.", "10.e2"])
def test_invalid_floats(literal: str) -> None:
    result = tokenize_bminor(f"x: float = {literal};")
    assert any(e.message == "Malformed float literal" for e in result.errors)


def test_identifier_length_limits() -> None:
    valid = "a" * 255
    invalid = "b" * 256
    ok = tokenize_bminor(f"{valid}: integer;")
    bad = tokenize_bminor(f"{invalid}: integer;")
    assert ok.errors == []
    assert any(
        e.message == "Identifier exceeds max length (255)" for e in bad.errors
    )


def test_comments_whitespace_and_operators() -> None:
    src = "x++ --y == z != w <= q >= p && a || b += 3 /* c */ // d\n"
    assert _types(src) == [
        "ID",
        "INC",
        "DEC",
        "ID",
        "EQ",
        "ID",
        "NE",
        "ID",
        "LE",
        "ID",
        "GE",
        "ID",
        "LAND",
        "ID",
        "LOR",
        "ID",
        "PLUS_ASSIGN",
        "INTEGER_LITERAL",
    ]


def test_continues_after_lexical_error() -> None:
    src = "x = 1; @ y = 2;"
    result = tokenize_bminor(src)
    assert any(e.message == "Illegal character" for e in result.errors)
    assert [t.type for t in result.tokens] == [
        "ID",
        "ASSIGN",
        "INTEGER_LITERAL",
        "SEMI",
        "ID",
        "ASSIGN",
        "INTEGER_LITERAL",
        "SEMI",
    ]


def test_line_and_column_tracking() -> None:
    src = "x = 1;\n  y = x + 2;\n"
    result = tokenize_bminor(src)
    y = next(t for t in result.tokens if t.lexeme == "y")
    plus = next(t for t in result.tokens if t.type == "PLUS")
    assert y.line == 2
    assert y.column == 3
    assert plus.line == 2
    assert plus.column == 9


def test_multiline_block_comment_updates_line_tracking() -> None:
    src = "/* a\n b */\nx = 1;\n"
    result = tokenize_bminor(src)
    x = next(t for t in result.tokens if t.lexeme == "x")
    assert x.line == 3
    assert x.column == 1
