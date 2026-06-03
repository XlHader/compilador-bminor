# Visualización del AST

Después de un parse exitoso, la CLI puede visualizar el AST en terminal con Rich
Tree o como imagen PNG con Graphviz.

## Rich Tree

Por defecto, la CLI muestra el AST como árbol en la terminal:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp
```

Salida ejemplo:

```text
Parse successful
Program
└── Function(main)
    ├── Signature
    │   └── Type(integer)
    └── Block
        ├── Print
        │   └── Literal('parser ok')
        └── Return
            └── Literal(0)
```

Para desactivar el árbol:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --no-tree
```

## Graphviz

Genera una imagen PNG del AST:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --graphviz
```

Esto guarda `output/ast.png`. Para un path personalizado:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --graphviz mi_ast.png
```

La visualización usa colores por categoría:

- **Program**: rojo, forma box.
- **Declaraciones** (`Function(...)`, `Variable(...)`, `Class(...)`): azul.
- **Statements** (`Block`, `If`, `While`, `For`, `Return`): naranja.
- **Expresiones** (`BinaryOp(...)`, `Literal(...)`, `Assign(...)`): verde.
- **Tipos** (`Type(...)`, `Signature`, `Parameter(...)`): gris.

También usa aristas ortogonales y etiquetas cortas como `decl 1`, `body`,
`stmt 1`, `lhs`, `rhs`, `cond` y `returns` para mantener legibles los diagramas.

## Requisito de Graphviz

El paquete `graphviz` en `requirements.txt` es solo la librería Python. Para
generar PNG necesitas el ejecutable `dot` instalado en el sistema operativo:

```bash
# Ubuntu/Debian
sudo apt install graphviz

# macOS
brew install graphviz
```

Sin `dot`, verás un error como:

```text
Error generating graph: failed to execute PosixPath('dot')...
```

El programa continuará funcionando y mostrará el Rich Tree, pero no generará la
imagen.

## Uso programático

```python
from pathlib import Path

from proyect.ast_visualizer import render_ast_graphviz, render_ast_tree
from proyect.parser import parse_bminor

result = parse_bminor(source)
if result.ast:
    tree = render_ast_tree(result.ast)
    print(tree)

    render_ast_graphviz(result.ast, Path("output/mi_ast.png"))
```
