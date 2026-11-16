# Self-hosted Sable

`sable.sable` is a core interpreter for Sable written in Sable itself.

```
python3 sable.py selfhost/sable.sable examples/fizzbuzz.sable
```

## Supported

Numbers, strings, booleans, nil, `let`/`const`, `if`/`else`, `while`,
`for..in`, top-level functions, `return`/`break`/`continue`,
`print`/`str`/`num`/`len`/`range`, and comments.

## Not yet

Classes, `match`, `try`/`catch` in interpreted programs, modules, closures,
list and map literals, type annotations, and concurrency.

## Bootstrap

This is the first self-hosting milestone: the implementation is written in
Sable, but the first run still needs a seed interpreter. The seed is currently
the Python-hosted `sable.py` or a Nuitka native binary.

A fully independent build needs a native seed. That means extending the C
backend to lists, maps, closures, and errors, or writing a small native runtime
for the self-hosted interpreter.
