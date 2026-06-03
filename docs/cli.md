# CLI

La CLI está en `src/proyect/main.py` y se ejecuta desde la raíz del proyecto con
`PYTHONPATH=src`.

## Comando base

```bash
PYTHONPATH=src python -m proyect.main
```

Por defecto procesa `examples/parser.bp`. Para indicar un archivo:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp
PYTHONPATH=src python -m proyect.main examples/good0.bminor
PYTHONPATH=src python -m proyect.main examples/sieve.bp
```

## Opciones frecuentes

```bash
# No mostrar el AST en terminal
PYTHONPATH=src python -m proyect.main examples/parser.bp --no-tree

# Imprimir IR de tres direcciones
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --no-tree

# Ejecutar IR con el intérprete integrado
PYTHONPATH=src python -m proyect.main examples/parser.bp --run-ir --no-tree

# Imprimir y ejecutar IR
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --run-ir --no-tree

# Elegir nivel de optimización
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O0
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O1
PYTHONPATH=src python -m proyect.main examples/opt1.bminor --ir --no-tree -O2
```

## Códigos de salida

- `0`: análisis léxico, sintáctico y semántico exitoso.
- `1`: se detectaron errores léxicos, sintácticos o semánticos.
- `2`: archivo fuente no encontrado.

## Salida

- Si hay errores léxicos, muestra una tabla con mensaje, lexema, línea y
  columna.
- Si hay errores sintácticos, muestra una tabla con mensaje, tipo de token,
  lexema, línea y columna.
- Si hay errores semánticos, muestra una tabla con mensaje, contexto, línea y
  columna.
- Si no hay errores, muestra `Parse successful` y el AST como Rich Tree.
- Con `--graphviz`, también puede guardar una imagen del AST.
- Con `--ir`, imprime una sección `IR Code`.
- Con `--run-ir`, ejecuta el IR y muestra una sección `IR Interpreter` con los
  `prints` capturados y el valor de retorno de `main`.

## Uso programático

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

`result.tokens` usa el modelo `Token` con `type`, `lexeme`, `value`, `line`,
`column` e `index`. `result.errors` usa `LexError` con mensaje y posición.

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

`ParseResult` expone `ast`, `lex_errors` y `parse_errors`.
