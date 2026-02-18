"""
CLI summary tool for FHE challenge RD-Agent runs.

Mirrors mle_summary.py but for FHE challenge scenarios.

Usage:
    rdagent fhe_summary --log-folder log/
    python rdagent/log/fhe_summary.py --log_folder log/
"""

from __future__ import annotations

import traceback
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import fire
import pandas as pd
import typer

from rdagent.core.proposal import ExperimentFeedback
from rdagent.log.storage import FileStorage
from rdagent.log.utils import extract_loopid_func_name, is_valid_session
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment
from rdagent.scenarios.fhe_challenge.proposal import FHEHypothesis


def summarize_fhe(
    log_folder: Annotated[str, typer.Option("--log-folder", "-l", help="Root log folder containing FHE run subdirectories")] = "log/",
) -> None:
    """
    Summarize FHE challenge run results from a log folder.

    Iterates all valid session subdirectories, reads pkl logs, and produces a
    per-run stat dict saved as ``fhe_summary.pkl`` in *log_folder*.

    Parameters
    ----------
    log_folder : str | Path
        Root log folder (contains one subdirectory per run).

    Returns
    -------
    dict
        Mapping of run-name → stats dict.
    """
    log_folder = Path(log_folder)
    stat: dict[str, dict] = defaultdict(dict)

    for log_trace_path in sorted(log_folder.iterdir()):
        if not is_valid_session(log_trace_path):
            continue

        try:
            run_stat = _summarize_one_run(log_trace_path)
            stat[log_trace_path.name] = run_stat
        except Exception:
            print(f"[fhe_summary] Error processing {log_trace_path}:")
            traceback.print_exc()

    # Print table to console
    _print_summary(stat)

    # Save
    save_path = log_folder / "fhe_summary.pkl"
    if save_path.exists():
        save_path.unlink()
    pd.to_pickle(stat, save_path)
    print(f"\nSummary saved → {save_path}")


def _summarize_one_run(log_trace_path: Path) -> dict:
    """Read all messages from one run and extract key metrics."""
    loop_num = 0
    pass_num = 0
    best_accuracy: float | None = None
    challenge_name: str | None = None
    challenge_type: str | None = None

    accuracies_by_loop: dict[int, float | None] = {}
    build_ok_by_loop: dict[int, bool] = {}
    run_ok_by_loop: dict[int, bool] = {}
    decisions_by_loop: dict[int, bool] = {}
    algorithms_by_loop: dict[int, str] = {}

    msgs = [
        (msg, extract_loopid_func_name(msg.tag))
        for msg in FileStorage(log_trace_path).iter_msg()
    ]
    msgs_parsed = [
        (msg, int(loop_id) if loop_id else None, fn)
        for msg, (loop_id, fn) in msgs
    ]

    for msg, loop_id, fn in msgs_parsed:
        if loop_id is not None:
            loop_num = max(loop_id + 1, loop_num)

        if not msg.tag:
            continue

        # Challenge name/type from settings
        if "FHE_SETTINGS" in msg.tag and isinstance(msg.content, dict):
            challenge_name = Path(msg.content.get("challenge_dir", "")).name or None
            challenge_type = msg.content.get("challenge_type", None)

        # Hypothesis (algorithm plan)
        if loop_id is not None and "direct_exp_gen" in msg.tag and "hypothesis" in msg.tag:
            if isinstance(msg.content, FHEHypothesis):
                algorithms_by_loop[loop_id] = msg.content.algorithm[:300]

        # Run results
        if loop_id is not None and "running" in msg.tag and "run_experiment" in msg.tag:
            if isinstance(msg.content, FHEExperiment):
                exp = msg.content
                accuracies_by_loop[loop_id] = exp.accuracy
                build_ok_by_loop[loop_id] = exp.build_success
                run_ok_by_loop[loop_id] = exp.run_success
                if exp.accuracy is not None:
                    if best_accuracy is None or exp.accuracy > best_accuracy:
                        best_accuracy = exp.accuracy

        # Feedback decisions
        if loop_id is not None and "feedback" in msg.tag and "evolving" not in msg.tag:
            if isinstance(msg.content, ExperimentFeedback):
                decisions_by_loop[loop_id] = msg.content.decision
                if msg.content.decision:
                    pass_num += 1

    return {
        "challenge_name": challenge_name or log_trace_path.name,
        "challenge_type": challenge_type or "unknown",
        "loop_num": loop_num,
        "pass_num": pass_num,
        "best_accuracy": best_accuracy,
        "accuracies_by_loop": accuracies_by_loop,
        "build_ok_by_loop": build_ok_by_loop,
        "run_ok_by_loop": run_ok_by_loop,
        "decisions_by_loop": decisions_by_loop,
        "algorithms_by_loop": algorithms_by_loop,
    }


def _print_summary(stat: dict) -> None:
    SEP = "=" * 70
    print(f"\n{SEP}")
    print("FHE CHALLENGE SUMMARY")
    print(SEP)
    for trace_name, s in stat.items():
        acc = s["best_accuracy"]
        acc_str = f"{acc:.4f} ({acc*100:.1f}%)" if acc is not None else "N/A"
        solved = "YES ✓" if s["pass_num"] > 0 else "NO ✗"
        print(f"\nRun:             {trace_name}")
        print(f"  Challenge:     {s['challenge_name']} ({s['challenge_type']})")
        print(f"  Total Loops:   {s['loop_num']}")
        print(f"  Passed Loops:  {s['pass_num']}  →  Solved: {solved}")
        print(f"  Best Accuracy: {acc_str}")
        build_counts = sum(1 for v in s["build_ok_by_loop"].values() if v)
        run_counts = sum(1 for v in s["run_ok_by_loop"].values() if v)
        print(f"  Build OK:      {build_counts}/{s['loop_num']} loops")
        print(f"  Run OK:        {run_counts}/{s['loop_num']} loops")
        acc_per_loop = ", ".join(
            f"L{k}:{v:.3f}" for k, v in sorted(s["accuracies_by_loop"].items()) if v is not None
        )
        print(f"  Acc/Loop:      {acc_per_loop or 'N/A'}")
    print(f"\n{SEP}")


if __name__ == "__main__":
    fire.Fire(summarize_fhe)
