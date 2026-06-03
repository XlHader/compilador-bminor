# IR y optimizaciones

La fase de IR convierte el AST validado semánticamente en una secuencia
determinística de instrucciones de tres direcciones.

Los temporales usan estilo SSA (`R1`, `R2`, `R3`, ...): cada temporal se asigna
una sola vez. Las variables, campos de objetos y elementos de arreglos se
mantienen como ubicaciones mutables mediante instrucciones de carga y
almacenamiento.

## Uso desde la CLI

```bash
PYTHONPATH=src python -m proyect.main examples/parser.bp --ir --no-tree
PYTHONPATH=src python -m proyect.main examples/prime_sum_opt.bminor --ir --run-ir -O2 --no-tree
```

Niveles de optimización:

- `-O0`: conserva la IR generada.
- `-O1`: aplica optimizaciones locales seguras como constant folding,
  simplificación algebraica, comparaciones constantes, ramas constantes y
  eliminación simple de código inalcanzable.
- `-O2`: incluye `-O1` y elimina definiciones de temporales puros que no vuelven
  a usarse.

Las instrucciones con efectos observables, llamadas, stores, saltos, labels,
alocaciones y operaciones desconocidas se conservan de forma conservadora.

## Uso programático

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

## Ejemplo de salida

Para `examples/parser.bp`:

```text
LABEL main
MOVS parser ok, R1
PRINTS R1
MOVI 0, R2
RET R2
```

## Instrucciones soportadas

Base del proyecto:

```text
MOVI VARI ALLOCI LOADI STOREI ADDI SUBI MULI DIVI PRINTI CMPI AND OR
MOVF VARF ALLOCF LOADF STOREF ADDF SUBF MULF DIVF PRINTF CMPF
MOVB VARB ALLOCB LOADB STOREB PRINTB CMPB
LABEL BRANCH CBRANCH CALL RET
```

Extensiones usadas por el lenguaje actual:

```text
MOVS VARS ALLOCS LOADS STORES CONCATS CMPS PRINTS
VARREF ALLOCREF LOADREF STOREREF
NEWARRAY ALOAD ASTORE ALENGTH
NEWOBJ GETFIELD SETFIELD
PHI PARAMI PARAMF PARAMB PARAMS PARAMREF MODI MODF POWI
```

## Cobertura de lenguaje

- Literales y operaciones `integer`, `float`, `boolean`, `char` y `string`.
- Declaraciones, cargas, stores y asignaciones compuestas.
- `print`, `return`, bloques, `if`, `while`, `for` y ternario `?:`.
- Funciones, parámetros, llamadas y retornos `void`/no-`void`.
- Clases, `new`, `init`, métodos, campos y acceso con `.`.
- Arreglos, inicializadores `{...}`, índices `arr[i]` y `array_length`.
