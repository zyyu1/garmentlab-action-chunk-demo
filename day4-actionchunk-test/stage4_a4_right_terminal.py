"""A4 offline analysis of 20 independently seeded right/single development runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from stage4_success_v1 import config, geometry, identity


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(path, key):
    with np.load(path, allow_pickle=False) as data:
        return data[key]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.results.resolve()
    historical = root / "TASK_B_RIGHT_DEV_V1_20261102-183740"
    serial = root / "A2_A3_SERIAL_20261103T045022Z"
    state = serial / "stage4-b-right-dev-v2-dev-v2"
    selected = {4200: historical / "day4-recovery-fold-20261103-023749-213160",
                4300: historical / "day4-recovery-fold-20261103-031351-818421"}
    attempts = [json.loads(line) for line in (state / "attempts.jsonl").read_text().splitlines()]
    assert [a["seed"] for a in attempts] == list(range(4201, 4210)) + list(range(4301, 4310))
    selected.update({a["seed"]: serial / Path(a["result_dir"]).name for a in attempts})
    evaluator = identity()
    base = read(serial / "square-recovery-fold-files.json")
    assert len(base) == 21
    rows = []
    for seed, directory in sorted(selected.items()):
        result = read(directory / "result.json")
        level = "perturbed" if seed < 4300 else "crumpled"
        assert (result["initial_case"]["seed"], result["initial_case"]["level"],
                result["fold_edge"], result["execution_mode"]) == (seed, level, "right", "single")
        assert result["code_files"] == base
        assert not (directory / "success_trace.npz").exists()
        evidence = {"result.json": sha(directory / "result.json")}
        row = {"seed": seed, "level": level, "directory": str(directory),
               "variant": "v1" if seed in (4200, 4300) else "v2.1",
               "development_pass": result["passed"], "errors": result["errors"],
               "evidence_sha256": evidence, "formal_success": None, "trace_frames_available": False}
        if (directory / "final.npz").exists():
            assert result["action_count"] == 12 and sum(result["call_horizons"]) == 12
            variant = read(directory / "variant_identity.json")
            tag = "v1" if seed in (4200, 4300) else "v2"
            frozen = historical if tag == "v1" else serial
            assert variant["code_files"] == read(frozen / f"square-recovery-fold-right-{tag}-files.json")
            assert variant["config"] == read(frozen / f"stage4-b-right-dev-{tag}.json")
            assert variant["config"]["fold_width_m"] == .2 and variant["config"]["overhang_m"] == 0
            evidence.update({name: sha(directory / name) for name in
                             ("variant_identity.json", "recovered.npz", "final.npz", "cloth_constructed.npz")})
            g = geometry(vertices(directory / "recovered.npz", "vertices"),
                         vertices(directory / "final.npz", "vertices"),
                         vertices(directory / "cloth_constructed.npz", "points"),
                         result["fold_metrics"]["pick_index"], result["fold_yaw"], "right", "B_nominal", 0.)
            row.update(quality_pass=g["geometry_pass"], metrics=g["metrics"], checks=g["checks"],
                       failed_checks=[k for k,v in g["checks"].items() if not v],
                       status="quality_pass" if g["geometry_pass"] else "quality_rejected")
        else:
            assert seed in (4301, 4309) and not result["passed"] and result["errors"]
            row.update(quality_pass=None, status="execution_error", failed_checks=[])
        rows.append(row)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"evaluator_version": config()["version"], "evaluator_manifest": evaluator,
              "criterion": "geometry(B_nominal), recovered -> final, floor_z=0 m",
              "selection": "4200/4300 single selected in v1 primary review, plus all 18 serial ledger entries",
              "rows": rows}
    (args.output / "terminal-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),encoding="utf-8")
    with (args.output / "seeds.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["seed","level","variant","development_pass","quality_pass","status","failed_checks","errors","directory"]
        writer = csv.DictWriter(f, fields); writer.writeheader()
        for r in rows:
            writer.writerow({k: " | ".join(r[k]) if k in ("errors","failed_checks") else r[k] for k in fields})
            print(r["seed"], r["development_pass"], r["status"], ",".join(r["failed_checks"]))


if __name__ == "__main__":
    main()
