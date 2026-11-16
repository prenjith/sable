# Bot learning simulation

This is a toy model, not user research. It asks a simple question: if bots with
different goals try to build things in Sable, which goal does the language fit
best?

Each bot has a skill level and attempts tasks that match its goal. Success
depends on skill, task difficulty, and how well the language's features fit the
task. The `support` field encodes current limitations, such as the native
backend covering only the core language and threads lacking synchronization.

Run it with:

```
python3 tools/simulate_bots.py
```

## Results (seed 7, 400 bots per persona)

| persona | success | avg time | friction | score |
| --- | ---: | ---: | ---: | ---: |
| automation | 84.0% | 19.5 | 0.0% | 4.316 |
| beginner | 81.5% | 20.2 | 0.0% | 4.039 |
| data | 79.3% | 22.0 | 0.0% | 3.601 |
| toolbuilder | 83.1% | 24.1 | 0.0% | 3.442 |
| concurrency | 73.2% | 29.6 | 33.3% | 2.468 |
| performance | 66.8% | 44.3 | 33.3% | 1.508 |

Across 20 seeds, **automation won every time**, with **beginner** consistently
second. Performance and concurrency trail because the native backend covers
only the core language and threads have no synchronization primitives.

## Primary goal

The simulation points to **small automation and scripting** as Sable's primary
goal, with **learning** a close second. The language is built to get a useful
program written quickly: short syntax, built-in collections, pattern matching,
errors, modules, and a REPL. It is not primarily a systems or performance
language, and the simulation shows that friction clearly.
