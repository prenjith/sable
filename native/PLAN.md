# Native independence plan

Goal: run Sable without Python.

## Milestones

1. **Core bytecode VM (done)**
   - `compiler.py` emits stack bytecode from the Sable AST
   - `vm.c` executes numbers, strings, booleans, nil, variables, arithmetic,
     comparisons, if/else, while, and print
2. **Functions, closures, lists, maps, for-in, runtime errors, try/catch**
3. **Classes, match, pipes, imports**
4. **Threads, checker integration, full self-host parity**
5. **Bootstrap**
   - compile `selfhost/sable.sable` with the native compiler
   - run it on the native VM
   - remove Python from the runtime

## Architecture

- The compiler is Python: it reuses `sable.parse` and emits a simple text
  bytecode (`PUSH_NUM`, `LOAD`, `JUMP`, ...).
- The VM is C: a stack machine with a single environment in milestone 1.
- Later milestones add parent-linked environments, heap objects (strings,
  lists, maps, closures), exception handling, classes, modules, and threads.

## Status

Milestone 1 is implemented and tested against the Python interpreter. The
remaining milestones are the work needed for full independence.
