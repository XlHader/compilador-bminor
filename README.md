# Compilador BMinor en Python

Proyecto para implementar un compilador de BMinor por fases usando Python y
`sly`.

## Estado actual

- Fase implementada: analisis lexico + analisis sintactico.
- El lexer reporta errores con linea, columna e indice.
- El parser construye un AST y reporta errores sintacticos con token,
  lexema, linea y columna.
- La CLI ahora ejecuta el parser por defecto.
- Las fases semanticas quedan para iteraciones siguientes.

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
- Entrypoint CLI: `src/proyect/main.py`
- Tests del lexer: `tests/test_lexer.py`
- Tests del parser: `tests/test_parser.py`

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

- `0`: parse exitoso
- `1`: se detectaron errores lexicos o sintacticos
- `2`: archivo fuente no encontrado

## Salida de la CLI

- Si hay errores lexicos, muestra una tabla con mensaje, lexema, linea y
  columna.
- Si hay errores sintacticos, muestra una tabla con mensaje, tipo de token,
  lexema, linea y columna.
- Si no hay errores, muestra `Parse successful` y un volcado estructurado del
  AST.

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
pytest tests/test_parser.py::test_parse_sieve_bp
pytest tests/test_parser.py -k ternary
```

## Casos cubiertos por tests

- Tokenizacion basica y errores lexicos.
- Literales `char` y regresion sobre `examples/good0.bminor`.
- Parse de programas pequenos y archivo vacio.
- Precedencia de expresiones.
- Errores sintacticos con linea y columna.
- Rechazo de asignaciones con targets no validos.
- Soporte para `new`, acceso por miembro, ternario y `examples/sieve.bp`.

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
