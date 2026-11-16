#!/usr/bin/env python3
"""Turn Sable session rows into a short Markdown report."""

import argparse
import collections
import csv
import statistics


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("goal") or not row.get("task_id"):
                continue
            row["success"] = int(row.get("success") or 0)
            row["time_seconds"] = float(row.get("time_seconds") or 0)
            row["attempts"] = int(row.get("attempts") or 1)
            row["friction"] = int(row.get("friction") or 0)
            row["confidence_before"] = float(row.get("confidence_before") or 0)
            row["confidence_after"] = float(row.get("confidence_after") or 0)
            rows.append(row)
    return rows


def mean(values):
    return statistics.mean(values) if values else 0.0


def summarize(rows, key):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    lines = []
    for name in sorted(groups):
        group = groups[name]
        success = sum(row["success"] for row in group) / len(group)
        delta = mean([row["confidence_after"] - row["confidence_before"] for row in group])
        lines.append(
            f"| {name} | {len(group)} | {success * 100:.0f}% | "
            f"{mean([row['time_seconds'] for row in group]):.0f}s | "
            f"{mean([row['attempts'] for row in group]):.1f} | "
            f"{sum(row['friction'] for row in group) / len(group) * 100:.0f}% | "
            f"{delta:+.1f} |")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--out")
    args = parser.parse_args()
    rows = load(args.csv)
    if not rows:
        raise SystemExit("no session rows found")

    participants = {row["participant_id"] for row in rows}
    lines = [
        "# Sable user research report",
        "",
        f"- Participants: {len(participants)}",
        f"- Task rows: {len(rows)}",
        f"- Overall success: {sum(row['success'] for row in rows) / len(rows) * 100:.0f}%",
        f"- Mean time: {mean([row['time_seconds'] for row in rows]):.0f}s",
        f"- Friction rate: {sum(row['friction'] for row in rows) / len(rows) * 100:.0f}%",
        "",
        "## By goal",
        "",
        "| goal | rows | success | mean time | attempts | friction | confidence |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(summarize(rows, "goal"))
    lines += [
        "",
        "## By task",
        "",
        "| task | rows | success | mean time | attempts | friction | confidence |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(summarize(rows, "task_id"))
    notes = [row["notes"].strip() for row in rows if row.get("notes", "").strip()]
    if notes:
        lines += ["", "## Notes", ""]
        for note in collections.Counter(notes).most_common(8):
            lines.append(f"- {note[0]} ({note[1]})")
    lines += [
        "",
        "## Caveats",
        "",
        "This is a small, local sample. Treat it as a signal for the next round of",
        "interviews, not as a benchmark. Do not publish participant quotes without",
        "permission.",
    ]
    text = "\n".join(lines)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")


if __name__ == "__main__":
    main()
