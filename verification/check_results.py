# Checks equilibrium-box fields and DIG logs against reference_results.json.

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

# Fluent cell fields use IDs 700 for density, 701 for velocity, and 702 for both temperatures.
FIELD_PATTERN = re.compile(r"\(300\s+\((\d+)\s+(\d+)\s+(\d+)\s+0\s+0\s+(\d+)\s+(\d+)\)\s*\((.*?)\)\)", re.S)
FILE_PATTERN = re.compile(r"DSMCKn([0-9.]+)_iter(\d+)_CELL(\d+)\.dat$")
REQUIRED_WIDTHS = {700: 1, 701: 3, 702: 2, 710: 6, 711: 3, 712: 3}


# Accept only complete finite cell fields before computing statistics.
def load_fields(path, expected_cells=512):
    fields = {}
    for match in FIELD_PATTERN.finditer(Path(path).read_text(encoding="utf-8")):
        field, zone, width, first, last = map(int, match.groups()[:5])
        if field in fields:
            raise ValueError(f"Duplicate field {field}")
        rows = [[float(x) for x in line.split()] for line in match.group(6).splitlines() if line.strip()]
        if zone != 2 or first != 1 or last != expected_cells or len(rows) != expected_cells:
            raise ValueError(f"Invalid cell range or count for field {field}")
        if any(len(row) != width for row in rows):
            raise ValueError(f"Invalid component count for field {field}")
        if any(not math.isfinite(x) for row in rows for x in row):
            raise ValueError(f"Non-finite value in field {field}")
        fields[field] = rows
    if set(fields) != set(REQUIRED_WIDTHS):
        raise ValueError("Expected fields 700, 701, 702, 710, 711 and 712")
    if any(len(fields[k][0]) != width for k, width in REQUIRED_WIDTHS.items()):
        raise ValueError("Unexpected field dimensions")
    return fields


# Equal cell volumes make arithmetic means equivalent to volume-weighted means.
def summarize_fields(fields, temperature_K=273.15):
    mean = lambda values: math.fsum(values) / len(values)
    rho = [row[0] for row in fields[700]]
    tt = [row[0] for row in fields[702]]
    tr = [row[1] for row in fields[702]]
    velocity = fields[701]
    rms_error = lambda values: math.sqrt(mean([(x - 1.0) ** 2 for x in values]))
    result = {
        "cells": len(rho),
        "rho_mean": mean(rho),
        "Tt_mean": mean(tt),
        "Tr_mean": mean(tr),
        "rho_rms_error": rms_error(rho),
        "Tt_rms_error": rms_error(tt),
        "Tr_rms_error": rms_error(tr),
        "velocity_rms": math.sqrt(mean([math.fsum(x * x for x in row) for row in velocity])),
        "nonpositive_rho_or_T": sum(x <= 0 for values in (rho, tt, tr) for x in values),
        "nonfinite_values": 0,
        "rho_range": [min(rho), max(rho)],
        "Tt_range": [min(tt), max(tt)],
        "Tr_range": [min(tr), max(tr)],
    }
    for j, name in enumerate(("u_mean_x", "u_mean_y", "u_mean_z")):
        result[name] = mean([row[j] for row in velocity])
    # Convert normalized temperatures to kelvin using the case reference temperature.
    result["Tt_mean_K"] = result["Tt_mean"] * temperature_K
    result["Tr_mean_K"] = result["Tr_mean"] * temperature_K
    return result


def summarize_file(path, expected_cells=512, temperature_K=273.15):
    return summarize_fields(load_fields(path, expected_cells), temperature_K)


def resolve_input(path, reference):
    path = Path(path)
    if path.is_file():
        return path
    folder = path / "statisticResults" if (path / "statisticResults").is_dir() else path
    config = reference["configuration"]
    return folder / f"DSMCKn{config['kn']:.3f}_iter{config['total_dsmc_steps']}_CELL{config['cells']}.dat"


# Each completed DIG block must include NS, high-order, and particle-feedback evidence.
def coupling_cycles(log_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="replace").replace("\r", "")
    cycles = []
    pattern = r"The macroscopic equations are solving after (\d+) DSMC steps(.*?)The macroscopic acceleration is done after \1 DSMC steps"
    for match in re.finditer(pattern, text, re.S):
        block = match.group(2)
        residuals = re.findall(r"ns : iter = (\d+), Error = ([\deE+.-]+)", block)
        feedback = re.search(r"GSIS_NS2DSMC_ACCEPT_SUM ready=1 total=(\d+) accepted=(\d+) rejected=(\d+)", block)
        high_order = re.search(r"HIGH_ORDER_DAMP accepted=(\d+)", block)
        rejected_kn = re.search(r"GSIS_COUPLING[^\n]*knRejected=(\d+)", block)
        if rejected_kn is None:
            rejected_kn = re.search(r"knCellUpperBoundsReject=(\d+)", block)
        if not residuals or not feedback or not high_order or not rejected_kn:
            raise ValueError(f"Incomplete coupling evidence at step {match.group(1)}")
        cycles.append({
            "step": int(match.group(1)),
            "ns_iterations": int(residuals[-1][0]),
            "ns_residual": float(residuals[-1][1]),
            "total_cells": int(feedback.group(1)),
            "accepted_cells": int(feedback.group(2)),
            "rejected_cells": int(feedback.group(3)),
            "high_order_accepted_cells": int(high_order.group(1)),
            "kn_rejected_cells": int(rejected_kn.group(1)),
        })
    return cycles, text


# A run passes only when its numerical results and coupling evidence satisfy the reference.
def evaluate(path, reference, log_path=None, mesh_path=None):
    path = resolve_input(path, reference)
    config = reference["configuration"]
    match = FILE_PATTERN.fullmatch(path.name)
    if not match or not math.isclose(float(match.group(1)), config["kn"], abs_tol=1e-12) or int(match.group(2)) != config["total_dsmc_steps"] or int(match.group(3)) != config["cells"]:
        raise ValueError("Input filename does not match the reference case")
    metrics = summarize_file(path, config["cells"], config["temperature_K"])
    checks = [{"name": "positive_density_and_temperatures", "passed": metrics["nonpositive_rho_or_T"] == 0}]
    for name, bounds in reference["acceptance"]["metrics"].items():
        value = metrics[name]
        checks.append({"name": name, "value": value, "lower": bounds["lower"], "upper": bounds["upper"], "passed": bounds["lower"] <= value <= bounds["upper"]})
    if log_path is None:
        log_path = path.parent.parent / "run.log"
    cycles, text = coupling_cycles(log_path)
    expected_steps = list(range(config["dsmc_interval"], config["total_dsmc_steps"] + 1, config["dsmc_interval"]))
    checks.append({"name": "coupling_steps", "passed": [c["step"] for c in cycles] == expected_steps})
    checks.append({"name": "all_cells_receive_feedback", "passed": all(c["total_cells"] == config["cells"] and c["accepted_cells"] == config["cells"] and c["rejected_cells"] == 0 and c["high_order_accepted_cells"] == config["cells"] and c["kn_rejected_cells"] == 0 for c in cycles)})
    checks.append({"name": "finite_ns_iterations_within_limit", "passed": all(0 < c["ns_iterations"] <= config["ns_max_iterations"] and math.isfinite(c["ns_residual"]) for c in cycles)})
    checks.append({"name": "completed_dsmc_steps", "passed": f"Finished {config['total_dsmc_steps']} of {config['total_dsmc_steps']} steps." in text and "Total running time =" in text})
    metadata = re.search(r"Random seed: (\d+), MPI ranks: (\d+)", text)
    checks.append({"name": "tested_world_size", "passed": metadata is not None and int(metadata.group(2)) in config["validated_world_ranks"]})
    checks.append({"name": "fixed_seed", "passed": metadata is not None and int(metadata.group(1)) == config["default_seed"]})
    filter_settings = re.findall(r"GSIS_COUPLING[^\n]*knCellUpperBound=(\d+)", text)
    if not filter_settings:
        filter_settings = re.findall(r"GSIS_COUPLE_FILTER_SUM[^\n]*knCellUpperBound=(\d+)", text)
    expected_filter = int(config["kn_cell_upper_bound_enabled"])
    checks.append({"name": "kn_filter_configuration", "passed": len(filter_settings) == len(expected_steps) and all(int(value) == expected_filter for value in filter_settings)})
    mesh_path = Path(mesh_path) if mesh_path else Path(__file__).resolve().parent.parent / "mesh" / "cavity_512.cas"
    mesh_hash = hashlib.sha256(mesh_path.read_bytes()).hexdigest()
    checks.append({"name": "mesh_sha256", "passed": mesh_hash == reference["mesh_sha256"]})
    return {"input": str(path), "log": str(log_path), "seed": int(metadata.group(1)) if metadata else None, "metrics": metrics, "checks": checks, "passed": all(check["passed"] for check in checks), "coupling_cycles": cycles, "all_ns_solves_reached_1e_minus_6": bool(cycles) and all(c["ns_residual"] <= 1e-6 for c in cycles), "scope": reference["validation_scope"]}


# Exit codes distinguish passing checks, failed checks, and invalid inputs as 0, 1, and 2.
def main():
    parser = argparse.ArgumentParser(description="Check the fixed equilibrium-box reference and statistical acceptance bands.")
    parser.add_argument("--input", required=True, type=Path, help="Run directory, statisticResults directory, or final Fluent DAT file")
    parser.add_argument("--reference", type=Path, default=Path(__file__).resolve().with_name("reference_results.json"))
    parser.add_argument("--log", type=Path, help="MPI log; defaults to run.log beside statisticResults")
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        result = evaluate(args.input, reference, args.log, args.mesh)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.json_out:
            args.json_out.write_text(output + "\n", encoding="utf-8")
        print(output)
        return 0 if result["passed"] else 1
    except (OSError, ValueError, KeyError) as error:
        print(f"CHECK_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
