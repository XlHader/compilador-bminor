# Compilador BMinor en Python

Compilador de BMinor por fases usando Python y `sly`.

## Estado actual

- Fases implementadas: análisis léxico, sintáctico, semántico y generación de IR
  de tres direcciones.
- La CLI reporta errores con ubicación, muestra el AST, puede imprimir IR,
  optimizarlo con `-O0`, `-O1`, `-O2`, y ejecutarlo con `--run-ir`.
- Soporta declaraciones, funciones, tipos simples, arreglos, control de flujo,
  expresiones, `print`, `return`, clases, `new`, acceso con `.` y ternario `?:`.

## Requisitos

- Python 3.11+

## Inicio rápido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Uso básico

Desde la raíz del proyecto:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp
```

Comandos útiles:

```bash
# Parsear sin imprimir el árbol AST
PYTHONPATH=src python -m proyect.main examples/parser.bp --no-tree

# Imprimir IR
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --no-tree

# Ejecutar IR
PYTHONPATH=src python -m proyect.main examples/parser.bp --run-ir --no-tree

# Optimizar IR
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir --run-ir -O2 --no-tree
```

Códigos de salida:

- `0`: análisis exitoso
- `1`: error léxico, sintáctico o semántico
- `2`: archivo fuente no encontrado

## Documentación

| Tema | Documento |
| --- | --- |
| Especificación del lenguaje | [`docs/bminor.md`](docs/bminor.md) |
| CLI y salida esperada | [`docs/cli.md`](docs/cli.md) |
| IR y optimizaciones | [`docs/ir.md`](docs/ir.md) |
| Intérprete de IR | [`docs/ir-interpreter.md`](docs/ir-interpreter.md) |
| AST y visualización | [`docs/ast-visualizer.md`](docs/ast-visualizer.md) |
| Desarrollo, examples y tests | [`docs/development.md`](docs/development.md) |

## Estructura principal

- `src/proyect/lexer/`: lexer
- `src/proyect/parser/`: parser y AST
- `src/proyect/semantic/`: análisis semántico
- `src/proyect/ir/`: generación, optimización e interpretación de IR
- `src/proyect/ast_visualizer/`: visualización del AST
- `src/proyect/main.py`: entrada de la CLI
- `examples/`: programas de ejemplo
- `tests/`: suite de pruebas

## Tests

```bash
ruff check .
ruff format --check .
pytest
bash scripts/check_examples.sh
```
