from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Token:
    type: str
    lexeme: str
    value: object
    line: int
    column: int
    index: int


@dataclass(frozen=True, slots=True)
class LexError:
    message: str
    line: int
    column: int
    index: int
    lexeme: str


@dataclass(frozen=True, slots=True)
class LexResult:
    tokens: list[Token]
    errors: list[LexError]
