#ifndef slic3r_NonplanarSurface_hpp_
#define slic3r_NonplanarSurface_hpp_

#include "libslic3r.h"
#include "NonplanarFacet.hpp"
#include "Point.hpp"
#include "Polygon.hpp"
#include "ExPolygon.hpp"
#include "Geometry.hpp"
#include "ClipperUtils.hpp"

namespace Slic3r {

typedef struct {
  float x;
  float y;
  float z;
} mesh_vertex;

typedef struct {
  mesh_vertex    max;
  mesh_vertex    min;
} mesh_stats;

class NonplanarSurface;

typedef std::vector<NonplanarSurface> NonplanarSurfaces;

class NonplanarSurface
{
    public:
    std::map<int, NonplanarFacet> mesh;
    mesh_stats stats;
    int stable_id = -1;
    NonplanarSurface() {};
    ~NonplanarSurface() {};
    NonplanarSurface(std::map<int, NonplanarFacet> &_mesh);
    bool operator==(const NonplanarSurface& other) const;
    void calculate_stats();
    void translate(float x, float y, float z);
    void scale(float factor);
    void scale(float versor[3]);
    void rotate_z(float angle);
    void debug_output();
    NonplanarSurfaces group_surfaces();
    void mark_neighbor_surfaces(int id);
    bool check_max_printing_height(float height);
    void check_printable_surfaces(float max_angle);
    bool check_surface_area();
    ExPolygons horizontal_projection() const;

};

// User-facing nonplanar errors share one format: what happened, where (height
// and layer as shown by the layer slider), what to do.  The technical detail
// goes to the log and, for internal checks, in short into the message.
// " at height 8.40 mm (layer 43)"; layer_id is 0-based.
std::string nonplanar_location(double z, size_t layer_id);
// Angle to suggest after a failure at `angle` (12 -> 10).
double      nonplanar_suggested_angle(double angle);
// A surface step a nonplanar line cannot follow (steeper than 12 degrees).
[[noreturn]] void throw_nonplanar_too_steep(double z, size_t layer_id, double angle, size_t object_id, const std::string &detail);
// An internal consistency check; not caused by a setting.
[[noreturn]] void throw_nonplanar_internal(const std::string &where, const std::string &detail, size_t object_id);
};

#endif
