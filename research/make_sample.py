#!/usr/bin/env python3
"""Generate clearly synthetic session data for trying the analysis script."""

import csv
import random

GOALS = {
    "automation": ["wordcount", "pipeline"],
    "beginner": ["hello", "fizzbuzz"],
    "data": ["wordcount", "match"],
    "toolbuilder": ["class", "modules"],
    "concurrency": ["parallel", "errors"],
    "performance": ["native", "fizzbuzz"],
}

BASE_SUCCESS = {
    "automation": 0.84,
    "beginner": 0.82,
    "data": 0.79,
    "toolbuilder": 0.83,
    "concurrency": 0.73,
    "performance": 0.67,
}

BASE_TIME = {
    "hello": 120,
    "fizzbuzz": 260,
    "wordcount": 300,
    "pipeline": 360,
    "class": 420,
    "errors": 240,
    "match": 300,
    "modules": 360,
    "parallel": 520,
    "native": 620,
}

NOTES = [
    "used the examples menu",
    "asked what a map key could be",
    "forgot a semicolon twice",
    "liked the pipeline operator",
    "confused by the native backend subset",
    "read the error message and fixed it",
    "wanted to use a list index",
    "needed a hint on imports",
]

FIELDS = [
    "participant_id", "session_date", "age_band", "prior_experience", "goal",
    "task_id", "success", "time_seconds", "attempts", "friction",
    "confidence_before", "confidence_after", "notes",
]


def main():
    rng = random.Random(11)
    rows = []
    for goal, tasks in GOALS.items():
        for index in range(1, 5):
            participant = f"{goal[:3].upper()}-{index:02d}"
            prior = rng.randint(1, 5)
            before = rng.randint(1, 5)
            for task in tasks:
                chance = BASE_SUCCESS[goal] - 0.04 * (task in ("parallel", "native"))
                success = 1 if rng.random() < chance else 0
                time_seconds = int(BASE_TIME[task] * rng.uniform(0.6, 1.6))
                attempts = rng.randint(1, 4)
                friction = 0 if success and rng.random() > 0.18 else 1
                after = min(5, before + (1 if success else 0))
                note = rng.choice(NOTES) if rng.random() < 0.35 else ""
                rows.append({
                    "participant_id": participant,
                    "session_date": "2026-11-16",
                    "age_band": rng.choice(["13-15", "16-18"]),
                    "prior_experience": prior,
                    "goal": goal,
                    "task_id": task,
                    "success": success,
                    "time_seconds": time_seconds,
                    "attempts": attempts,
                    "friction": friction,
                    "confidence_before": before,
                    "confidence_after": after,
                    "notes": note,
                })
    with open("sample_sessions.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote sample_sessions.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
