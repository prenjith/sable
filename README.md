# Sable

Sable is a small dynamically typed scripting language. It is a tree-walking
interpreter written in Python with no third-party dependencies.

I built it to have a language that is comfortable for small scripts: C-like
syntax, first-class functions, lexical closures, lists, and string-keyed maps.

## Running

```
python3 sable.py examples/fizzbuzz.sable
python3 sable.py            # REPL
python3 sable.py --tokens examples/fib.sable
python3 sable.py --ast examples/fib.sable
```

Sable programs use the `.sable` extension. Statements end with semicolons.
Comments are `// line` and `/* block */`.

## A quick tour

```sable
let name = "world";
print("hello, " + name);

fn add(a, b) {
    return a + b;
}

let nums = [1, 2, 3];
let total = 0;
for n in nums {
    total = total + n;
}
print(total);

if total > 5 {
    print("big");
} else {
    print("small");
}
```

Functions are values and close over the scope where they were created:

```sable
fn counter() {
    let n = 0;
    fn next() {
        n = n + 1;
        return n;
    }
    return next;
}

let c = counter();
print(c());
print(c());
```

Maps use string keys:

```sable
let ages = {"ana": 15, "ben": 16};
ages["cara"] = 14;
print(ages["ana"]);
print(has(ages, "ben"));
for name in keys(ages) {
    print(name);
}
```

## Types

- `nil`
- `bool`: `true`, `false`
- `number`: all numbers are floats, printed without a trailing `.0` when whole
- `string`
- `list`
- `map` (string keys)
- functions and builtins

Truthiness: only `nil` and `false` are false. `0` and `""` are true.

## Operators

`+ - * / %` for numbers, `+` also concatenates strings and lists.

`== != < <= > >=` compare values. `and` and `or` short-circuit and return
one of their operands. `not` is a unary operator.

Assignment is `=`, with `+=`, `-=`, `*=`, and `/=` as shortcuts.

## Builtins

| Name | Description |
| --- | --- |
| `print(...)` | Write values to stdout |
| `len(x)` | Length of a string, list, or map |
| `str(x)` | Convert to a string |
| `num(x)` | Convert a string or number to a number |
| `type(x)` | Type name as a string |
| `range(a, b?, step?)` | List of numbers |
| `push(list, value)` | Append and return the list |
| `pop(list)` | Remove and return the last item |
| `keys(map)` | List of keys |
| `has(map, key)` | Check for a key |
| `input(prompt?)` | Read a line from stdin |
| `assert(cond, message?)` | Fail if the condition is false |
| `sort(list)` | Return a sorted copy |
| `upper(s)`, `lower(s)` | Change case |
| `join(list, sep)`, `split(s, sep)` | String/list conversion |

## Design

The implementation is in one file, `sable.py`:

1. The lexer turns source text into tokens, tracking line and column for errors.
2. The parser is a recursive-descent parser. Assignment is right-associative;
   binary operators use the usual precedence ladder. Function expressions and
   map literals are parsed in primary position.
3. The interpreter walks the AST with an environment chain. Blocks get a fresh
   environment, closures capture the environment where the function was made,
   and `return`/`break`/`continue` are implemented as signals.

Errors print the source line and a caret:

```
RuntimeError: undefined variable 'x'
  line 3: print(x);
  ^
```

## Limitations

- No modules or imports.
- Maps only accept string keys.
- No user-defined classes or methods.
- No garbage collector concerns (it is Python under the hood).
- `and`/`or` return operand values, not strict booleans.

## Tests

```
python3 -m unittest discover -s tests -v
```
