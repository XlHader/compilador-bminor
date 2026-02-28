from __future__ import annotations

# pyright: reportUndefinedVariable=false
# pyright: reportIncompatibleMethodOverride=false
from sly import Lexer

from .models import LexError, LexResult, Token


class BMinorLexer(Lexer):
    tokens = {
        "ID",
        "INTEGER_LITERAL",
        "FLOAT_LITERAL",
        "CHAR_LITERAL",
        "STRING_LITERAL",
        "ARRAY",
        "AUTO",
        "BOOLEAN",
        "CHAR",
        "ELSE",
        "FALSE",
        "FLOAT",
        "FOR",
        "FUNCTION",
        "IF",
        "INTEGER",
        "PRINT",
        "RETURN",
        "STRING",
        "TRUE",
        "VOID",
        "WHILE",
        "INC",
        "DEC",
        "EQ",
        "NE",
        "LE",
        "GE",
        "LAND",
        "LOR",
        "PLUS_ASSIGN",
        "MINUS_ASSIGN",
        "TIMES_ASSIGN",
        "DIVIDE_ASSIGN",
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "MOD",
        "EXP",
        "ASSIGN",
        "LT",
        "GT",
        "NOT",
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "LBRACKET",
        "RBRACKET",
        "COMMA",
        "SEMI",
        "COLON",
        "QUESTION",
        "DOT",
    }

    ignore = " \t\r"
    ignore_line_comment = r"//[^\n]*"

    INC = r"\+\+"
    DEC = r"--"
    EQ = r"=="
    NE = r"!="
    LE = r"<="
    GE = r">="
    LAND = r"&&"
    LOR = r"\|\|"
    PLUS_ASSIGN = r"\+="
    MINUS_ASSIGN = r"-="
    TIMES_ASSIGN = r"\*="
    DIVIDE_ASSIGN = r"/="

    PLUS = r"\+"
    MINUS = r"-"
    TIMES = r"\*"
    DIVIDE = r"/(?![/*])"
    MOD = r"%"
    EXP = r"\^"
    ASSIGN = r"="
    LT = r"<"
    GT = r">"
    NOT = r"!"

    LPAREN = r"\("
    RPAREN = r"\)"
    LBRACE = r"\{"
    RBRACE = r"\}"
    LBRACKET = r"\["
    RBRACKET = r"\]"
    COMMA = r","
    SEMI = r";"
    COLON = r":"
    QUESTION = r"\?"
    DOT = r"\.(?!\d)"

    _KEYWORDS = {
        "array": "ARRAY",
        "auto": "AUTO",
        "boolean": "BOOLEAN",
        "char": "CHAR",
        "else": "ELSE",
        "false": "FALSE",
        "float": "FLOAT",
        "for": "FOR",
        "function": "FUNCTION",
        "if": "IF",
        "integer": "INTEGER",
        "print": "PRINT",
        "return": "RETURN",
        "string": "STRING",
        "true": "TRUE",
        "void": "VOID",
        "while": "WHILE",
    }

    _SIMPLE_ESCAPES = {
        "a": "\a",
        "b": "\b",
        "e": "\x1b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
        "'": "'",
        '"': '"',
    }

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[LexError] = []
        self._source = ""

    @_(r"\n+")  # noqa: F821
    def ignore_newline(self, t):
        self.lineno += t.value.count("\n")

    @_(r"/\*(.|\n)*?\*/")  # noqa: F821
    def ignore_block_comment(self, t):
        self.lineno += t.value.count("\n")

    @_(r"\d+\.(?!\d)(?:[eE][+-]?\d+)?")  # noqa: F821
    def malformed_float(self, t):
        self._error("Malformed float literal", t.value, t.index)

    @_(  # noqa: F821
        r"(?:\d+\.\d+(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|"
        r"\d+[eE][+-]?\d+)"
    )
    def FLOAT_LITERAL(self, t):  # noqa: N802
        t.value = float(t.value)
        return t

    @_(r"\d+")  # noqa: F821
    def INTEGER_LITERAL(self, t):  # noqa: N802
        t.value = int(t.value)
        return t

    @_(r"[A-Za-z_][A-Za-z0-9_]*")  # noqa: F821
    def ID(self, t):  # noqa: N802
        if len(t.value) > 255:
            self._error(
                "Identifier exceeds max length (255)", t.value, t.index
            )
            return None

        keyword_type = self._KEYWORDS.get(t.value)
        if keyword_type is not None:
            t.type = keyword_type
            if keyword_type == "TRUE":
                t.value = True
            elif keyword_type == "FALSE":
                t.value = False
            return t

        return t

    @_(r"\"([^\\\n\"]|\\.)*(\\)?(\n|$)")  # noqa: F821
    def unterminated_string(self, t):
        self._error(
            "Unterminated string literal", t.value.rstrip("\n"), t.index
        )
        self.lineno += t.value.count("\n")

    @_(r"\"([^\\\n\"]|\\.)*\"")  # noqa: F821
    def STRING_LITERAL(self, t):  # noqa: N802
        raw = t.value[1:-1]
        decoded = self._decode_escapes(raw, t.index)
        if decoded is None:
            return None
        if len(decoded) > 255:
            self._error("String exceeds max length (255)", t.value, t.index)
            return None
        t.value = decoded
        return t

    @_(r"'([^\\\n]|\\.)*(\\)?(\n|$)")  # noqa: F821
    def unterminated_char(self, t):
        self._error("Unterminated char literal", t.value.rstrip("\n"), t.index)
        self.lineno += t.value.count("\n")

    @_(r"'([^\\\n]|\\.)*'")  # noqa: F821
    def CHAR_LITERAL(self, t):  # noqa: N802
        raw = t.value[1:-1]
        decoded = self._decode_escapes(raw, t.index)
        if decoded is None:
            return None
        if len(decoded) != 1:
            self._error("Invalid char literal length", t.value, t.index)
            return None
        t.value = decoded
        return t

    def error(self, t):
        if t.value.startswith("/*"):
            self._error("Unterminated block comment", "/*", self.index)
            self.index = len(self._source)
            return

        bad = t.value[0]
        self._error("Illegal character", bad, self.index)
        self.index += 1

    def tokenize_with_metadata(self, text: str) -> LexResult:
        self.errors = []
        self._source = text
        self.lineno = 1

        tokens: list[Token] = []
        for tok in self.tokenize(text):
            line = tok.lineno
            index = tok.index
            column = self._column_from_index(index)
            end = getattr(tok, "end", index)
            lexeme = self._source[index:end]
            tokens.append(
                Token(
                    type=tok.type,
                    lexeme=lexeme,
                    value=tok.value,
                    line=line,
                    column=column,
                    index=index,
                )
            )

        return LexResult(tokens=tokens, errors=self.errors.copy())

    def _decode_escapes(self, text: str, start_index: int) -> str | None:
        result: list[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch != "\\":
                if not (32 <= ord(ch) <= 126):
                    self._error(
                        "Non-printable character in literal", ch, start_index
                    )
                    return None
                result.append(ch)
                i += 1
                continue

            if i + 1 >= len(text):
                self._error("Invalid escape sequence", "\\", start_index + i)
                return None

            esc = text[i + 1]
            mapped = self._SIMPLE_ESCAPES.get(esc)
            if mapped is not None:
                result.append(mapped)
                i += 2
                continue

            if esc == "0" and i + 4 < len(text) and text[i + 2] == "x":
                hh = text[i + 3 : i + 5]
                if all(c in "0123456789abcdefABCDEF" for c in hh):
                    result.append(chr(int(hh, 16)))
                    i += 5
                    continue

            self._error(
                "Invalid escape sequence",
                text[i : min(i + 5, len(text))],
                start_index + i,
            )
            return None

        return "".join(result)

    def _column_from_index(self, index: int) -> int:
        last_nl = self._source.rfind("\n", 0, index)
        if last_nl < 0:
            return index + 1
        return index - last_nl

    def _error(self, message: str, lexeme: str, index: int) -> None:
        self.errors.append(
            LexError(
                message=message,
                line=self.lineno,
                column=self._column_from_index(index),
                index=index,
                lexeme=lexeme,
            )
        )


def tokenize_bminor(source: str) -> LexResult:
    lexer = BMinorLexer()
    return lexer.tokenize_with_metadata(source)
