from graphviz import Digraph
from rich.console import Console

from .logging_config import configure_logging


def build_sample_graph() -> Digraph:
    graph = Digraph(comment="Project Bootstrap")
    graph.node("A", "Start")
    graph.node("B", "Ready")
    graph.edge("A", "B")
    return graph


def main() -> int:
    console = Console()
    configure_logging()
    graph = build_sample_graph()
    console.print("[bold green]Proyecto Python inicializado[/bold green]")
    console.print(f"Grafo listo con {len(graph.body)} elementos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
