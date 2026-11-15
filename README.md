<p align="center">
  <img src="logo.svg" width="96" alt="Sable logo">
</p>

<h1 align="center">Sable</h1>

<p align="center">
  A small scripting language with closures, pattern matching, error handling,
  and a pipeline operator.
</p>

<p align="center">
  <a href="docs/index.html">Language reference</a>
</p>

Sable is a tree-walking interpreter written in Python with no third-party
dependencies. It is meant for small scripts, experiments, and learning how a
language fits together.

## Features

- C-like syntax with semicolon-terminated statements
- `let` and `const` declarations with block scoping
- First-class functions, anonymous functions, and lexical closures
- Lists, string-keyed maps, and `map.key` dot access
- `if` / `else`, `while`, and `for ... in`
- `match` statements with literal, wildcard, and binding patterns
- `try` / `catch` / `throw`
- `|>` pipelines
- A standard library for math, strings, and collections
- REPL, file runner, token dumper, and AST dumper
- Errors with line and column information

## Running

```
python3 sable.py examples/fizzbuzz.sable
python3 sable.py examples/fib.sable
python3 sable.py            # REPL
python3 sable.py --tokens examples/fib.sable
python3 sable.py --ast examples/fib.sable
```

Sable programs use the `.sable` extension. Comments are `// line` and
`/* block */`.

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
```

Functions close over the scope where they were created:

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

Maps use string keys and support dot access:

```sable
let user = {"name": "ana", "age": 15};
print(user.name);
user.age = user.age + 1;
print(user.age);
```

`const` values cannot be reassigned:

```sable
const limit = 10;
limit = 20;   // RuntimeError: cannot assign to constant 'limit'
```

`match` picks the first arm that fits:

```sable
fn describe(n) {
    match n {
        1 => return "one";
        2 => return "two";
        _ => return "many";
    }
}
```

Errors can be thrown and caught:

```sable
try {
    if b == 0 {
        throw "cannot divide by zero";
    }
    print(a / b);
} catch err {
    print("error: " + str(err));
}
```

Runtime errors arrive as maps with `message` and `line` fields. Thrown values
are passed through unchanged.

Pipelines pass a value into a function:

```sable
let result = nums
    |> filter(is_even)
    |> map(square);

print(result);
```

`value |> f` calls `f(value)`. If the right side is a call, the value becomes
the first argument: `value |> f(x)` is `f(value, x)`.

## Types

- `nil`
- `bool`: `true`, `false`
- `number`: all numbers are floats, printed without a trailing `.0` when whole
- `string`
- `list`
- `map` (string keys)
- functions and builtins

Only `nil` and `false` are false. `0` and `""` are true.

## Operators

`+ - * / %` work on numbers; `+` also concatenates strings and lists.

`== != < <= > >=` compare values. `and` and `or` short-circuit and return one
of their operands. `not` is a unary operator.

Assignment is `=`, with `+=`, `-=`, `*=`, and `/=` as shortcuts.

## Builtins

| Name | Description |
| --- | --- |
| `print(...)` | Write values to stdout |
| `len(x)` | Length of a string, list, or map |
| `str(x)`, `num(x)`, `type(x)` | Conversions and type names |
| `range(a, b?, step?)` | List of numbers |
| `push(list, value)`, `pop(list)` | List mutation |
| `keys(map)`, `has(map, key)` | Map helpers |
| `map(list, fn)`, `filter(list, fn)`, `reduce(list, fn, initial?)` | Higher-order list operations |
| `sort(list, comparator?)` | Sorted copy, optionally with a comparator |
| `sum(list)`, `min(...)`, `max(...)`, `abs(n)` | Numeric helpers |
| `floor(n)`, `ceil(n)`, `round(n)`, `sqrt(n)`, `pow(a, b)` | Math helpers |
| `contains(x, value)`, `index_of(x, value)`, `slice(x, start, end?)` | Search and slicing |
| `replace(s, old, new)`, `trim(s)`, `starts_with(s, p)`, `ends_with(s, s2)` | String helpers |
| `join(list, sep)`, `split(s, sep)`, `upper(s)`, `lower(s)` | String conversion |
| `input(prompt?)`, `assert(cond, message?)` | Input and checks |

## Project layout

```
sable.py                 interpreter, parser, lexer, and CLI
examples/                sample programs
tests/                   unittest suite
docs/index.html          language reference page
editors/vscode/          syntax highlighting extension
```

## Development

```
python3 -m unittest discover -s tests -v
```

The interpreter is a single file. The lexer produces tokens with line and
column positions, the parser builds an AST with recursive descent, and the
interpreter evaluates that AST against a chain of environments. Closures
capture their defining environment, and `return`, `break`, and `continue` are
control-flow signals.

## Limitations

- No modules or imports.
- Maps only accept string keys.
- No user-defined classes or methods.
- No garbage collector concerns (it is Python under the hood).
- `and` / `or` return operand values, not strict booleans.

## License

MIT. See `LICENSE`.
