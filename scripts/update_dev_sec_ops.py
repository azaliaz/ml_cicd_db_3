#!/usr/bin/env python3
"""
Обновляет dev_sec_ops.yml: последние 5 коммитов git, покрытие pytest-cov (если есть coverage.json).
Digest образа подставьте из вывода CI после docker push (docker inspect --format='{{index .RepoDigests 0}}').
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dev_sec_ops.yml"
COV_JSON = ROOT / "coverage.json"


def git_last_commits(n: int = 5) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", f"-{n}", "--pretty=%H"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[:n]


def coverage_percent() -> float | None:
    if not COV_JSON.is_file():
        return None
    data = json.loads(COV_JSON.read_text(encoding="utf-8"))
    tot = data.get("totals") or {}
    pct = tot.get("percent_covered")
    return float(pct) if pct is not None else None


def main() -> int:
    template = yaml.safe_load(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {}
    docker = (template or {}).get("docker") or {}
    commits = git_last_commits(5)
    if commits:
        template.setdefault("git", {})["last_five_commits"] = commits
    cov = coverage_percent()
    if cov is not None:
        template.setdefault("quality", {})["test_coverage_percent"] = round(cov, 2)
    template.setdefault("docker", docker)
    OUT.write_text(yaml.safe_dump(template, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Обновлён {OUT} (коммиты: {len(commits)}, coverage: {cov})")
    print("Подсказка: вставьте digest вручную в docker.digest после успешного push образа.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())