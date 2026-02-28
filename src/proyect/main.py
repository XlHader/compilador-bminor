from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import cast

from rich.console import Console
from rich.table import Table

from .lexer import LexResult, tokenize_bminor
from .logging_config import configure_logging


def _build_token_table(result: LexResult) -> Table:
    table = Table(title="BMinor Lexer Output")
    table.add_column("#", justify="right")
    table.add_column("Type")
    table.add_column("Lexeme")
    table.add_column("Value")
    table.add_column("Line", justify="right")
    table.add_column("Col", justify="right")

    for idx, token in enumerate(result.tokens, start=1):
        table.add_row(
            str(idx),
            token.type,
            repr(token.lexeme),
            repr(token.value),
            str(token.line),
            str(token.column),
        )

    if result.errors:
        table.caption = f"Lexical errors: {len(result.errors)}"

    return table


def _build_error_table(result: LexResult) -> Table:
    table = Table(title="BMinor Lexer Errors")
    table.add_column("#", justify="right")
    table.add_column("Message")
    table.add_column("Lexeme")
    table.add_column("Line", justify="right")
    table.add_column("Col", justify="right")

    for idx, error in enumerate(result.errors, start=1):
        table.add_row(
            str(idx),
            error.message,
            repr(error.lexeme),
            str(error.line),
            str(error.column),
        )

    return table


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    console = Console()
    configure_logging()

    parser = ArgumentParser(description="Run BMinor lexer on a source file")
    _ = parser.add_argument(
        "source",
        nargs="?",
        default="examples/test.bp",
        help="Path to a .bp file (default: examples/test.bp)",
    )
    args: Namespace = parser.parse_args()

    source_path = Path(cast(str, args.source))
    if not source_path.exists() or not source_path.is_file():
        console.print(f"[bold red]File not found:[/bold red] {source_path}")
        return 2

    source = _read_source(source_path)
    result = tokenize_bminor(source)
    token_table = _build_token_table(result)
    error_table = _build_error_table(result)

    console.print(f"[bold green]Lexing:[/bold green] {source_path}")
    console.print(token_table)

    if error_table.row_count > 0:
        console.print(error_table)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
