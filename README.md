# Compilador BMinor en Python

Proyecto para implementar un compilador de BMinor por fases usando Python y
`sly`.

## Estado actual

- Fases implementadas: analisis lexico + analisis sintactico + analisis semantico.
- El lexer reporta errores con linea, columna e indice.
- El parser construye un AST y reporta errores sintacticos con token,
  lexema, linea y columna.
- La CLI ejecuta parser, analisis semantico y visualiza el AST con Rich Tree y Graphviz.

## Caracteristicas soportadas hoy

- Declaraciones de variables y funciones.
- Tipos simples, arreglos y tipos nombrados.
- Bloques, `if`, `while`, `for`, `print`, `return`.
- Expresiones aritmeticas, logicas, relacionales y asignaciones.
- Operadores prefijo/postfijo `++` y `--`.
- Construcciones B-Minor+ usadas por `examples/sieve.bp`:
  - `class`
  - `new`
  - acceso por miembro con `.`
  - operador ternario `?:`

## Estructura relevante

- Especificacion del lenguaje: `docs/bminor.md`
- Programas de ejemplo:
  - `examples/parser.bp`
  - `examples/good0.bminor`
  - `examples/sieve.bp`
- Lexer: `src/proyect/lexer/`
- Parser y AST: `src/proyect/parser/`
- Visualizacion del AST: `src/proyect/ast_visualizer/`
- Entrypoint CLI: `src/proyect/main.py`
- Tests del lexer: `tests/test_lexer.py`
- Tests del parser: `tests/test_parser.py`
- Tests del visualizador: `tests/test_ast_visualizer.py`

## Requisitos

- Python 3.11+

## Inicio rapido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Ejecutar la CLI

Desde la raiz del proyecto:

```bash
PYTHONPATH=src python -m proyect.main
```

Por defecto procesa `examples/parser.bp`. Para un archivo especifico:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp
PYTHONPATH=src python -m proyect.main examples/good0.bminor
PYTHONPATH=src python -m proyect.main examples/sieve.bp
```

Codigos de salida de la CLI:

- `0`: analisis lexico, sintactico y semantico exitoso
- `1`: se detectaron errores lexicos, sintacticos o semanticos
- `2`: archivo fuente no encontrado

## Salida de la CLI

- Si hay errores lexicos, muestra una tabla con mensaje, lexema, linea y
  columna.
- Si hay errores sintacticos, muestra una tabla con mensaje, tipo de token,
  lexema, linea y columna.
- Si hay errores semanticos, muestra una tabla con mensaje, contexto, linea
  y columna.
- Si no hay errores, muestra `Parse successful` y el AST como arbol Rich Tree
  (opcionalmente tambien como imagen Graphviz con `--graphviz`).

## Uso programatico

### Lexer

```python
from proyect.lexer import tokenize_bminor

source = "x: integer = 3;"
result = tokenize_bminor(source)

for token in result.tokens:
    print(token.type, token.lexeme, token.line, token.column)

for error in result.errors:
    print(error.message, error.line, error.column)
```

`result.tokens` usa el modelo `Token` con campos:

- `type`
- `lexeme`
- `value`
- `line`
- `column`
- `index`

`result.errors` usa `LexError` con mensaje y posicion.

### Parser

```python
from proyect.parser import parse_bminor

source = "main: function integer () = { return 0; }"
result = parse_bminor(source)

if result.lex_errors:
    for error in result.lex_errors:
        print(error.message, error.line, error.column)
elif result.parse_errors:
    for error in result.parse_errors:
        print(error.message, error.token_type, error.line, error.column)
else:
    print(result.ast)
```

`ParseResult` expone:

- `ast`: `Program | None`
- `lex_errors`: lista de `LexError`
- `parse_errors`: lista de `ParseError`

Algunos nodos AST disponibles desde `proyect.parser`:

- `Program`
- `VarDecl`
- `FunctionDecl`
- `ClassDecl`
- `BlockStmt`
- `BinaryExpr`
- `CallExpr`
- `MemberExpr`
- `NewExpr`
- `ConditionalExpr`

## Visualizacion del AST

Despues de un parse exitoso, puedes visualizar el AST de dos formas:

### Rich Tree (terminal)

Por defecto, la CLI muestra el AST como un arbol en la terminal:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp
```

Salida ejemplo:
```
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

Para desactivar:
```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --no-tree
```

### Graphviz (imagen)

Genera una imagen PNG del grafo AST:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --graphviz
```

Esto guarda `output/ast.png` con una visualizacion grafica del AST donde:
- **Program**: rojo, forma box
- **Declaraciones** (`Function(...)`, `Variable(...)`, `Class(...)`): azul
- **Statements** (`Block`, `If`, `While`, `For`, `Return`): naranja
- **Expresiones** (`BinaryOp(...)`, `Literal(...)`, `Assign(...)`): verde
- **Tipos** (`Type(...)`, `Signature`, `Parameter(...)`): gris

La visualizacion usa aristas ortogonales y etiquetas cortas como `decl 1`,
`body`, `stmt 1`, `lhs`, `rhs`, `cond` y `returns` para que el diagrama se
mantenga legible en programas medianos.

Para un path personalizado:
```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --graphviz mi_ast.png
```

**Nota importante:** El paquete `graphviz` en `requirements.txt` es solo la libreria Python. Para generar imagenes PNG necesitas el ejecutable `dot` de Graphviz instalado en el sistema operativo:

```bash
# Ubuntu/Debian
sudo apt install graphviz

# macOS
brew install graphviz

# Windows
# Descargar desde: https://graphviz.org/download/
```

Sin el ejecutable del sistema, veras un error como:
```
Error generating graph: failed to execute PosixPath('dot')...
```

El programa continuara funcionando (mostrara el arbol Rich Tree), pero no generara la imagen.

### Uso programatico

```python
from pathlib import Path

from proyect.ast_visualizer import render_ast_tree, render_ast_graphviz
from proyect.parser import parse_bminor

result = parse_bminor(source)
if result.ast:
    # Rich Tree
    tree = render_ast_tree(result.ast)
    print(tree)

    # Graphviz
    render_ast_graphviz(result.ast, Path("output/mi_ast.png"))
```

## Tests y calidad de codigo

```bash
ruff check .
ruff check --fix .
ruff format .
ruff format --check .
pytest
pytest -vv
pytest --collect-only
pytest tests/test_lexer.py
pytest tests/test_parser.py
pytest tests/test_ast_visualizer.py
pytest tests/test_parser.py::test_parse_sieve_bp
pytest tests/test_parser.py -k ternary
pytest tests/test_ast_visualizer.py -k tree
```

## Casos cubiertos por tests

- Tokenizacion basica y errores lexicos.
- Literales `char` y regresion sobre `examples/good0.bminor`.
- Parse de programas pequenos y archivo vacio.
- Precedencia de expresiones.
- Errores sintacticos con linea y columna.
- Rechazo de asignaciones con targets no validos.
- Soporte para `new`, acceso por miembro, ternario y `examples/sieve.bp`.
- Visualizacion del AST con Rich Tree (estructura, nodos, expresiones).
- Generacion de graficos con Graphviz (archivos PNG).

## Estilo de codigo

Se sigue mayormente PEP 8, automatizado con Ruff:

- indentacion con 4 espacios
- longitud de linea 79
- imports ordenados
- convenciones de nombres consistentes
- dataclasses inmutables para modelos estructurados

Nota: en lexer y parser hay excepciones puntuales (`# noqa`) por requisitos
internos de `sly`, especialmente el decorador `@_` y la redefinicion de reglas
de gramatica con el mismo nombre.
