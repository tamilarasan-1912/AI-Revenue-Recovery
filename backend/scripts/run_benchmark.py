import json
import os
from pathlib import Path

from app.simulation.evaluation import run_evaluation


def main() -> None:
    size = int(os.getenv("BENCHMARK_SIZE", "10000"))
    seed = int(os.getenv("BENCHMARK_SEED", "42"))
    result = run_evaluation(dataset_size=size, seed=seed)
    out = Path(os.getenv("BENCHMARK_OUTPUT", "benchmark-result.json"))
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
