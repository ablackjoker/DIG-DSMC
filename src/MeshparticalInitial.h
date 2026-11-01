// Defines particle storage and the interfaces for initial particle generation.

#pragma once
# include "meshImport.h"
# include "MessagePassing.h"
# include "MpiContext.h"
# include "MeshPartitionTransfer3D.h"
# include <random>
# include <unordered_map>
using namespace std;

struct particle
{

    int p_serial;
    int p_rank_serial;
    int p_mesh_serial;
    int p_weight_origin_gid = -1;
    // Velocity and position are stored in normalized DSMC units.
    double p_velocity[DIM];
    double p_location[DIM];

    double p_Ir;
    double dt_left;
};

struct DtleftPacket
{

    particle p;
    int gface = -1;
    int gcell = -1;
    int tri = -1;
};

struct ParticleBucketSoA
{

    std::vector<int> p_serial;
    std::vector<int> p_rank_serial;
    std::vector<int> p_mesh_serial;
    std::vector<double> vx;
    std::vector<double> vy;
    std::vector<double> vz;
    std::vector<double> px;
    std::vector<double> py;
    std::vector<double> pz;
    std::vector<double> p_Ir;
    std::vector<double> dt_left;

    size_t size() const { return p_serial.size(); }

    bool empty() const { return p_serial.empty(); }

    size_t capacity() const { return p_serial.capacity(); }

    void clear()
    {
        p_serial.clear();
        p_rank_serial.clear();
        p_mesh_serial.clear();
        vx.clear();
        vy.clear();
        vz.clear();
        px.clear();
        py.clear();
        pz.clear();
        p_Ir.clear();
        dt_left.clear();
    }

    void reserve(size_t n)
    {
        p_serial.reserve(n);
        p_rank_serial.reserve(n);
        p_mesh_serial.reserve(n);
        vx.reserve(n);
        vy.reserve(n);
        vz.reserve(n);
        px.reserve(n);
        py.reserve(n);
        pz.reserve(n);
        p_Ir.reserve(n);
        dt_left.reserve(n);
    }

    void resize(size_t n)
    {
        p_serial.resize(n);
        p_rank_serial.resize(n);
        p_mesh_serial.resize(n);
        vx.resize(n);
        vy.resize(n);
        vz.resize(n);
        px.resize(n);
        py.resize(n);
        pz.resize(n);
        p_Ir.resize(n);
        dt_left.resize(n);
    }

    particle get(size_t i) const
    {
        particle part;
        part.p_serial = p_serial[i];
        part.p_rank_serial = p_rank_serial[i];
        part.p_mesh_serial = p_mesh_serial[i];
        part.p_velocity[0] = vx[i];
        part.p_velocity[1] = vy[i];
        part.p_velocity[2] = vz[i];
        part.p_location[0] = px[i];
        part.p_location[1] = py[i];
        part.p_location[2] = pz[i];
        part.p_Ir = p_Ir[i];
        part.dt_left = dt_left[i];
        return part;
    }

    void set(size_t i, const particle &part)
    {
        p_serial[i] = part.p_serial;
        p_rank_serial[i] = part.p_rank_serial;
        p_mesh_serial[i] = part.p_mesh_serial;
        vx[i] = part.p_velocity[0];
        vy[i] = part.p_velocity[1];
        vz[i] = part.p_velocity[2];
        px[i] = part.p_location[0];
        py[i] = part.p_location[1];
        pz[i] = part.p_location[2];
        p_Ir[i] = part.p_Ir;
        dt_left[i] = part.dt_left;
    }

    void push_back(const particle &part)
    {
        p_serial.push_back(part.p_serial);
        p_rank_serial.push_back(part.p_rank_serial);
        p_mesh_serial.push_back(part.p_mesh_serial);
        vx.push_back(part.p_velocity[0]);
        vy.push_back(part.p_velocity[1]);
        vz.push_back(part.p_velocity[2]);
        px.push_back(part.p_location[0]);
        py.push_back(part.p_location[1]);
        pz.push_back(part.p_location[2]);
        p_Ir.push_back(part.p_Ir);
        dt_left.push_back(part.dt_left);
    }

    void append_copies(const particle& part, int localCell, int rank, int copies)
    {
        if (copies <= 0) return;

        const size_t first = size();
        const size_t count = (size_t)copies;
        p_serial.resize(first + count);
        for (size_t offset = 0; offset < count; ++offset)
            p_serial[first + offset] = (int)(first + offset);

        p_rank_serial.insert(p_rank_serial.end(), count, rank);
        p_mesh_serial.insert(p_mesh_serial.end(), count, localCell);
        vx.insert(vx.end(), count, part.p_velocity[0]);
        vy.insert(vy.end(), count, part.p_velocity[1]);
        vz.insert(vz.end(), count, part.p_velocity[2]);
        px.insert(px.end(), count, part.p_location[0]);
        py.insert(py.end(), count, part.p_location[1]);
        pz.insert(pz.end(), count, part.p_location[2]);
        p_Ir.insert(p_Ir.end(), count, part.p_Ir);
        dt_left.insert(dt_left.end(), count, 0.0);
    }

    void pop_back()
    {
        p_serial.pop_back();
        p_rank_serial.pop_back();
        p_mesh_serial.pop_back();
        vx.pop_back();
        vy.pop_back();
        vz.pop_back();
        px.pop_back();
        py.pop_back();
        pz.pop_back();
        p_Ir.pop_back();
        dt_left.pop_back();
    }

    void append_bucket(ParticleBucketSoA &other)
    {
        const size_t addSize = other.size();
        if (addSize == 0) return;
        reserve(size() + addSize);
        p_serial.insert(p_serial.end(), other.p_serial.begin(), other.p_serial.end());
        p_rank_serial.insert(p_rank_serial.end(), other.p_rank_serial.begin(), other.p_rank_serial.end());
        p_mesh_serial.insert(p_mesh_serial.end(), other.p_mesh_serial.begin(), other.p_mesh_serial.end());
        vx.insert(vx.end(), other.vx.begin(), other.vx.end());
        vy.insert(vy.end(), other.vy.begin(), other.vy.end());
        vz.insert(vz.end(), other.vz.begin(), other.vz.end());
        px.insert(px.end(), other.px.begin(), other.px.end());
        py.insert(py.end(), other.py.begin(), other.py.end());
        pz.insert(pz.end(), other.pz.begin(), other.pz.end());
        p_Ir.insert(p_Ir.end(), other.p_Ir.begin(), other.p_Ir.end());
        dt_left.insert(dt_left.end(), other.dt_left.begin(), other.dt_left.end());
        other.clear();
    }
};

class MeshparticalInitial
{
private:
public:

    inline mt19937& thread_rng()
    {
        static thread_local mt19937 gen{RANDOM_SEED + static_cast<unsigned int>(rank)};
        return gen;
    }

    static std::uniform_real_distribution<double>& get_uniform() {
        static thread_local std::uniform_real_distribution<double> dis(0.0, 1.0);
        return dis;
    }

    meshImport *mesh = NULL;
    meshMessage mess; 

    vector<DsmcCell> cells;
    vector<DsmcEdge> edges;
    vector<double> localPointXY;
    vector<unsigned char> faceSplitTag;
    const MpiContext* mpi = nullptr;
    MessagePassing *mpass = NULL;

    int rank,size,c_rank,c_size;

    vector<int> local_cells;vector<int> face_gids;
    unordered_map<int,int> gid2local;unordered_map<int,int> face_gid2local;
    vector<int> rank_cell_all;

    PartitionState3D partitionState;
    bool partitionReady = false;
    int my_ncell, my_nface;
    int my_owned_ncell = 0; 

    MPI_Comm calGroup;
    MPI_Comm comm;
    // Current buckets hold active particles; next buckets receive advected ones.
    vector<ParticleBucketSoA> cell_particles_curr;
    unordered_map<int, ParticleBucketSoA> cell_particles_next;

    vector<int> cell_particle_reserve_hint;
    vector<double> cellNeffByGlobal;
    vector<double> crmax;

    vector<double> remainderincoll;
    vector<double> remainderinpre;

    MeshparticalInitial();

    ~MeshparticalInitial();

    MeshparticalInitial(meshImport *mesh, meshMessage mess, MessagePassing *mpass, const MpiContext& mpiCtx);

    void module_variables();

    double particleWeight(int globalCell) const;

    void allocateOwnedParticleBuckets();

    int Iround(double x);

    void adjust_particles(vector<double>& regions, int size, int delta);

    void Np_tri_inititial(int i, vector<double>& Np_tri, int Np_exa);

    void meshfillpar(int i,vector<double>& Np_tri);

    void Collision_constant_initial();

    void CreateParticlesnode(int j,int i, int index0, int index1, int index2, const double center[DIM]);

    void CreateParticlesnode(int j,int i, int index0, int index1, int index2, int index3);

    particle velocityLocationGenerate(int i, int index0, int index1, int index2, const double center[DIM]);

    particle velocityLocationGenerate(int i, int index0, int index1, int index2, int index3);

    void crossProduct(const double* vecA, const double* vecB, double* result);

    double dotProduct(const double* vecA, const double* vecB, int size);
};
