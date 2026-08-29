import json
import os
from pathlib import Path

from app.simulation.evaluation import run_multi_seed_evaluation


def main() -> None:
    size = int(os.getenv("BENCHMARK_SIZE", "10000"))
    raw_seeds = os.getenv("BENCHMARK_SEEDS", "42,123,456,789,2026")
    seeds = [int(value.strip()) for value in raw_seeds.split(",") if value.strip()]
    result = run_multi_seed_evaluation(dataset_size=size, seeds=seeds)

    aggregate = result["aggregate"]
    if aggregate["incremental_revenue_mean"] <= 0:
        raise SystemExit("Benchmark failed: mean incremental revenue is not positive.")
    if aggregate["recoverai_revenue_recovery_rate_mean"] < aggregate["baseline_revenue_recovery_rate_mean"]:
        raise SystemExit("Benchmark failed: RecoverAI recovery rate is below baseline.")

    out = Path(os.getenv("BENCHMARK_OUTPUT", "benchmark-result.json"))
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
