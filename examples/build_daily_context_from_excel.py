from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libsbapi.daily_context_builder import build_daily_context_records
from libsbapi.daily_context_io import write_daily_context_files, write_recommendation_log

DEFAULT_INPUT_DIR: Final = Path("/mnt/c/Users/연재성/Desktop/strawberry_kaggle_safe/core")
DEFAULT_CONTEXT_DIR: Final = Path("outputs/daily_contexts")
DEFAULT_LOG_PATH: Final = Path("outputs/recommendation_logs/daily_recommendations.jsonl")


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) >= 2 else DEFAULT_INPUT_DIR
    context_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_CONTEXT_DIR
    log_path = Path(sys.argv[3]) if len(sys.argv) >= 4 else DEFAULT_LOG_PATH

    records = build_daily_context_records(input_dir)
    context_paths = write_daily_context_files(records, context_dir)
    write_recommendation_log(records, log_path)

    print(f"input_dir={input_dir}")
    print(f"context_files={len(context_paths)} dir={context_dir}")
    print(f"recommendation_log={log_path}")


if __name__ == "__main__":
    main()
