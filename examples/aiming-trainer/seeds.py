"""Run the trainer across several seeds, because one run proves nothing.

The first version of this experiment reported a single column of numbers and they
were a coincidence of the seed. A measurement that cannot be repeated is an
anecdote, so this runs the same four stages several times with different worlds
and prints the spread.

    python seeds.py [--rounds 80] [--seeds 6] [--latency 3]
"""

from __future__ import annotations

import argparse
import statistics

import sim


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=80)
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--latency", type=int, default=3)
    args = parser.parse_args()

    per_stage: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}
    leads: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}
    improvement: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}

    for index in range(args.seeds):
        for stage in (1, 2, 3, 4):
            result = sim.run_stage(stage, args.rounds, seed=1000 + stage + index * 77, latency=args.latency)
            per_stage[stage].append(result["accuracy"])
            leads[stage].append(result["final_lead"])
            improvement[stage].append(result["last_third"] - result["first_third"])

    print(f"{args.seeds} worlds, {args.rounds} rounds each, latency {args.latency}")
    print(f"{'stage':<7}{'what it is':<34}{'accuracy':>10}{'worst':>8}{'best':>8}{'change':>9}{'lead':>8}")
    labels = {
        1: "static",
        2: "static, changes colour and shape",
        3: "moving",
        4: "moving, changes colour and shape",
    }
    for stage in (1, 2, 3, 4):
        values = per_stage[stage]
        print(
            f"{stage:<7}{labels[stage]:<34}"
            f"{statistics.mean(values):>10.3f}{min(values):>8.2f}{max(values):>8.2f}"
            f"{statistics.mean(improvement[stage]):>+9.3f}{statistics.mean(leads[stage]):>8.2f}"
        )
    print()
    print("change = last third minus first third. Positive means it got better as it went,")
    print("which is the only thing that separates learning from luck.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
