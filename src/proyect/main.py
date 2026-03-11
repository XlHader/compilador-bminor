from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import cast

from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table

from .lexer import LexError
from .logging_config import configure_logging
from .parser import ParseError, ParseResult, ast_to_dict, parse_bminor


def _build_lex_error_table(errors: list[LexError]) -> Table:
    table = Table(title="BMinor Lexical Errors")
    table.add_column("#", justify="right")
    table.add_column("Message")
    table.add_column("Lexeme")
    table.add_column("Line", justify="right")
    table.add_column("Col", justify="right")

    for idx, error in enumerate(errors, start=1):
        table.add_row(
            str(idx),
            error.message,
            repr(error.lexeme),
            str(error.line),
            str(error.column),
        )

    return table


def _build_parse_error_table(errors: list[ParseError]) -> Table:
    table = Table(title="BMinor Syntax Errors")
    table.add_column("#", justify="right")
    table.add_column("Message")
    table.add_column("Token")
    table.add_column("Lexeme")
    table.add_column("Line", justify="right")
    table.add_column("Col", justify="right")

    for idx, error in enumerate(errors, start=1):
        table.add_row(
            str(idx),
            error.message,
            error.token_type,
            repr(error.lexeme),
            str(error.line),
            str(error.column),
        )

    return table


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _print_parse_success(console: Console, result: ParseResult) -> None:
    console.print("[bold green]Parse successful[/bold green]")
    console.print(Pretty(ast_to_dict(result.ast), expand_all=True))


def main() -> int:
    console = Console()
    configure_logging()

    parser = ArgumentParser(description="Run BMinor parser on a source file")
    _ = parser.add_argument(
        "source",
        nargs="?",
        default="examples/parser.bp",
        help="Path to a .bp file (default: examples/parser.bp)",
    )
    args: Namespace = parser.parse_args()

    source_path = Path(cast(str, args.source))
    if not source_path.exists() or not source_path.is_file():
        console.print(f"[bold red]File not found:[/bold red] {source_path}")
        return 2

    source = _read_source(source_path)
    result = parse_bminor(source)

    console.print(f"[bold green]Parsing:[/bold green] {source_path}")

    if result.lex_errors:
        console.print(_build_lex_error_table(result.lex_errors))
        return 1

    if result.parse_errors:
        console.print(_build_parse_error_table(result.parse_errors))
        return 1

    _print_parse_success(console, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
