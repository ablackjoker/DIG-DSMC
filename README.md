# DIG-DSMC

Version: [v1.1](https://github.com/ablackjoker/DIG-DSMC/tree/v1.1).

**DIG-DSMC equilibrium-box benchmark**: a lightweight DIG-augmented DSMC case: an 8 x 8 x 8 closed box with six stationary isothermal diffuse walls, run with four MPI processes.

The original Apollo case, mesh, and supercomputer build/job scripts are preserved on the `apollo-original` branch; `master` contains this lightweight benchmark.

## Case

| Parameter | Value |
| --- | --- |
| Mesh | [cavity_512.cas](mesh/cavity_512.cas); 512 equal-volume cells; length 1 m |
| Boundary tags | Interior 3; walls 4 |
| Mach / Knudsen number | 0 / 0.1 |
| Initial and wall temperature | 273.15 K |
| Initial particles | 30 per cell; 15360 total |
| Rotational collision number / relaxation probability | 2.59 / 0.25 |
| Random seed | 20261015; streams derived from MPI rank |
| DSMC steps / sampling start | 3000 / 400 |
| DIG interval / NS iteration cap | 500 steps / 200 iterations per call |
| Parallel execution | 4 MPI processes; 1 OpenMP thread per process |
| Kn-cell upper-bound filter | Disabled |

The theoretical equilibrium is uniform: normalized density 1, zero mean velocity, and translational and rotational temperatures of 273.15 K. Finite particle sampling produces fluctuations.

Case parameters are compiled into `src/`; recompile after changing them. [reference_results.json](verification/reference_results.json) records the configuration and acceptance criteria; it does not configure the solver.

## Build

See [BUILD.md](BUILD.md) for Windows MinGW + Microsoft MPI and Ubuntu / WSL instructions, including METIS/GKlib compilation. The solver uses C++11 and GNU Make; dependency libraries must match the platform and use 32-bit METIS indices and reals.

After installing the dependencies:

```sh
make -j4
```

Python 3 is required for verification; plotting also requires NumPy and Matplotlib:

```sh
python -m pip install numpy matplotlib
```

## Run

Run from the repository root, using a fresh output directory.

**Windows PowerShell**

```powershell
$caseRoot = (Get-Location).Path
New-Item -ItemType Directory -Force runs/cavity/statisticResults,runs/cavity/nsTemp,runs/cavity/cellDistribute | Out-Null
$env:OMP_NUM_THREADS = "1"
Remove-Item Env:DSMC2NS_KN_CELL_UPPER_BOUND,Env:DSMC2NS_KN_CELL_FILTER -ErrorAction SilentlyContinue
Push-Location runs/cavity
mpiexec -n 4 "$caseRoot/main_mpiDSMC_ht.exe" "$caseRoot/mesh/cavity_512.cas" 2>&1 | Tee-Object -FilePath run.log
$solverExitCode = $LASTEXITCODE
Pop-Location
if ($solverExitCode -ne 0) { throw "MPI run failed with exit code $solverExitCode" }
```

**Ubuntu / WSL**

```bash
case_root="$PWD"
mkdir -p runs/cavity/statisticResults runs/cavity/nsTemp runs/cavity/cellDistribute
cd runs/cavity
export OMP_NUM_THREADS=1
unset DSMC2NS_KN_CELL_UPPER_BOUND DSMC2NS_KN_CELL_FILTER
mpiexec -n 4 "$case_root/main_mpiDSMC_ht" "$case_root/mesh/cavity_512.cas" > run.log 2>&1
solver_exit_code=$?
cd "$case_root"
if [ "$solver_exit_code" -ne 0 ]; then echo "MPI run failed: $solver_exit_code"; exit "$solver_exit_code"; fi
```

## Verify and plot

The supplied [reference run](runs/cavity_kn01_reference/) contains the four-process execution log and 22 field files. Inspect it without compiling or running the solver:

```sh
python -B verification/check_results.py --input runs/cavity_kn01_reference
python -B verification/plot_results.py --input runs/cavity_kn01_reference --outdir benchmark_plots
```

For your own run, replace `runs/cavity_kn01_reference` with `runs/cavity`. Use `python3` on Linux if needed. Plots are saved as `equilibrium_fields.png` and `equilibrium_history.png` in the output directory.

| Global mean | Equilibrium | Reference result | Tolerance |
| --- | ---: | ---: | --- |
| Normalized density | 1 | 0.9994865 | +/-0.5% of equilibrium |
| Translational temperature | 273.15 K | 273.2890 K | +/-0.5% of equilibrium |
| Rotational temperature | 273.15 K | 273.4172 K | +/-0.5% of equilibrium |

Each normalized mean velocity component must be within +/-0.001; spatial RMS density/temperature errors and RMS speed must be at most 0.015. These are regression limits for global statistics, not per-cell bounds or confidence intervals. Full definitions and exact reference values are in [reference_results.json](verification/reference_results.json).

The checker also checks complete finite fields, positive density/temperatures, the seed and rank count, disabled Kn-cell filtering, 3000 completed steps, and six DIG cycles transferring and correcting all 512 cells. Exit codes: `0` pass, `1` failed checks, `2` input/parsing error. Only the four-process configuration has been validated; fixed seeds do not guarantee identical results across toolchains.

## License

Original project code and documentation: [MIT License](LICENSE), copyright (c) 2026 DIG-DSMC contributors. Bundled [METIS/GKlib sources](metis/sources/) retain their own licenses and copyright notices.
