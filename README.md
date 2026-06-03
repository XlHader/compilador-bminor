# Compilador BMinor en Python

Proyecto para implementar un compilador de BMinor por fases usando Python y
`sly`.

## Estado actual

- Fases implementadas: analisis lexico + analisis sintactico + analisis
  semantico + generacion de IR de tres direcciones.
- El lexer reporta errores con linea, columna e indice.
- El parser construye un AST y reporta errores sintacticos con token,
  lexema, linea y columna.
- La CLI ejecuta parser, analisis semantico, visualiza el AST con Rich Tree y
  Graphviz, puede imprimir IR con `--ir`, optimizarlo con `-O0`, `-O1`,
  `-O2`, y ejecutarlo con `--run-ir`.

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
  - `examples/classes_demo.bminor`
  - `examples/factorial.bminor`
  - `examples/prime_sum_opt.bminor`
- Lexer: `src/proyect/lexer/`
- Parser y AST: `src/proyect/parser/`
- Generacion de IR: `src/proyect/ir/`
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

Para imprimir el IR de tres direcciones despues del analisis semantico:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --no-tree
```

Para ejecutar el IR generado con el interprete integrado:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --run-ir --no-tree
```

Para mostrar el IR y ejecutarlo en el mismo comando:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --run-ir --no-tree
```

El IR tambien acepta niveles de optimizacion locales estilo compilador:

```bash
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O0
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O1
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O2
```

Tambien se puede optimizar y ejecutar el IR en una sola pasada:

```bash
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir --run-ir -O2 --no-tree
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
- Con `--ir`, si no hay errores, imprime una seccion `IR Code` con las
  instrucciones generadas. Las opciones `-O0`, `-O1` y `-O2` controlan el
  nivel de optimizacion aplicado antes de imprimir.
- Con `--run-ir`, si no hay errores, ejecuta el IR con el interprete integrado
  y muestra una seccion `IR Interpreter` con los `prints` capturados y el valor
  de retorno de `main`.

## Generacion de IR

La fase de IR convierte el AST validado semanticamente en una secuencia
deterministica de instrucciones de tres direcciones. Los registros virtuales
temporales usan estilo SSA (`R1`, `R2`, `R3`, ...): cada temporal se asigna una
sola vez. Las variables, campos de objetos y elementos de arreglos se mantienen
como ubicaciones mutables mediante instrucciones de carga y almacenamiento.

Uso programatico:

```python
from proyect.ir import format_ir, generate_ir, optimize_ir
from proyect.parser import parse_bminor
from proyect.semantic import analyze_semantic

parsed = parse_bminor("main: function integer () = { return 0; }")
semantic = analyze_semantic(parsed.ast)
ir = generate_ir(parsed.ast, semantic)
optimized = optimize_ir(ir, level=2)

print(optimized.to_tuples())
print(format_ir(optimized))
```

`-O0` conserva la IR generada. `-O1` aplica optimizaciones locales seguras,
como constant folding, simplificacion algebraica, comparaciones constantes,
ramas constantes y eliminacion de codigo inalcanzable simple. `-O2` incluye
`-O1` y elimina definiciones de temporales puros que no vuelven a usarse. Las
instrucciones con efectos observables, llamadas, stores, saltos, labels,
alocaciones y operaciones desconocidas se conservan de forma conservadora.

Ejemplo de salida para `examples/parser.bp`:

```text
LABEL main
MOVS parser ok, R1
PRINTS R1
MOVI 0, R2
RET R2
```

### Instrucciones soportadas

El IR incluye las instrucciones base del proyecto para enteros, flotantes,
bytes/chars, control de flujo, llamadas y retorno:

```text
MOVI VARI ALLOCI LOADI STOREI ADDI SUBI MULI DIVI PRINTI CMPI AND OR
MOVF VARF ALLOCF LOADF STOREF ADDF SUBF MULF DIVF PRINTF CMPF
MOVB VARB ALLOCB LOADB STOREB PRINTB CMPB
LABEL BRANCH CBRANCH CALL RET
```

Tambien se documentan extensiones necesarias para el lenguaje actual completo:

```text
MOVS VARS ALLOCS LOADS STORES CONCATS CMPS PRINTS
VARREF ALLOCREF LOADREF STOREREF
NEWARRAY ALOAD ASTORE ALENGTH
NEWOBJ GETFIELD SETFIELD
PHI PARAMI PARAMF PARAMB PARAMS PARAMREF MODI MODF POWI
```

Cobertura de lenguaje del IR:

- literales y operaciones `integer`, `float`, `boolean`, `char` y `string`,
- declaraciones, cargas, stores y asignaciones compuestas,
- `print`, `return`, bloques, `if`, `while`, `for` y ternario `?:`,
- funciones, parametros, llamadas y retornos `void`/no-`void`,
- clases, `new`, `init`, metodos, campos y acceso con `.`,
- arreglos, inicializadores `{...}`, indices `arr[i]` y `array_length`.

## Ejecucion del IR con interpreter

El interprete ejecuta la IR generada por el compilador. Trabaja sobre las
instrucciones de tres direcciones, crea frames para llamadas a funciones,
mantiene registros temporales, variables locales/globales, arreglos, objetos y
captura la salida de `print`.

Comando base:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --run-ir --no-tree
```

Salida esperada:

```text
IR Interpreter:
prints: ['parser ok']
return: 0
```

Para ver IR y ejecucion juntos:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --run-ir --no-tree
```

### Demos recomendadas

#### Clases, objetos y metodos

```bash
PYTHONPATH=src python -m proyect.main examples/classes_demo.bminor --ir --run-ir --no-tree
```

Este ejemplo crea una clase `Wallet` con campos, constructor y metodos. En IR,
los metodos se bajan como funciones con nombre calificado (`Wallet.deposit`) y
el objeto receptor se pasa como parametro interno `$self`.

Salida final esperada:

```text
IR Interpreter:
prints: ['owner', 'Ada', 'balance', '24']
return: 24
```

#### Recursividad

```bash
PYTHONPATH=src python -m proyect.main examples/factorial.bminor --ir --run-ir --no-tree
```

Este ejemplo calcula `fact(5)` con llamadas recursivas. Cada `CALL fact` crea un
frame nuevo y cada `RET` devuelve el valor al frame anterior.

Salida final esperada:

```text
IR Interpreter:
prints: ['120']
return: 120
```

#### Primos, suma y optimizacion

```bash
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir --run-ir -O2 --no-tree
```

Este ejemplo genera los primos de `0` a `100`, los imprime y suma el total.
Ademas incluye expresiones constantes para mostrar optimizacion del IR.

Salida final esperada:

```text
IR Interpreter:
prints: ['Primos:', '2', '3', ..., '97', 'Suma:', '1060']
return: 1060
```

Para comparar optimizacion:

```bash
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir -O0 --no-tree
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir -O2 --no-tree
```

En `-O0`, expresiones como `10 - 10`, `6 / 6`, `3 - 2` y `2 - 1`
aparecen como operaciones completas (`SUBI`, `DIVI`, etc.). En `-O2`, esas
expresiones se reducen a movimientos constantes como `MOVI 0` o `MOVI 1`, sin
cambiar el resultado del programa.

## Validar los examples

Con el entorno virtual activado, puedes correr todos los ejemplos de
`examples/` con este script:

```bash
source .venv/bin/activate
bash scripts/check_examples.sh
```

El script:

- exige que `good*.bminor` terminen con exito,
- exige que `bad*.bminor` fallen,
- muestra la salida real de cada `bad*.bminor` para revisar por que falla,
- y termina con codigo `1` si encuentra resultados inesperados.

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
