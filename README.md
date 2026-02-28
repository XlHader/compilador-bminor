# Compilador BMinor en Python

Proyecto para implementar un compilador de BMinor por fases.

## Estado actual

- Fase 1 implementada: analisis lexico (lexer) con `sly`.
- Incluye tracking de linea/columna, errores lexicos y pruebas automatizadas.
- El parser, AST y fases semanticas quedan para iteraciones siguientes.

## Estructura relevante

- Especificacion del lenguaje: `docs/bminor.md`
- Programas de ejemplo: `examples/test.bp`, `examples/sieve.bp`
- Lexer: `src/proyect/lexer/`
- Entrypoint CLI actual: `src/proyect/main.py`
- Tests del lexer: `tests/test_lexer.py`

## Requisitos

- Python 3.11+

## Inicio rapido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Ejecutar el lexer

Desde la raiz del proyecto:

```bash
PYTHONPATH=src python -m proyect.main
```

Por defecto procesa `examples/test.bp`. Para un archivo especifico:

```bash
PYTHONPATH=src python -m proyect.main examples/test.bp
PYTHONPATH=src python -m proyect.main examples/sieve.bp
```

Codigos de salida de la CLI:

- `0`: analisis lexico sin errores
- `1`: se detectaron errores lexicos
- `2`: archivo fuente no encontrado

## Uso programatico

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

## Calidad de codigo

```bash
ruff check .
ruff check --fix .
ruff format .
pytest
```

## Estilo de codigo

Se sigue mayormente PEP 8, automatizado con Ruff:

- indentacion con 4 espacios
- longitud de linea 79
- imports ordenados
- convenciones de nombres

Nota: en el lexer hay excepciones puntuales (`# noqa`) por requisitos internos
de `sly` (nombres de handlers de tokens en mayusculas y decorador `@_`).
