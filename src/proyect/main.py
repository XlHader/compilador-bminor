from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import cast

from rich.console import Console
from rich.table import Table

from .ast_visualizer import render_ast_graphviz, render_ast_tree
from .lexer import LexError
from .logging_config import configure_logging
from .parser import ParseError, ParseResult, parse_bminor


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


def _print_parse_success(
    console: Console, result: ParseResult, show_tree: bool = True
) -> None:
    if result.ast is None:
        return
    console.print("[bold green]Parse successful[/bold green]")
    if show_tree:
        console.print(render_ast_tree(result.ast))


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
    _ = parser.add_argument(
        "--tree",
        action="store_true",
        default=True,
        help="Display AST as Rich tree (default: True)",
    )
    _ = parser.add_argument(
        "--no-tree",
        action="store_true",
        help="Disable Rich tree display",
    )
    _ = parser.add_argument(
        "--graphviz",
        nargs="?",
        const="output/ast.png",
        metavar="PATH",
        help="Generate Graphviz AST visualization (default: output/ast.png)",
    )
    args: Namespace = parser.parse_args()

    show_tree = args.tree and not args.no_tree

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

    _print_parse_success(console, result, show_tree)

    if args.graphviz and result.ast is not None:
        output_path = Path(args.graphviz)
        try:
            render_ast_graphviz(result.ast, output_path)
            console.print(
                f"[bold blue]AST graph saved to:[/bold blue] {output_path}"
            )
        except Exception as e:
            console.print(f"[bold red]Error generating graph:[/bold red] {e}")
            console.print(
                "[yellow]Make sure Graphviz is installed on your system"
                " (apt install graphviz / brew install graphviz)[/yellow]"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
