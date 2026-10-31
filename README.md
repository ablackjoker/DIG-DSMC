# DIG-DSMC Apollo case

Three-dimensional Apollo return-capsule case using the DIG-augmented DSMC solver. The lightweight equilibrium-box benchmark is available on [master](https://github.com/ablackjoker/DIG-DSMC/tree/master).

## Parameters

| Parameter | Value |
| --- | --- |
| Mesh | `mesh/3dapollo372500.cas`; 372500 cells |
| Mach / Knudsen number | 5 / 0.01 |
| Reference length | 3.912 m |
| Freestream / wall temperature | 142.2 K / 300 K |
| Boundary tags | Interior 3; inlet 4; outlet 5; diffuse wall 6 |
| Initial particle target | 100 per cell |
| Rotational collision number `zr` | 2.59 |
| Rotational relaxation probability `P_relax` | 0.25 |
| Random seed | 20261015; streams derived from MPI rank |
| DSMC steps / sampling start | 10000 / 5000 |
| DIG interval / first coupling step | 100 steps / step 200 |
| NS iteration cap / residual tolerance | 800 per DIG call / 1e-6 |

Parameters are compiled into `src/`; rebuild after changing them. The initial macroscopic solve also uses a residual tolerance of 1e-6. High-order ramping, sample-count and bound filters, the Kn-cell upper-bound filter, low-order harmonic reconstruction, and exponential weighting of DSMC-to-NS data are disabled in the default configuration. Finite-value checks remain active. Environment variables beginning with `DSMC2NS_` can override coupling settings.

## Build and run

Use a C++11 compiler, GNU Make, MPI, and METIS/GKlib libraries with 32-bit METIS indices and reals. The existing Makefile contains Intel compiler settings and machine-specific dependency paths. Set these for your machine; for example, with a GNU MPI compiler wrapper:

```bash
mkdir -p obj cellDistribute nsTemp statisticResults
make clean
make -j4 CC=mpic++ CFLAGS="-O3 -std=c++11" \
  METIS_INCLUDE="-I/path/to/metis/include" METIS_LIB="-L/path/to/metis/lib" \
  GK_INCLUDE="-I/path/to/GKlib/include" GK_LIB="-L/path/to/GKlib/lib"
```

Build from source after updating this branch so that existing object files and executables are replaced. Run from the repository root:

```bash
export OMP_NUM_THREADS=1
mpiexec -n 160 ./main_mpiDSMC_ht ./mesh/3dapollo372500.cas > run.log 2>&1
```

The process count can be adjusted to the available resources; this remains a large case with an initial target of approximately 37.25 million simulation particles. For LSF, configure the queue and process count in `SubmitJob.lsf`, then submit with `bsub < SubmitJob.lsf`.

Macroscopic fields and per-cell particle counts are written to `statisticResults/`; macroscopic-solver outputs are written to `nsTemp/`.

## License

[MIT License](LICENSE), copyright (c) 2026 DIG-DSMC contributors. METIS/GKlib dependencies retain their own licenses.
