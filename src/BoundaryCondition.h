#pragma once

#include <vector>

enum class BoundaryRole : unsigned char
{

    None,

    Interface,

    Inlet,

    Outlet,

    Wall,

    Symmetry
};

enum class BoundaryModel : unsigned char
{

    None,

    FreestreamInlet,

    PressureInlet,

    OpenOutlet,

    PressureOutlet,

    IsothermalWall,

    DiffuseWall,

    SpecularWall
};

struct BoundaryCondition
{

    int tag = -1;

    BoundaryRole nsRole = BoundaryRole::None;
    BoundaryModel nsModel = BoundaryModel::None;

    BoundaryRole dsmcRole = BoundaryRole::None;
    BoundaryModel dsmcModel = BoundaryModel::None;

    bool injectParticles = false;
    double pressure = 0.0;
    double rho = 1.0;
    double ux = 0.0;
    double uy = 0.0;
    double uz = 0.0;
    double temperature = 1.0;
    double freestreamUxScale = 1.0;
};

class BoundaryConditionTable
{
public:
    BoundaryConditionTable()
    {
        loadDefaults();
    }
    void loadDefaults()
    {
        conditions.clear();
        // Tag 3 is the NS/DSMC interface and does not inject particles.
        BoundaryCondition interfaceBc;
        interfaceBc.tag = 3;
        interfaceBc.nsRole = BoundaryRole::Interface;
        interfaceBc.nsModel = BoundaryModel::None;
        interfaceBc.dsmcRole = BoundaryRole::Interface;
        interfaceBc.dsmcModel = BoundaryModel::None;
        addOrReplace(interfaceBc);
        BoundaryCondition wallBc;
        wallBc.tag = 4;
        wallBc.nsRole = BoundaryRole::Wall;
        wallBc.nsModel = BoundaryModel::IsothermalWall;
        wallBc.dsmcRole = BoundaryRole::Wall;
        wallBc.dsmcModel = BoundaryModel::DiffuseWall;
        wallBc.injectParticles = false;
        wallBc.ux = 0.0;
        wallBc.uy = 0.0;
        wallBc.uz = 0.0;
        wallBc.temperature = 1.0;
        addOrReplace(wallBc);
    }

    void addOrReplace(const BoundaryCondition& bc)
    {
        for (BoundaryCondition& item : conditions)
        {
            if (item.tag == bc.tag)
            {
                item = bc;
                return;
            }
        }
        conditions.push_back(bc);
    }

    const BoundaryCondition& byTag(int tag) const
    {
        for (const BoundaryCondition& item : conditions)
        {
            if (item.tag == tag)
                return item;
        }
        return fallback;
    }
private:
    std::vector<BoundaryCondition> conditions;
    BoundaryCondition fallback;
};
