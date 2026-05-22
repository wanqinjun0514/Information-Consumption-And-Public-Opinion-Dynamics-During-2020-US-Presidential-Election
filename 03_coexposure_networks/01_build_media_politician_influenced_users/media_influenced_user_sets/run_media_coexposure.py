"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

_rp = Path(__file__).resolve()
for _ in range(10):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent

from media_step01_extract_retweet_domain_bias import run_step1
from media_step02_build_influenced_user_sets import run_step2
from media_step03_pairwise_common_users import run_step3


def main() -> None:
    run_step1()
    run_step2()
    run_step3()


if __name__ == "__main__":
    main()
