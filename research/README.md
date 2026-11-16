# Sable user research kit

This folder is for running real, ethical user research with Hack Club members.
It replaces the toy simulation with a repeatable study: a short session, clear
tasks, consent and assent, and a simple analysis script.

## What you get

- `protocol.md` — how to run a 25-minute session
- `tasks.md` — task cards for different goals
- `consent.md` — guardian consent and participant assent templates
- `survey.md` — pre/post questions
- `observation.md` — observer rubric
- `sessions_template.csv` — the data format
- `analysis.py` — turns session rows into a report
- `sample_sessions.csv` — synthetic data so you can try the analysis

## Before you run anything

1. Read `consent.md`. Participants under 18 need guardian consent and their own
   assent.
2. Use anonymous participant IDs. Do not collect names in the CSV.
3. Keep data local. Share only aggregate results, and only with permission.
4. Make it clear this is a test of the language, not of the kid.

## A 25-minute session

1. Consent and assent (5 min).
2. Warm-up in the browser playground (5 min).
3. Two or three task cards (12 min).
4. Short survey and interview (3 min).

Use the playground at
https://pranavrenjith2-source.github.io/sable-playground/ so nothing needs to
be installed.

## Analysis

```
python3 research/analysis.py research/sample_sessions.csv
python3 research/analysis.py research/sessions.csv --out report.md
```

The report shows success rate, time, attempts, friction, and confidence change
by goal and by task. Compare real sessions against the sample data, not against
the toy simulation.
