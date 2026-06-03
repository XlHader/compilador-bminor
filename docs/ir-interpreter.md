# Intérprete de IR

El intérprete ejecuta la IR generada por el compilador. Trabaja sobre las
instrucciones de tres direcciones, crea frames para llamadas a funciones,
mantiene registros temporales, variables locales/globales, arreglos, objetos y
captura la salida de `print`.

## Comando base

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --run-ir --no-tree
```

Salida esperada:

```text
IR Interpreter:
prints: ['parser ok']
return: 0
```

Para ver IR y ejecución juntos:

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --run-ir --no-tree
```

## Demos recomendadas

### Clases, objetos y métodos

```bash
PYTHONPATH=src python -m proyect.main examples/classes_demo.bminor --ir --run-ir --no-tree
```

Este ejemplo crea una clase `Wallet` con campos, constructor y métodos. En IR,
los métodos se bajan como funciones con nombre calificado (`Wallet.deposit`) y
el objeto receptor se pasa como parámetro interno `$self`.

Salida final esperada:

```text
IR Interpreter:
prints: ['owner', 'Ada', 'balance', '24']
return: 24
```

### Recursividad

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

### Primos, suma y optimización

```bash
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir --run-ir -O2 --no-tree
```

Este ejemplo genera los primos de `0` a `100`, los imprime y suma el total.
Además incluye expresiones constantes para mostrar optimización del IR.

Salida final esperada:

```text
IR Interpreter:
prints: ['Primos:', '2', '3', ..., '97', 'Suma:', '1060']
return: 1060
```

Para comparar optimización:

```bash
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir -O0 --no-tree
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir -O2 --no-tree
```

En `-O0`, expresiones como `10 - 10`, `6 / 6`, `3 - 2` y `2 - 1` aparecen como
operaciones completas (`SUBI`, `DIVI`, etc.). En `-O2`, se reducen a movimientos
constantes como `MOVI 0` o `MOVI 1`, sin cambiar el resultado del programa.
