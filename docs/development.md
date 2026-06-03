# Desarrollo, ejemplos y tests

## Ejemplos disponibles

- `examples/parser.bp`
- `examples/good0.bminor`
- `examples/sieve.bp`
- `examples/classes_demo.bminor`
- `examples/factorial.bminor`
- `examples/prime_sum_opt.bminor`

## Validar examples

Con el entorno virtual activado:

```bash
source .venv/bin/activate
bash scripts/check_examples.sh
```

El script:

- exige que `good*.bminor` terminen con éxito,
- exige que `bad*.bminor` fallen,
- muestra la salida real de cada `bad*.bminor`,
- termina con código `1` si encuentra resultados inesperados.

## Tests y calidad de código

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

- Tokenización básica y errores léxicos.
- Literales `char` y regresión sobre `examples/good0.bminor`.
- Parse de programas pequeños y archivo vacío.
- Precedencia de expresiones.
- Errores sintácticos con línea y columna.
- Rechazo de asignaciones con targets no válidos.
- Soporte para `new`, acceso por miembro, ternario y `examples/sieve.bp`.
- Visualización del AST con Rich Tree.
- Generación de gráficos con Graphviz.

## Estilo de código

Se sigue mayormente PEP 8, automatizado con Ruff:

- indentación con 4 espacios,
- longitud de línea 79,
- imports ordenados,
- convenciones de nombres consistentes,
- dataclasses inmutables para modelos estructurados.

Nota: en lexer y parser hay excepciones puntuales (`# noqa`) por requisitos
internos de `sly`, especialmente el decorador `@_` y la redefinición de reglas
de gramática con el mismo nombre.
