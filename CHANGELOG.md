# Changelog

## 0.3.0 — 2026-11-15

- Optional type annotations and a static checker (`--check`)
- `import` statements with module caching
- Maps accept strings, numbers, booleans, and nil as keys
- `stdlib/result.sable` and `stdlib/option.sable`
- New examples for types, modules, results, and options

## 0.2.0 — 2026-11-15

- Map dot access (`user.name`, `user.age += 1`)
- `const` declarations
- `try` / `catch` / `throw`
- `match` statements with literal, wildcard, and binding patterns
- `|>` pipeline operator, including piping into calls
- Standard library additions: `map`, `filter`, `reduce`, `sum`, `min`, `max`,
  `abs`, `floor`, `ceil`, `round`, `sqrt`, `pow`, `contains`, `index_of`,
  `slice`, `replace`, `trim`, `starts_with`, `ends_with`
- Optional comparator for `sort`
- Documentation site and VS Code syntax highlighting

## 0.1.0 — 2026-11-13

- Initial release: lexer, parser, tree-walking interpreter, environments,
  closures, lists, maps, builtins, REPL, and tests
