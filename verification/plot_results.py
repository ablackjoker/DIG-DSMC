# Plots final equilibrium-box fields and cumulative sampling history.

import argparse
import json
from pathlib import Path

import matplotlib

# The noninteractive backend also supports terminals without a graphical display.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from check_results import FILE_PATTERN, evaluate, load_fields, resolve_input, summarize_file

DENSITY_COLOR = "#2364AA"
TRANSLATIONAL_COLOR = "#C45508"
ROTATIONAL_COLOR = "#14836B"
SPEED_COLOR = "#6C4BA5"

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Plot equilibrium-box Fluent fields and cumulative statistics against the fixed reference."
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        help="Run directory, statisticResults directory, or final DAT file",
    )
    parser.add_argument(
        "--reference", type=Path,
        default=Path(__file__).resolve().with_name("reference_results.json"),
    )
    parser.add_argument("--log", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("benchmark_plots"))
    return parser.parse_args()


# Sampling files contain cumulative averages after startup rather than independent samples.
def read_history(field_path, config):
    history = []
    for output_file in field_path.parent.glob("DSMCKn*_iter*_CELL*.dat"):
        match = FILE_PATTERN.fullmatch(output_file.name)
        if match is None:
            continue
        if abs(float(match.group(1)) - config["kn"]) >= 1e-12:
            continue
        if int(match.group(3)) != config["cells"]:
            continue

        step = int(match.group(2))
        if not config["sampling_start"] < step <= config["total_dsmc_steps"]:
            continue

        metrics = summarize_file(output_file, config["cells"], config["temperature_K"])
        history.append((step, metrics))

    history.sort(key=lambda entry: entry[0])
    if not history:
        raise ValueError("No post-startup cumulative outputs found")
    return history


# Cell IDs follow output order, and velocity histograms show cell means rather than particles.
def plot_fields(fields, config, seed, output_file):
    density = np.array(fields[700])[:, 0]
    temperature = np.array(fields[702])
    velocity = np.array(fields[701])
    cell_ids = np.arange(1, len(density) + 1)

    figure, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
    density_axis, temperature_axis = axes[0]
    velocity_axis, speed_axis = axes[1]

    density_axis.plot(cell_ids, density, ".", ms=2.5, color=DENSITY_COLOR)
    density_axis.axhline(1, color="black", ls="--", lw=1, label="Equilibrium")
    density_axis.set(
        xlabel="Output cell ID", ylabel="Density / reference density",
        title="Density distribution",
    )
    density_axis.legend(frameon=False)

    temperature_axis.plot(
        cell_ids, temperature[:, 0], ".", ms=2.5,
        color=TRANSLATIONAL_COLOR, label="Translational",
    )
    temperature_axis.plot(
        cell_ids, temperature[:, 1], ".", ms=2.5,
        color=ROTATIONAL_COLOR, alpha=0.7, label="Rotational",
    )
    temperature_axis.axhline(1, color="black", ls="--", lw=1)
    temperature_axis.set(
        xlabel="Output cell ID", ylabel="Temperature / wall temperature",
        title="Temperature distributions",
    )
    temperature_axis.legend(frameon=False, ncol=2)

    components = ("ux", "uy", "uz")
    colors = (DENSITY_COLOR, TRANSLATIONAL_COLOR, ROTATIONAL_COLOR)
    for index, (component, color) in enumerate(zip(components, colors)):
        velocity_axis.hist(
            velocity[:, index], bins=24, histtype="step",
            lw=1.5, color=color, label=component,
        )
    velocity_axis.axvline(0, color="black", ls="--", lw=1)
    velocity_axis.set(
        xlabel="Normalized macroscopic velocity (solver output)",
        ylabel="Cell count", title="Velocity components",
    )
    velocity_axis.legend(frameon=False)

    speed_axis.plot(
        cell_ids, np.linalg.norm(velocity, axis=1), ".", ms=2.5, color=SPEED_COLOR,
    )
    speed_axis.set(
        xlabel="Output cell ID", ylabel="Normalized macroscopic speed",
        title="Spatial velocity fluctuations",
    )
    figure.suptitle(
        f"Equilibrium box | Kn={config['kn']} | step {config['total_dsmc_steps']} | seed {seed}"
    )
    figure.savefig(output_file)
    plt.close(figure)


# Dashed lines show equilibrium, stars mark the fixed reference, and vertical lines mark DIG calls.
def plot_history(history, reference, output_file):
    config = reference["configuration"]
    fixed = reference["observed_reference_metrics"]
    steps = [step for step, metrics in history]
    mean_density = [metrics["rho_mean"] for step, metrics in history]
    translational_temperature = [metrics["Tt_mean_K"] for step, metrics in history]
    rotational_temperature = [metrics["Tr_mean_K"] for step, metrics in history]
    rms_speed = [metrics["velocity_rms"] for step, metrics in history]

    figure, axes = plt.subplots(
        3, 1, figsize=(10.5, 8), sharex=True, constrained_layout=True,
    )
    density_axis, temperature_axis, speed_axis = axes

    density_axis.plot(
        steps, mean_density, "o-", ms=3,
        color=DENSITY_COLOR, label="Volume-weighted mean",
    )
    density_axis.axhline(1, color="black", ls="--", lw=1, label="Equilibrium")
    density_axis.set(ylabel="Mean normalized density")
    density_axis.legend(frameon=False, ncol=2)

    temperature_axis.plot(
        steps, translational_temperature, "o-", ms=3,
        color=TRANSLATIONAL_COLOR, label="Translational",
    )
    temperature_axis.plot(
        steps, rotational_temperature, "o-", ms=3,
        color=ROTATIONAL_COLOR, label="Rotational",
    )
    temperature_axis.axhline(
        config["temperature_K"], color="black", ls="--", lw=1, label="Wall temperature",
    )
    temperature_axis.set(ylabel="Mean temperature (K)")
    temperature_axis.legend(frameon=False, ncol=3)

    speed_axis.plot(
        steps, rms_speed, "o-", ms=3, color=SPEED_COLOR, label="Spatial RMS speed",
    )
    speed_axis.set(xlabel="DSMC step", ylabel="Normalized RMS speed")
    speed_axis.legend(frameon=False)

    final_step = config["total_dsmc_steps"]
    density_axis.plot(
        final_step, fixed["rho_mean"], "*", color="black", ms=11,
        label="Fixed-seed reference",
    )
    temperature_axis.plot(
        final_step, fixed["Tt_mean_K"], "*", color=TRANSLATIONAL_COLOR, ms=11,
    )
    temperature_axis.plot(
        final_step, fixed["Tr_mean_K"], "*", color=ROTATIONAL_COLOR, ms=11,
    )
    speed_axis.plot(final_step, fixed["velocity_rms"], "*", color="black", ms=11)

    dig_steps = range(config["dsmc_interval"], final_step + 1, config["dsmc_interval"])
    for axis in axes:
        for step in dig_steps:
            axis.axvline(step, color="0.7", lw=0.6, alpha=0.4)
        axis.grid(alpha=0.18)

    figure.suptitle(
        f"Kn={config['kn']} | cumulative statistics after step {config['sampling_start']}"
        " | stars: fixed-seed reference\n"
        f"Functional benchmark; NS sub-solves capped at {config['ns_max_iterations']} iterations"
    )
    figure.savefig(output_file)
    plt.close(figure)


# Validate the selected run before writing plots and the machine-readable summary.
def main():
    args = parse_arguments()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    config = reference["configuration"]
    field_path = resolve_input(args.input, reference)
    result = evaluate(field_path, reference, args.log)
    fields = load_fields(field_path, config["cells"])

    args.outdir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 300,
    })
    fields_plot = args.outdir / "equilibrium_fields.png"
    history_plot = args.outdir / "equilibrium_history.png"
    summary_file = args.outdir / "check_summary.json"

    plot_fields(fields, config, result["seed"], fields_plot)
    history = read_history(field_path, config)
    plot_history(history, reference, history_plot)
    summary_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "passed": result["passed"],
        "plots": [str(fields_plot), str(history_plot)],
        "summary": str(summary_file),
    }, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
