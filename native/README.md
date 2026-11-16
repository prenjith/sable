# Native VM

A bytecode compiler and C virtual machine for the core of Sable.

```
python3 native/compiler.py examples/fizzbuzz.sable -o /tmp/fizzbuzz.sasm
cc -O2 -o native/sable-vm native/vm.c -lm
./native/sable-vm /tmp/fizzbuzz.sasm
```

## Supported

Numbers, strings, booleans, nil, variables, arithmetic, comparisons, if/else,
while, and `print`.

## Not yet

Functions, closures, lists, maps, classes, errors, modules, and threads. See
`PLAN.md` for the milestones to full independence.

## Tests

`tests/test_native_vm.py` compiles the VM and compares its output with the
Python interpreter for the core programs.
