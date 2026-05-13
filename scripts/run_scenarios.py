"""
Прогон сценариев из scenario.json против уже запущенного API (например, контейнер после CD).
Пример: SCENARIO_BASE_URL=http://127.0.0.1:8000 python scripts/run_scenarios.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


def _deep_subset(actual: Any, expected: dict) -> bool:
    if not isinstance(actual, dict):
        return False
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, dict) and isinstance(actual[k], dict):
            if not _deep_subset(actual[k], v):
                return False
        elif actual[k] != v:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Запуск сценариев из scenario.json")
    parser.add_argument(
        "--scenario-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "scenario.json",
    )
    parser.add_argument("--base-url", default=os.environ.get("SCENARIO_BASE_URL"))
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    data = json.loads(args.scenario_file.read_text(encoding="utf-8"))
    base = (args.base_url or data.get("default_base_url") or "").rstrip("/")
    if not base:
        print("Укажите --base-url или SCENARIO_BASE_URL", file=sys.stderr)
        return 2

    scenarios = data.get("scenarios") or []
    failed = 0
    results: list[dict[str, Any]] = []
    with httpx.Client(base_url=base, timeout=60.0) as client:
        for sc in scenarios:
            sid = sc.get("id", "?")
            req = sc["request"]
            method = req["method"].upper()
            path = req["path"]
            headers = req.get("headers")
            body = req.get("json")
            try:
                r = client.request(method, path, headers=headers, json=body)
            except httpx.RequestError as e:
                print(f"FAIL {sid}: {e}")
                failed += 1
                results.append({"id": sid, "status": "fail", "reason": str(e)})
                continue
            exp = sc.get("expect") or {}
            want_status = exp.get("status")
            if want_status is not None and r.status_code != want_status:
                print(f"FAIL {sid}: status {r.status_code} != {want_status}: {r.text[:500]}")
                failed += 1
                results.append({"id": sid, "status": "fail", "reason": f"status {r.status_code} != {want_status}"})
                continue
            if "json" in exp:
                try:
                    payload = r.json()
                except json.JSONDecodeError:
                    print(f"FAIL {sid}: ответ не JSON: {r.text[:500]}")
                    failed += 1
                    results.append({"id": sid, "status": "fail", "reason": "response is not JSON"})
                    continue
                if not _deep_subset(payload, exp["json"]):
                    print(f"FAIL {sid}: JSON не совпал. Ожидалось {exp['json']}, получено {payload}")
                    failed += 1
                    results.append({"id": sid, "status": "fail", "reason": "json mismatch"})
                    continue
            if "json_keys" in exp:
                try:
                    payload = r.json()
                except json.JSONDecodeError:
                    print(f"FAIL {sid}: ответ не JSON: {r.text[:500]}")
                    failed += 1
                    results.append({"id": sid, "status": "fail", "reason": "response is not JSON"})
                    continue
                bad = False
                for key in exp["json_keys"]:
                    if key not in payload:
                        print(f"FAIL {sid}: нет ключа {key} в {payload}")
                        failed += 1
                        results.append({"id": sid, "status": "fail", "reason": f"missing key {key}"})
                        bad = True
                        break
                if bad:
                    continue
            print(f"OK   {sid}")
            results.append({"id": sid, "status": "ok"})
    if args.report_json is not None:
        report = {
            "base_url": base,
            "total": len(scenarios),
            "failed": failed,
            "passed": len(scenarios) - failed,
            "results": results,
        }
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())