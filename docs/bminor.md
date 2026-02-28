# Descripción B-Minor

**Nota**: El lenguaje B-Minor utilizado en esta clase cambia cada año para ofrecer nuevos desafíos y oportunidades. Este documento difiere del libro de texto en los siguientes aspectos:

* Las cadenas y los caracteres tienen varios códigos de escape adicionales.
* Los arrays se pueden declarar con una longitud determinada en tiempo de ejecución.
* Se han añadido valores y tipos de punto flotante.


## Descripción General

Esta es una especificación informal de B-Minor 2025, un lenguaje similar a C para su uso en una clase de compiladores de pregrado. B-Minor incluye expresiones, flujo de control básico, funciones recursivas y comprobación estricta de tipos. Es compatible con el código objeto de C ordinario y, por lo tanto, puede aprovechar la biblioteca estándar de C, dentro de sus tipos definidos. Es lo suficientemente similar a C como para resultar familiar, pero lo suficientemente diferente como para ofrecer una idea de las alternativas.


Este documento es deliberadamente informal: la especificación más precisa de un lenguaje es el propio compilador, ¡y es su trabajo escribirlo! Es su responsabilidad leer el documento con atención y extraer una especificación formal. Seguramente encontrará elementos poco claros o con especificaciones incompletas, por lo que le animamos a plantear preguntas en clase.

## Espacios y comentarios

En B-Minor, los espacios son cualquier combinación de los siguientes caracteres: tabulaciones, espacios, salto de línea (\n) y retorno de carro (\r). La ubicación de los espacios no es relevante en B-Minor. Tanto los comentarios de estilo C como los de C++ son válidos en B-Minor:

```c
/* A C-style comment */
a=5; // A C++ style comment
```

## Identificadores

Los identificadores (es decir, nombres de variables y funciones) pueden contener letras, números y guiones bajos. Deben comenzar con una letra o un guion bajo. Estos son ejemplos de identificadores válidos:

```c
i x mystr fog123 BigLongName55
```

Las siguientes cadenas son palabras clave en B-Minor (o reservadas para una futura expansión) y no pueden usarse como identificadores:

```c
array auto boolean char else false float for function if integer print return string true void while
```

## Tipos

B-Minor tiene cinco tipos atómicos: integers, floats, booleans, charaters y strings. Una variable se declara con un nombre seguido de dos puntos, un tipo y un inicializador opcional. Por ejemplo:

```c
x: integer;
y: integer = 123;
f: float = 45.67;
b: boolean = false;
c: char    = 'q';
s: string  = "hello bminor\n";
```

Un **integer** siempre es un valor con signo de 64 bits. **float** es un número de punto flotante que cumple con el estándar [IEEE 754](https://en.m.wikipedia.org/wiki/Double-precision_floating-point_format) de doble precisión. **boolean** puede tomar los valores literales **true** o **false**. **char** es un carácter ASCII de 8 bits. **string** es una cadena constante entre comillas dobles que termina en nulo y no se puede modificar.

Los valores **float** se pueden representar de varias maneras. Un método consiste en colocar el componente entero, un punto y el componente fraccionario en una fila, como en **12.34**. Otro método válido es usar la representación científica del valor, que implica tener un valor de punto flotante, como se describió anteriormente, seguido de un exponente (representado como **e** o **E**). Algunos ejemplos serían **5.67E1**, que tiene el valor de 56.7, o **89e-2**, que tiene el valor de 0.89. Los valores **float** pueden ir precedidos de un signo más o menos opcional. El valor del exponente también puede ir precedido de un signo más o menos opcional. Además, solo se puede omitir la parte entera del float para valores válidos de **float**. Esto convierte a **.123** en un número de punto flotante válido, pero no a **11.**

Tanto **char** como **string** pueden contener cualquier carácter imprimible entre los valores decimales ASCII 32 y 126 inclusive. Además, se utilizan los siguientes códigos de barra invertida para representar caracteres especiales:

| Código | Valor | Significado |
| --- | --- | --- |
| `\a` | 7 | Sonido de campana |
| `\b` | 8 | Backspace |
| `\e` | 27 | Escape |
| `\f` | 12 | Form Feed (limpiar) |
| `\n` | 10 | Newline |
| `\r` | 13 | Carriage Return |
| `\t` | 9 | Tab |
| `\v` | 11 | Tab vertical |
| `\\` | 92 | Backslash |
| `\`   | 39 | Comilla simple |
| `\"` | 34 | Comilla doble |
| `\0xHH` | HH | Dígito hexadecimal |

(Cualquier otro carácter después de una barra invertida no es válido).

Tanto las cadenas como los identificadores pueden tener hasta **255** caracteres, sin incluir el terminador nulo.

B-minor también admite matrices globales de tamaño fijo y matrices locales de tamaño variable. Pueden declararse sin valor, lo que hace que contengan solo ceros: 

```c
a: array [5] integer;
```

O bien, se pueden asignar valores específicos a toda la matriz:

```c
a: array [5] integer = {1,2,3,4,5};
```

## Expresiones

B-Minor contiene muchos de los operadores aritméticos de C, con el mismo significado y nivel de precedencia:


| Simbolo | Significado |
| --- | --- |
| `() [] f()` | Agrupación, subíndice de array, llamada a función |
| `++ --` | Incremento y decremento (postfijo) |
| `- !` | Negación unaria y no (logico) |
| `^` | Exponente |
| `* / %` | Multiplicación, división y resto |
| `+ -` | Suma y resta |
| `< <= > >= == !=` | Comparación |
| `&&` | Conexión lógica y |
| `||` | Conexión lógica o |
| `=` | Asignación |

B-Minor es **estrictamente tipado**. Esto significa que solo se puede asignar un valor a una variable (o parámetro de función) si los tipos coinciden **exactamente**. No se pueden realizar muchas de las conversiones rápidas y flexibles que se encuentran en C.

A continuación, se presentan ejemplos de algunos (pero no todos) errores de tipo:

```c
x: integer = 65;
y: char = 'A';
if(x>y) ... // error: x and y are of different types!

f: integer = 0;
if(f) ...      // error: f is not a boolean!

writechar: function void ( c: char );
a: integer = 65;
writechar(a);  // error: a is not a char!

b: array [2] boolean = {true,false};
x: integer = 0;
x = b[0];      // error: x is not a boolean!

x: integer = 0;
y: float = x;  // error: integer types can not be implicitly converted to float
```

A continuación se muestran algunos ejemplos (pero no todos) de asignaciones de tipos correctas:

```c
b: boolean;
x: integer = 3;
y: integer = 5;
b = x<y;     // ok: the expression x<y is boolean

f: integer = 0;
if(f==0) ...    // ok: f==0 is a boolean expression

c: char = 'a';
if(c=='a') ...  // ok: c and 'a' are both chars
```

## Declaraciones y sentencias

En B-Minor, se pueden declarar variables globales con inicializadores de constantes opcionales, prototipos de funciones y definiciones de funciones. Dentro de las funciones, se pueden declarar variables locales (incluyendo matrices) con expresiones de inicialización opcionales. Las reglas de alcance son idénticas a las de C. Las definiciones de funciones no pueden estar anidadas.

En las funciones, las sentencias básicas pueden ser expresiones aritméticas, sentencias de retorno, sentencias de impresión, sentencias if y if-else, bucles for o código dentro de grupos internos { }:

```c
// An arithmetic expression statement.
y = m*x + b;

// A return statement.
return (f-32)*5/9;

// An if-else statement.
if( temp>100 ) {
    print "It's really hot!\n";
} else if( temp>70 ) {
    print "It's pretty warm.\n";
} else {
    print "It's not too bad.\n";
}

// A for loop statement.
for( i=0; i<100; i++ ) {
    print i;
}
```

B-Minor no tiene sentencias switch, bucles while ni bucles do-while. (Pero podrías considerar añadirlos como un pequeño proyecto adicional).

La sentencia print es un poco inusual porque es una sentencia y no una llamada a función, como printf en C. print toma una lista de expresiones separadas por comas y las imprime en la consola, así:

```c
print "The temperature is: ", temp, " degrees\n";
```

## Funciones

Las funciones se declaran de la misma forma que las variables, con la diferencia de que se especifica el tipo de **function**, seguido del tipo de retorno, los argumentos y el código.

```c
square: function integer ( x: integer ) = {
	return x^2;
}
```

El tipo de retorno debe ser uno de los cuatro tipos atómicos o **void** para indicar que no hay tipo. Los argumentos de la función pueden ser de cualquier tipo. Los argumentos **integer**, **boolean** y **char** se pasan por valor, mientras que los argumentos de **string** y **array** se pasan por referencia. La implementación de arrays incluirá una función **array_length()** que permite obtener la longitud de un array en tiempo de ejecución.

```c
printarray: function void ( a: array [] integer ) = {
	i: integer;
	for( i=0;i<array_length(a);i++) {
		print a[i], "\n";
	}
}
```

Se puede proporcionar un prototipo de función que indique la existencia y el tipo de la función, pero no incluya código. Esto es necesario si el usuario desea llamar a una función externa enlazada por otra biblioteca. Por ejemplo, para invocar la función de C, **puts**:

```c
puts: function void ( s: string );

main: function integer () = {
	puts("hello world");
}
```

Un programa completo debe tener una función **main** que devuelva un integer. Los argumentos de **main** pueden ser vacíos o usar **argc** y **argv** con el mismo significado que en C:

```c
main: function integer ( argc: integer, argv: array [] string ) = {
  puts("hello world");
}
```

## Gramática de B-Minor

La gramática libre de contexto para este proyecto es bastante elegante en mi opinión:


```
prog ::= decl_list 'EOF'

/* Declarations */

decl_list ::= /* epsilon */
    | decl decl_list

decl ::= 'ID' ':' type_simple ';'
    | 'ID' ':' type_array_sized ';'
    | 'ID' ':' type_func ';'
    | decl_init

decl_init ::= 'ID' ':' type_simple '=' expr ';'
    | 'ID' ':' type_array_sized '=' '{' opt_expr_list '}' ';'
    | 'ID' ':' type_func '=' '{' opt_stmt_list '}'

/* Statements */

opt_stmt_list ::= /* epsilon */
    | stmt_list

stmt_list ::= stmt
    | stmt stmt_list

stmt ::= open_stmt
    | closed_stmt

closed_stmt ::= if_stmt_closed
    | for_stmt_closed
    | simple_stmt

open_stmt ::= if_stmt_open
    | for_stmt_open

if_cond ::= 'IF' '(' opt_expr ')'

if_stmt_closed ::= if_cond closed_stmt 'ELSE' closed_stmt

if_stmt_open ::= if_cond stmt
    | if_cond closed_stmt 'ELSE' if_stmt_open

for_header ::= 'FOR' '(' opt_expr ';' opt_expr ';' opt_expr ')'

for_stmt_open ::= for_header open_stmt

for_stmt_closed ::= for_header closed_stmt

/* Simple statements are not recursive */
simple_stmt ::= print_stmt
    | return_stmt
    | block_stmt
    | decl
    | expr ';'

print_stmt ::= 'PRINT' opt_expr_list ';'

return_stmt ::= 'RETURN' opt_expr ';'

block_stmt ::= '{' stmt_list '}'

/* Expressions */

opt_expr_list ::= /* epsilon */
    | expr_list

expr_list ::= expr
    | expr ',' expr_list

opt_expr ::= /* epsilon */
    | expr

expr ::= expr1

expr1 ::= lval '=' expr1
    | expr2

lval ::= 'ID'
    | 'ID' index

expr2 ::= expr2 'LOR' expr3
    | expr3

expr3 ::= expr3 'LAND' expr4
    | expr4

expr4 ::= expr4 'EQ' expr5
    | expr4 'NE' expr5
    | expr4 'LT' expr5
    | expr4 'LE' expr5
    | expr4 'GT' expr5
    | expr4 'GE' expr5
    | expr5


expr5 ::= expr5 '+' expr6
    | expr5 '-' expr6
    | expr6

expr6 ::= expr6 '*' expr7
    | expr6 '/' expr7
    | expr6 '%' expr7
    | expr7

expr7 ::= expr7 '^' expr8
    | expr8

expr8 ::= '-' expr8
    | 'NOT' expr8
    | expr9

expr9 ::= expr9 'INC'
    | expr9 'DEC'
    | group

group ::= '(' expr ')'
    | 'ID' '(' opt_expr_list ')'
    | 'ID' index
    | factor

index ::= '[' expr ']'

factor ::= 'ID'
    | 'INTEGER_LITERAL'
    | 'FLOAT_LITERAL'
    | 'CHAR_LITERAL'
    | 'STRING_LITERAL'
    | 'TRUE'
    | 'FALSE'

/* Types */

type_simple ::= 'INTEGER'
    | 'FLOAT'
    | 'BOOLEAN'
    | 'CHAR'
    | 'STRING'
    | 'VOID'

type_array ::= 'ARRAY' '[' ']' type_simple
    | 'ARRAY' '[' ']' type_array

type_array_sized ::= 'ARRAY' index type_simple
    | 'ARRAY' index type_array_sized

type_func ::= 'FUNCTION' type_simple '(' opt_param_list ')'
    | 'FUNCTION' type_array_sized '(' opt_param_list ')'

opt_param_list ::= /* epsilon */
    | param_list

param_list ::= param
    | param_list ',' param

param ::= 'ID' ':' type_simple
    | 'ID' ':' type_array
    | 'ID' ':' type_array_sized
```
