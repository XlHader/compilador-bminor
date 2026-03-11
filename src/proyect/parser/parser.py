from __future__ import annotations

# pyright: reportUndefinedVariable=false
# ruff: noqa: F811, F821
from sly import Parser

from ..lexer.lexer import BMinorLexer
from ..lexer.models import LexError
from .models import (
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
    Parameter,
    ParseError,
    ParseResult,
    PrintStmt,
    Program,
    ReturnStmt,
    SimpleType,
    SourceSpan,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)


class _ParseAbortError(Exception):
    pass


class BMinorParser(Parser):
    tokens = BMinorLexer.tokens
    expected_shift_reduce = 1

    precedence = (
        ("nonassoc", "IFX"),
        ("nonassoc", "ELSE"),
        (
            "right",
            "ASSIGN",
            "PLUS_ASSIGN",
            "MINUS_ASSIGN",
            "TIMES_ASSIGN",
            "DIVIDE_ASSIGN",
        ),
        ("right", "QUESTION"),
        ("left", "LOR"),
        ("left", "LAND"),
        ("nonassoc", "EQ", "NE", "LT", "LE", "GT", "GE"),
        ("left", "PLUS", "MINUS"),
        ("left", "TIMES", "DIVIDE", "MOD"),
        ("right", "EXP"),
        ("right", "NOT", "UMINUS"),
        ("left", "INC", "DEC"),
    )

    def __init__(self, source: str) -> None:
        self.source = source
        self.errors: list[ParseError] = []

    @_("opt_decl_list")
    def program(self, p):
        declarations = p.opt_decl_list
        if declarations:
            span = self._merge_spans(
                declarations[0].span, declarations[-1].span
            )
        else:
            span = SourceSpan(line=1, column=1, index=0, end=0)
        return Program(span=span, declarations=declarations)

    @_("empty")
    def opt_decl_list(self, p):
        return []

    @_("decl_list")
    def opt_decl_list(self, p):
        return p.decl_list

    @_("decl_list decl")
    def decl_list(self, p):
        return [*p.decl_list, p.decl]

    @_("decl")
    def decl_list(self, p):
        return [p.decl]

    @_("ID COLON type_node SEMI")
    def decl(self, p):
        if isinstance(p.type_node, FunctionType):
            return FunctionDecl(
                span=self._span_from_parts(p),
                name=p.ID,
                function_type=p.type_node,
                body=None,
            )
        return VarDecl(
            span=self._span_from_parts(p),
            name=p.ID,
            type_node=p.type_node,
            initializer=None,
        )

    @_("ID COLON CLASS ASSIGN LBRACE opt_class_member_list RBRACE")
    def decl(self, p):
        return ClassDecl(
            span=self._span_from_parts(p),
            name=p.ID,
            members=p.opt_class_member_list,
        )

    @_("ID COLON simple_assignable_type ASSIGN expr SEMI")
    def decl(self, p):
        return VarDecl(
            span=self._span_from_parts(p),
            name=p.ID,
            type_node=p.simple_assignable_type,
            initializer=p.expr,
        )

    @_("ID COLON array_type ASSIGN LBRACE opt_expr_list RBRACE SEMI")
    def decl(self, p):
        return VarDecl(
            span=self._span_from_parts(p),
            name=p.ID,
            type_node=p.array_type,
            initializer=ArrayInitializer(
                span=self._span_from_slice(p, start=4, end=6),
                elements=p.opt_expr_list,
            ),
        )

    @_("ID COLON function_type ASSIGN block_stmt")
    def decl(self, p):
        return FunctionDecl(
            span=self._span_from_parts(p),
            name=p.ID,
            function_type=p.function_type,
            body=p.block_stmt,
        )

    @_("empty")
    def opt_class_member_list(self, p):
        return []

    @_("decl_list")
    def opt_class_member_list(self, p):
        return p.decl_list

    @_("simple_type")
    def simple_assignable_type(self, p):
        return p.simple_type

    @_("named_type")
    def simple_assignable_type(self, p):
        return p.named_type

    @_("simple_type")
    def type_node(self, p):
        return p.simple_type

    @_("named_type")
    def type_node(self, p):
        return p.named_type

    @_("array_type")
    def type_node(self, p):
        return p.array_type

    @_("function_type")
    def type_node(self, p):
        return p.function_type

    @_("AUTO")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="auto")

    @_("INTEGER")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="integer")

    @_("FLOAT")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="float")

    @_("BOOLEAN")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="boolean")

    @_("CHAR")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="char")

    @_("STRING")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="string")

    @_("VOID")
    def simple_type(self, p):
        return SimpleType(span=self._span_from_slice(p), name="void")

    @_("ID")
    def named_type(self, p):
        return NamedType(span=self._span_from_slice(p), name=p.ID)

    @_("ARRAY LBRACKET opt_expr RBRACKET simple_assignable_type")
    def array_type(self, p):
        return ArrayType(
            span=self._span_from_parts(p),
            element_type=p.simple_assignable_type,
            size=p.opt_expr,
        )

    @_("ARRAY LBRACKET opt_expr RBRACKET array_type")
    def array_type(self, p):
        return ArrayType(
            span=self._span_from_parts(p),
            element_type=p.array_type,
            size=p.opt_expr,
        )

    @_("FUNCTION simple_assignable_type LPAREN opt_param_list RPAREN")
    def function_type(self, p):
        return FunctionType(
            span=self._span_from_parts(p),
            return_type=p.simple_assignable_type,
            parameters=p.opt_param_list,
        )

    @_("FUNCTION array_type LPAREN opt_param_list RPAREN")
    def function_type(self, p):
        return FunctionType(
            span=self._span_from_parts(p),
            return_type=p.array_type,
            parameters=p.opt_param_list,
        )

    @_("empty")
    def opt_param_list(self, p):
        return []

    @_("param_list")
    def opt_param_list(self, p):
        return p.param_list

    @_("param_list COMMA param")
    def param_list(self, p):
        return [*p.param_list, p.param]

    @_("param")
    def param_list(self, p):
        return [p.param]

    @_("ID COLON simple_assignable_type")
    def param(self, p):
        return Parameter(
            span=self._span_from_parts(p),
            name=p.ID,
            type_node=p.simple_assignable_type,
        )

    @_("ID COLON array_type")
    def param(self, p):
        return Parameter(
            span=self._span_from_parts(p),
            name=p.ID,
            type_node=p.array_type,
        )

    @_("LBRACE opt_stmt_list RBRACE")
    def block_stmt(self, p):
        return BlockStmt(
            span=self._span_from_parts(p),
            statements=p.opt_stmt_list,
        )

    @_("empty")
    def opt_stmt_list(self, p):
        return []

    @_("stmt_list")
    def opt_stmt_list(self, p):
        return p.stmt_list

    @_("stmt_list stmt")
    def stmt_list(self, p):
        return [*p.stmt_list, p.stmt]

    @_("stmt")
    def stmt_list(self, p):
        return [p.stmt]

    @_("decl")
    def stmt(self, p):
        return p.decl

    @_("print_stmt")
    def stmt(self, p):
        return p.print_stmt

    @_("return_stmt")
    def stmt(self, p):
        return p.return_stmt

    @_("block_stmt")
    def stmt(self, p):
        return p.block_stmt

    @_("while_stmt")
    def stmt(self, p):
        return p.while_stmt

    @_("for_stmt")
    def stmt(self, p):
        return p.for_stmt

    @_("if_stmt")
    def stmt(self, p):
        return p.if_stmt

    @_("expr SEMI")
    def stmt(self, p):
        return ExprStmt(span=self._span_from_parts(p), expression=p.expr)

    @_("PRINT opt_expr_list SEMI")
    def print_stmt(self, p):
        return PrintStmt(
            span=self._span_from_parts(p), expressions=p.opt_expr_list
        )

    @_("RETURN opt_expr SEMI")
    def return_stmt(self, p):
        return ReturnStmt(span=self._span_from_parts(p), value=p.opt_expr)

    @_("WHILE LPAREN opt_expr RPAREN stmt")
    def while_stmt(self, p):
        return WhileStmt(
            span=self._span_from_parts(p),
            condition=p.opt_expr,
            body=p.stmt,
        )

    @_("FOR LPAREN opt_expr SEMI opt_expr SEMI opt_expr RPAREN stmt")
    def for_stmt(self, p):
        return ForStmt(
            span=self._span_from_parts(p),
            initializer=p.opt_expr0,
            condition=p.opt_expr1,
            update=p.opt_expr2,
            body=p.stmt,
        )

    @_("IF LPAREN opt_expr RPAREN stmt %prec IFX")
    def if_stmt(self, p):
        return IfStmt(
            span=self._span_from_parts(p),
            condition=p.opt_expr,
            then_branch=p.stmt,
            else_branch=None,
        )

    @_("IF LPAREN opt_expr RPAREN stmt ELSE stmt")
    def if_stmt(self, p):
        return IfStmt(
            span=self._span_from_parts(p),
            condition=p.opt_expr,
            then_branch=p.stmt0,
            else_branch=p.stmt1,
        )

    @_("empty")
    def opt_expr(self, p):
        return None

    @_("expr")
    def opt_expr(self, p):
        return p.expr

    @_("empty")
    def opt_expr_list(self, p):
        return []

    @_("expr_list")
    def opt_expr_list(self, p):
        return p.expr_list

    @_("expr_list COMMA expr")
    def expr_list(self, p):
        return [*p.expr_list, p.expr]

    @_("expr")
    def expr_list(self, p):
        return [p.expr]

    @_("expr1")
    def expr(self, p):
        return p.expr1

    @_("lvalue ASSIGN expr1")
    def expr1(self, p):
        return AssignmentExpr(
            span=self._span_from_parts(p),
            operator="=",
            target=p.lvalue,
            value=p.expr1,
        )

    @_("lvalue PLUS_ASSIGN expr1")
    def expr1(self, p):
        return AssignmentExpr(
            span=self._span_from_parts(p),
            operator="+=",
            target=p.lvalue,
            value=p.expr1,
        )

    @_("lvalue MINUS_ASSIGN expr1")
    def expr1(self, p):
        return AssignmentExpr(
            span=self._span_from_parts(p),
            operator="-=",
            target=p.lvalue,
            value=p.expr1,
        )

    @_("lvalue TIMES_ASSIGN expr1")
    def expr1(self, p):
        return AssignmentExpr(
            span=self._span_from_parts(p),
            operator="*=",
            target=p.lvalue,
            value=p.expr1,
        )

    @_("lvalue DIVIDE_ASSIGN expr1")
    def expr1(self, p):
        return AssignmentExpr(
            span=self._span_from_parts(p),
            operator="/=",
            target=p.lvalue,
            value=p.expr1,
        )

    @_("conditional_expr")
    def expr1(self, p):
        return p.conditional_expr

    @_("postfix LBRACKET expr RBRACKET")
    def lvalue(self, p):
        return IndexExpr(
            span=self._span_from_parts(p),
            collection=p.postfix,
            index_expr=p.expr,
        )

    @_("postfix DOT ID")
    def lvalue(self, p):
        return MemberExpr(
            span=self._span_from_parts(p),
            object_expr=p.postfix,
            member=p.ID,
        )

    @_("ID")
    def lvalue(self, p):
        return IdentifierExpr(span=self._span_from_slice(p), name=p.ID)

    @_("expr2 QUESTION expr COLON conditional_expr")
    def conditional_expr(self, p):
        return ConditionalExpr(
            span=self._span_from_parts(p),
            condition=p.expr2,
            then_expr=p.expr,
            else_expr=p.conditional_expr,
        )

    @_("expr2")
    def conditional_expr(self, p):
        return p.expr2

    @_("expr2 LOR expr3")
    def expr2(self, p):
        return BinaryExpr(
            span=self._span_from_parts(p),
            operator="||",
            left=p.expr2,
            right=p.expr3,
        )

    @_("expr3")
    def expr2(self, p):
        return p.expr3

    @_("expr3 LAND expr4")
    def expr3(self, p):
        return BinaryExpr(
            span=self._span_from_parts(p),
            operator="&&",
            left=p.expr3,
            right=p.expr4,
        )

    @_("expr4")
    def expr3(self, p):
        return p.expr4

    @_("expr4 EQ expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), "==", p.expr4, p.expr5)

    @_("expr4 NE expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), "!=", p.expr4, p.expr5)

    @_("expr4 LT expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), "<", p.expr4, p.expr5)

    @_("expr4 LE expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), "<=", p.expr4, p.expr5)

    @_("expr4 GT expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), ">", p.expr4, p.expr5)

    @_("expr4 GE expr5")
    def expr4(self, p):
        return BinaryExpr(self._span_from_parts(p), ">=", p.expr4, p.expr5)

    @_("expr5")
    def expr4(self, p):
        return p.expr5

    @_("expr5 PLUS expr6")
    def expr5(self, p):
        return BinaryExpr(self._span_from_parts(p), "+", p.expr5, p.expr6)

    @_("expr5 MINUS expr6")
    def expr5(self, p):
        return BinaryExpr(self._span_from_parts(p), "-", p.expr5, p.expr6)

    @_("expr6")
    def expr5(self, p):
        return p.expr6

    @_("expr6 TIMES expr7")
    def expr6(self, p):
        return BinaryExpr(self._span_from_parts(p), "*", p.expr6, p.expr7)

    @_("expr6 DIVIDE expr7")
    def expr6(self, p):
        return BinaryExpr(self._span_from_parts(p), "/", p.expr6, p.expr7)

    @_("expr6 MOD expr7")
    def expr6(self, p):
        return BinaryExpr(self._span_from_parts(p), "%", p.expr6, p.expr7)

    @_("expr7")
    def expr6(self, p):
        return p.expr7

    @_("expr8 EXP expr7")
    def expr7(self, p):
        return BinaryExpr(self._span_from_parts(p), "^", p.expr8, p.expr7)

    @_("expr8")
    def expr7(self, p):
        return p.expr8

    @_("MINUS expr8 %prec UMINUS")
    def expr8(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="-",
            operand=p.expr8,
            position="prefix",
        )

    @_("NOT expr8")
    def expr8(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="!",
            operand=p.expr8,
            position="prefix",
        )

    @_("INC expr8")
    def expr8(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="++",
            operand=p.expr8,
            position="prefix",
        )

    @_("DEC expr8")
    def expr8(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="--",
            operand=p.expr8,
            position="prefix",
        )

    @_("postfix")
    def expr8(self, p):
        return p.postfix

    @_("postfix INC")
    def postfix(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="++",
            operand=p.postfix,
            position="postfix",
        )

    @_("postfix DEC")
    def postfix(self, p):
        return UnaryExpr(
            span=self._span_from_parts(p),
            operator="--",
            operand=p.postfix,
            position="postfix",
        )

    @_("postfix LPAREN opt_expr_list RPAREN")
    def postfix(self, p):
        return CallExpr(
            span=self._span_from_parts(p),
            callee=p.postfix,
            arguments=p.opt_expr_list,
        )

    @_("postfix LBRACKET expr RBRACKET")
    def postfix(self, p):
        return IndexExpr(
            span=self._span_from_parts(p),
            collection=p.postfix,
            index_expr=p.expr,
        )

    @_("postfix DOT ID")
    def postfix(self, p):
        return MemberExpr(
            span=self._span_from_parts(p),
            object_expr=p.postfix,
            member=p.ID,
        )

    @_("primary")
    def postfix(self, p):
        return p.primary

    @_("LPAREN expr RPAREN")
    def primary(self, p):
        return p.expr

    @_("ID")
    def primary(self, p):
        return IdentifierExpr(span=self._span_from_slice(p), name=p.ID)

    @_("NEW ID LPAREN opt_expr_list RPAREN")
    def primary(self, p):
        return NewExpr(
            span=self._span_from_parts(p),
            type_name=p.ID,
            arguments=p.opt_expr_list,
        )

    @_("INTEGER_LITERAL")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=p.INTEGER_LITERAL,
            literal_type="integer",
        )

    @_("FLOAT_LITERAL")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=p.FLOAT_LITERAL,
            literal_type="float",
        )

    @_("CHAR_LITERAL")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=p.CHAR_LITERAL,
            literal_type="char",
        )

    @_("STRING_LITERAL")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=p.STRING_LITERAL,
            literal_type="string",
        )

    @_("TRUE")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=True,
            literal_type="boolean",
        )

    @_("FALSE")
    def primary(self, p):
        return LiteralExpr(
            span=self._span_from_slice(p),
            value=False,
            literal_type="boolean",
        )

    @_("")
    def empty(self, p):
        return None

    def error(self, token):
        if token is None:
            line = self.source.count("\n") + 1
            column = self._column_from_index(len(self.source))
            self.errors.append(
                ParseError(
                    message="Unexpected end of input",
                    line=line,
                    column=column,
                    index=len(self.source),
                    lexeme="EOF",
                    token_type="EOF",
                )
            )
            raise _ParseAbortError

        self.errors.append(
            ParseError(
                message=f"Unexpected token {token.type}",
                line=token.lineno,
                column=self._column_from_index(token.index),
                index=token.index,
                lexeme=self._token_lexeme(token),
                token_type=token.type,
            )
        )
        raise _ParseAbortError

    def _token_lexeme(self, token) -> str:
        end = getattr(token, "end", token.index + len(str(token.value)))
        return self.source[token.index : end]

    def _column_from_index(self, index: int) -> int:
        last_nl = self.source.rfind("\n", 0, index)
        if last_nl < 0:
            return index + 1
        return index - last_nl

    def _span_from_token(self, start_token, end_token=None) -> SourceSpan:
        token = end_token or start_token
        end = getattr(token, "end", token.index + len(str(token.value)))
        return SourceSpan(
            line=start_token.lineno,
            column=self._column_from_index(start_token.index),
            index=start_token.index,
            end=end,
        )

    def _span_from_slice(
        self, p, start: int = 0, end: int | None = None
    ) -> SourceSpan:
        symbols = p._slice
        last_index = len(symbols) - 1 if end is None else end
        return self._merge_spans(
            self._span_from_symbol(symbols[start]),
            self._span_from_symbol(symbols[last_index]),
        )

    def _span_from_symbol(self, symbol) -> SourceSpan:
        value = getattr(symbol, "value", None)
        span = getattr(value, "span", None)
        if span is not None:
            return span
        return self._span_from_token(symbol)

    def _span_from_parts(self, p) -> SourceSpan:
        first = None
        last = None
        for symbol in p._slice:
            value = getattr(symbol, "value", None)
            if value is None:
                continue
            span = getattr(value, "span", None)
            if span is not None:
                if first is None:
                    first = span
                last = span
                continue
            lineno = getattr(symbol, "lineno", None)
            index = getattr(symbol, "index", None)
            if lineno is None or index is None:
                continue
            token_span = self._span_from_token(symbol)
            if first is None:
                first = token_span
            last = token_span

        if first is None or last is None:
            return SourceSpan(line=1, column=1, index=0, end=0)
        return self._merge_spans(first, last)

    def _merge_spans(self, start: SourceSpan, end: SourceSpan) -> SourceSpan:
        return SourceSpan(
            line=start.line,
            column=start.column,
            index=start.index,
            end=end.end,
        )


def parse_bminor(source: str) -> ParseResult:
    lexer = BMinorLexer()
    tokens = list(lexer.tokenize(source))
    lex_errors: list[LexError] = lexer.errors.copy()
    if lex_errors:
        return ParseResult(ast=None, lex_errors=lex_errors, parse_errors=[])

    parser = BMinorParser(source)
    try:
        ast = parser.parse(iter(tokens))
    except _ParseAbortError:
        ast = None

    return ParseResult(
        ast=ast, lex_errors=lex_errors, parse_errors=parser.errors.copy()
    )


__all__ = ["BMinorParser", "parse_bminor"]
