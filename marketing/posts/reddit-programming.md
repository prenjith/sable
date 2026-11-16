I built a small language called Sable and would like a critique

Sable is a dynamically typed scripting language with:
- a hand-written lexer and recursive-descent parser
- a static checker for optional type annotations
- a tree-walking interpreter
- a self-hosted core interpreter written in Sable
- a C bytecode VM for the core language

Features: classes, closures, pattern matching, pipelines, try/catch, modules,
and thread-based concurrency.

What I am unsure about:
- Does the syntax feel coherent, or like a pile of features?
- Are the error messages useful?
- Is the native VM worth continuing, or should the tree-walker stay the only
  runtime?

Playground: https://pranavrenjith2-source.github.io/sable-playground/
Source: https://github.com/prenjith/sable
