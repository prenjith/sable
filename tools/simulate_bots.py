#!/usr/bin/env python3
"""A toy simulation of bots learning Sable with different goals.

This is not user research. It is a small model of how well the language's
features fit different kinds of work.
"""

import random

TASKS = {
    "hello":      {"features": ["print"], "difficulty": 1, "base_time": 4, "support": 1.0},
    "fizzbuzz":   {"features": ["loops", "conditionals"], "difficulty": 2, "base_time": 8, "support": 1.0},
    "wordcount":  {"features": ["strings", "maps", "loops"], "difficulty": 2, "base_time": 10, "support": 1.0},
    "pipeline":   {"features": ["higher_order", "pipes", "lists"], "difficulty": 3, "base_time": 12, "support": 1.0},
    "closure":    {"features": ["closures"], "difficulty": 3, "base_time": 10, "support": 1.0},
    "class":      {"features": ["classes"], "difficulty": 3, "base_time": 14, "support": 1.0},
    "errors":     {"features": ["errors"], "difficulty": 2, "base_time": 9, "support": 1.0},
    "match":      {"features": ["match"], "difficulty": 3, "base_time": 11, "support": 1.0},
    "modules":    {"features": ["modules"], "difficulty": 3, "base_time": 13, "support": 1.0},
    "parallel":   {"features": ["concurrency"], "difficulty": 4, "base_time": 18, "support": 0.75},
    "native":     {"features": ["native", "functions"], "difficulty": 5, "base_time": 26, "support": 0.5},
}

PERSONAS = {
    "beginner": {
        "tasks": ["hello", "fizzbuzz", "closure", "class", "match"],
        "affinity": {
            "print": 0.95, "loops": 0.9, "conditionals": 0.9, "closures": 0.55,
            "classes": 0.7, "errors": 0.6, "match": 0.65, "strings": 0.8,
            "maps": 0.7, "lists": 0.8, "higher_order": 0.5, "pipes": 0.5,
            "modules": 0.4, "concurrency": 0.25, "native": 0.2, "functions": 0.7,
        },
    },
    "automation": {
        "tasks": ["hello", "wordcount", "pipeline", "modules", "errors"],
        "affinity": {
            "print": 0.9, "loops": 0.9, "conditionals": 0.85, "strings": 0.95,
            "maps": 0.9, "lists": 0.85, "higher_order": 0.8, "pipes": 0.75,
            "errors": 0.85, "modules": 0.8, "match": 0.6, "closures": 0.5,
            "classes": 0.4, "concurrency": 0.5, "native": 0.35, "functions": 0.8,
        },
    },
    "data": {
        "tasks": ["wordcount", "pipeline", "match", "errors"],
        "affinity": {
            "strings": 0.9, "maps": 0.95, "lists": 0.95, "higher_order": 0.95,
            "pipes": 0.9, "loops": 0.85, "conditionals": 0.8, "print": 0.8,
            "match": 0.7, "closures": 0.6, "errors": 0.6, "modules": 0.6,
            "classes": 0.4, "concurrency": 0.4, "native": 0.3, "functions": 0.7,
        },
    },
    "toolbuilder": {
        "tasks": ["modules", "class", "errors", "match"],
        "affinity": {
            "modules": 0.95, "classes": 0.95, "errors": 0.9, "match": 0.8,
            "closures": 0.7, "print": 0.8, "loops": 0.7, "conditionals": 0.7,
            "strings": 0.7, "maps": 0.7, "lists": 0.7, "higher_order": 0.6,
            "pipes": 0.6, "concurrency": 0.5, "native": 0.6, "functions": 0.8,
        },
    },
    "concurrency": {
        "tasks": ["parallel", "errors", "closure"],
        "affinity": {
            "concurrency": 0.95, "errors": 0.8, "closures": 0.7, "loops": 0.7,
            "conditionals": 0.7, "print": 0.7, "lists": 0.6, "maps": 0.5,
            "strings": 0.5, "match": 0.5, "modules": 0.5, "classes": 0.4,
            "higher_order": 0.5, "pipes": 0.4, "native": 0.4, "functions": 0.6,
        },
    },
    "performance": {
        "tasks": ["native", "fizzbuzz", "closure"],
        "affinity": {
            "native": 0.95, "loops": 0.9, "conditionals": 0.8, "print": 0.8,
            "functions": 0.6, "closures": 0.6, "classes": 0.5, "modules": 0.5,
            "errors": 0.5, "match": 0.5, "lists": 0.5, "maps": 0.4,
            "strings": 0.4, "higher_order": 0.4, "pipes": 0.3, "concurrency": 0.4,
        },
    },
}


def clamp(value, low, high):
    return max(low, min(high, value))


def simulate(seed=7, bots_per_persona=400):
    rng = random.Random(seed)
    results = {}
    for persona, config in PERSONAS.items():
        successes = 0
        total_time = 0.0
        friction = 0
        total = 0
        for _ in range(bots_per_persona):
            skill = clamp(rng.gauss(0.65, 0.15), 0.2, 0.95)
            for task_name in config["tasks"]:
                task = TASKS[task_name]
                fit = sum(config["affinity"].get(f, 0.3) for f in task["features"]) / len(task["features"])
                chance = clamp(
                    skill * (0.55 + 0.45 * fit) * (1.05 - 0.12 * task["difficulty"]) * task["support"],
                    0.02, 0.98)
                cost = (task["base_time"] * (1 + 0.25 * task["difficulty"])
                        * (1.5 - skill) * (1.15 - 0.25 * fit))
                spent = 0.0
                done = False
                for attempt in range(1, 4):
                    spent += cost * (0.6 if attempt > 1 else 1.0)
                    if rng.random() < chance:
                        done = True
                        break
                total += 1
                if done:
                    successes += 1
                total_time += spent
                if fit < 0.5 or task["difficulty"] >= 4:
                    friction += 1
        rate = successes / total
        average = total_time / total
        results[persona] = {
            "success": rate,
            "time": average,
            "friction": friction / total,
            "score": rate / average * 100,
        }
    return results


def main():
    results = simulate()
    print("persona        success   avg_min   friction   score")
    print("---------------------------------------------------")
    for persona, data in sorted(results.items(), key=lambda item: -item[1]["score"]):
        print(f"{persona:14} {data['success']*100:6.1f}% {data['time']:8.1f} "
              f"{data['friction']*100:9.1f}% {data['score']:8.3f}")
    winner = max(results, key=lambda name: results[name]["score"])
    print()
    print(f"primary goal by score: {winner}")


if __name__ == "__main__":
    main()
