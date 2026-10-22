.DEFAULT_GOAL := all

CXXFLAGS ?= -O2 -std=c++11
LDFLAGS ?=
EXTRA_LIBS ?=
D_SRC := src

# Select platform-specific compiler, MPI settings, and dependency paths.
ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -NonInteractive -Command
CXX := g++
D_OBJ := obj/windows
EXEC := main_mpiDSMC_ht.exe
LIB_ROOT ?= metis/windows
MPI_INCLUDE ?= D:/MPI/Include
MPI_LIBRARY ?= D:/MPI/Lib/x64/msmpi.lib
CPPFLAGS += -I"$(MPI_INCLUDE)"
LDLIBS := "$(MPI_LIBRARY)"
else
SHELL := /bin/sh
CXX := mpic++
D_OBJ := obj/linux
EXEC := main_mpiDSMC_ht
LIB_ROOT ?= metis/linux
LDLIBS := -lm
endif

METIS_LIBRARY := $(LIB_ROOT)/lib/libmetis.a
GK_LIBRARY := $(LIB_ROOT)/lib/libGKlib.a
CPPFLAGS += -I"$(LIB_ROOT)/include"
# Map source files to objects and generated header dependencies.
SRC := $(wildcard $(D_SRC)/*.cpp)
OBJ := $(patsubst $(D_SRC)/%.cpp,$(D_OBJ)/%.o,$(SRC))
DEP := $(OBJ:.o=.d)

.PHONY: all clean

all: $(EXEC)

$(EXEC): $(OBJ) $(METIS_LIBRARY) $(GK_LIBRARY)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o "$@" $(OBJ) "$(METIS_LIBRARY)" "$(GK_LIBRARY)" $(LDLIBS) $(EXTRA_LIBS)

$(D_OBJ)/%.o: $(D_SRC)/%.cpp | $(D_OBJ)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c "$<" -o "$@"

$(D_OBJ):
ifeq ($(OS),Windows_NT)
	New-Item -ItemType Directory -Force -Path "$(D_OBJ)" | Out-Null
else
	mkdir -p "$(D_OBJ)"
endif

clean:
ifeq ($(OS),Windows_NT)
	Get-ChildItem -LiteralPath "$(D_OBJ)" -File -ErrorAction SilentlyContinue | Where-Object { $$_.Extension -in '.o', '.d' } | Remove-Item -Force
	Remove-Item -LiteralPath "$(EXEC)" -Force -ErrorAction SilentlyContinue
else
	$(RM) $(OBJ) $(DEP) "$(EXEC)"
endif

-include $(DEP)
