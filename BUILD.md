# Build instructions

Run these commands from the repository root. Return to [README](README.md) for benchmark parameters, execution, and verification.


Use a C++11 compiler, GNU Make, MPI, and static METIS/GKlib libraries built for the same platform and ABI. METIS indices and reals must both use 32 bits. Python 3 is needed for result checking; NumPy and Matplotlib are needed for plots.

Verified toolchains: Windows 64-bit MinGW GCC 14.2.0 with Microsoft MPI; WSL Ubuntu 22.04 with GCC 11.4.0 and Open MPI 4.1.2. Local plotting used NumPy 1.24.3 and Matplotlib 3.7.2. A fixed seed does not imply byte-identical results across different toolchains or MPI implementations.

The dependency sources under `metis/sources` correspond to:

- GKlib: https://github.com/KarypisLab/GKlib at `3b7d61b9f885063c89901f3901fb4426f9cfb58f`.
- METIS: https://github.com/KarypisLab/METIS at `272d4a91c5f66c92327493339a476c553ebf1f5d`.

Retain their bundled license files. `Makefile` builds the solver and expects the dependency headers/libraries to be installed first. Default locations are `metis/windows` and `metis/linux`; `LIB_ROOT` can override these locations.

### Windows PowerShell

Install 64-bit MinGW GCC/GNU Make, Microsoft MPI runtime and SDK, and CMake. Ensure `g++`, `make`, `mpiexec`, and `cmake` are on PATH. The default MPI SDK paths are `D:/MPI/Include` and `D:/MPI/Lib/x64/msmpi.lib`; supply your own paths when different:

```powershell
make -j4 MPI_INCLUDE="D:/MPI/Include" MPI_LIBRARY="D:/MPI/Lib/x64/msmpi.lib"
```

This uses `metis/windows/include`, `metis/windows/lib/libmetis.a`, and `metis/windows/lib/libGKlib.a`. To rebuild the dependency libraries from the bundled sources, use an unused drive letter as an ASCII path alias if the checkout path contains non-ASCII characters:

```powershell
subst V: "$PWD"
Push-Location V:\
$makeProgram = (Get-Command make).Source
python -c "from pathlib import Path; import shutil; p=Path('metis/sources/METIS'); q=p/'build/xinclude'; q.mkdir(parents=True,exist_ok=True); (q/'metis.h').write_text('#define IDXTYPEWIDTH 32\n#define REALTYPEWIDTH 32\n'+(p/'include/metis.h').read_text()); shutil.copyfile(p/'include/CMakeLists.txt',q/'CMakeLists.txt')"
cmake -S metis/sources/GKlib -B metis/build/mingw/GKlib -G "MinGW Makefiles" "-DCMAKE_MAKE_PROGRAM=$makeProgram" -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release -DSHARED=OFF -DOPENMP=OFF -DGKLIB_BUILD_APPS=OFF -DCMAKE_INSTALL_PREFIX=V:/metis/windows
cmake --build metis/build/mingw/GKlib --parallel 4
cmake --install metis/build/mingw/GKlib
cmake -S metis/sources/METIS -B metis/build/mingw/METIS -G "MinGW Makefiles" "-DCMAKE_MAKE_PROGRAM=$makeProgram" -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release -DSHARED=OFF -DGKLIB_PATH=V:/metis/windows -DCMAKE_INSTALL_PREFIX=V:/metis/windows
cmake --build metis/build/mingw/METIS --target metis --parallel 4
cmake --install metis/build/mingw/METIS/libmetis
Copy-Item metis/sources/METIS/build/xinclude/metis.h metis/windows/include/metis.h
Pop-Location
subst V: /D
make -j4
```

Only the METIS library target is required. Its optional command-line programs are not part of the benchmark. Run the dependency commands in a fresh build directory if an existing CMake cache points to a different checkout.

### Ubuntu / WSL

Install the build tools and MPI if absent:

```bash
sudo apt-get update
sudo apt-get install build-essential cmake python3 python3-numpy python3-matplotlib openmpi-bin libopenmpi-dev
```

From the checkout root, build the dependency libraries if absent:

```bash
python3 -c "from pathlib import Path; import shutil; p=Path('metis/sources/METIS'); q=p/'build/xinclude'; q.mkdir(parents=True,exist_ok=True); (q/'metis.h').write_text('#define IDXTYPEWIDTH 32\n#define REALTYPEWIDTH 32\n'+(p/'include/metis.h').read_text()); shutil.copyfile(p/'include/CMakeLists.txt',q/'CMakeLists.txt')"
cmake -S metis/sources/GKlib -B metis/build/linux/GKlib -DCMAKE_BUILD_TYPE=Release -DSHARED=OFF -DOPENMP=OFF -DGKLIB_BUILD_APPS=OFF -DCMAKE_INSTALL_PREFIX="$PWD/metis/linux"
cmake --build metis/build/linux/GKlib --parallel 4
cmake --install metis/build/linux/GKlib
cmake -S metis/sources/METIS -B metis/build/linux/METIS -DCMAKE_BUILD_TYPE=Release -DSHARED=OFF -DGKLIB_PATH="$PWD/metis/linux" -DCMAKE_INSTALL_PREFIX="$PWD/metis/linux"
cmake --build metis/build/linux/METIS --target metis --parallel 4
cmake --install metis/build/linux/METIS/libmetis
cp metis/sources/METIS/build/xinclude/metis.h metis/linux/include/metis.h
make -j4
```

The solver executable is `main_mpiDSMC_ht.exe` on Windows and `main_mpiDSMC_ht` on Linux. Object files are kept separately in `obj/windows` and `obj/linux`. `make clean` removes solver objects and the executable for the current platform.
