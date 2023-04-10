﻿/********************************************************************************
*                                                                              *
* This file is part of IfcOpenShell.                                           *
*                                                                              *
* IfcOpenShell is free software: you can redistribute it and/or modify         *
* it under the terms of the Lesser GNU General Public License as published by  *
* the Free Software Foundation, either version 3.0 of the License, or          *
* (at your option) any later version.                                          *
*                                                                              *
* IfcOpenShell is distributed in the hope that it will be useful,              *
* but WITHOUT ANY WARRANTY; without even the implied warranty of               *
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                 *
* Lesser GNU General Public License for more details.                          *
*                                                                              *
* You should have received a copy of the Lesser GNU General Public License     *
* along with this program. If not, see <http://www.gnu.org/licenses/>.         *
*                                                                              *
********************************************************************************/

#ifndef CGAL_KERNEL_H
#define CGAL_KERNEL_H

/*
#ifdef NO_CACHE

#define IN_CACHE(T,E,t,e)
#define CACHE(T,E,e)

#else

#define IN_CACHE(T,E,t,e) std::map<int,t>::const_iterator it = cache.T.find(E->entity->id());\
if ( it != cache.T.end() ) { e = it->second; return true; }
#define CACHE(T,E,e) cache.T[E->entity->id()] = e;

#endif
*/

#ifdef IFOPSH_SIMPLE_KERNEL
#define CgalKernel SimpleCgalKernel
#define create_cube create_cube_simple
#define create_polyhedron create_polyhedron_simple
#endif

#include "../../../ifcparse/macros.h"

#include "../../../ifcgeom/AbstractKernel.h"

#include "../../../ifcgeom/IfcGeomElement.h"
#include "../../../ifcgeom/kernels/cgal/CgalConversionResult.h"

#include <CGAL/Polygon_2.h>

#include <cmath>

namespace ifcopenshell {
	namespace geometry {
		namespace utils {
			IFC_GEOM_API CGAL::Polyhedron_3<Kernel_> create_cube(double d);
			IFC_GEOM_API CGAL::Polyhedron_3<Kernel_> create_cube(const Kernel_::Point_3& lower, const Kernel_::Point_3& upper);
			IFC_GEOM_API CGAL::Polyhedron_3<Kernel_> create_polyhedron(std::list<cgal_face_t> &face_list, bool stitch_borders = false);

#ifndef IFOPSH_SIMPLE_KERNEL
			IFC_GEOM_API CGAL::Polyhedron_3<Kernel_> create_polyhedron(const CGAL::Nef_polyhedron_3<Kernel_> &nef_polyhedron);
			IFC_GEOM_API CGAL::Nef_polyhedron_3<Kernel_> create_nef_polyhedron(std::list<cgal_face_t> &face_list);
			IFC_GEOM_API CGAL::Nef_polyhedron_3<Kernel_> create_nef_polyhedron(CGAL::Polyhedron_3<Kernel_> &polyhedron);
#endif
		}

		namespace kernels {

			class IFC_GEOM_API CgalKernel : public AbstractKernel {
			private:
				size_t circle_segments_;

#ifndef IFOPSH_SIMPLE_KERNEL
				bool preprocess_boolean_operand(const IfcUtil::IfcBaseClass* log_reference, const cgal_shape_t& shape_const, CGAL::Nef_polyhedron_3<Kernel_>& result, bool dilate);

				bool thin_solid(const CGAL::Nef_polyhedron_3<Kernel_>& a, CGAL::Nef_polyhedron_3<Kernel_>& result);

				CGAL::Nef_polyhedron_3<Kernel_> create_precision_cube_() const {
					auto cc = utils::create_cube(conv_settings_.getValue(ConversionSettings::GV_PRECISION));
					return CGAL::Nef_polyhedron_3<Kernel_>(cc);
				}
#endif
			public:

				CgalKernel(const ConversionSettings& settings)
					: AbstractKernel("cgal", settings)
					, circle_segments_(32)
				{}

				void remove_duplicate_points_from_loop(cgal_wire_t& polygon);

				bool convert(const taxonomy::extrusion*, cgal_shape_t&);
				bool convert(const taxonomy::face*, cgal_face_t&);
				bool convert(const taxonomy::loop*, cgal_wire_t&);
				// bool convert(const taxonomy::matrix4*, cgal_placement_t&);
				bool convert(const taxonomy::shell*, cgal_shape_t&);

				bool process_extrusion(const cgal_face_t& bottom_face, const taxonomy::direction3& direction, double height, cgal_shape_t& shape);
				bool process_as_2d_polygon(const taxonomy::boolean_result* br, std::list<CGAL::Polygon_2<Kernel_>>& loops, double& z0, double& z1);
				bool process_as_2d_polygon(const std::list<std::list<std::pair<const IfcUtil::IfcBaseClass*, cgal_shape_t>>>& operands, std::list<CGAL::Polygon_2<Kernel_>>& loops, double& z0, double& z1);

				virtual bool convert_impl(const taxonomy::shell*, IfcGeom::ConversionResults&);
				virtual bool convert_impl(const taxonomy::extrusion*, IfcGeom::ConversionResults&);
				virtual bool convert_impl(const taxonomy::boolean_result*, IfcGeom::ConversionResults&);
				virtual bool convert_impl(const taxonomy::solid*, IfcGeom::ConversionResults&);

				virtual bool convert_openings(const IfcUtil::IfcBaseEntity* entity, const std::vector<std::pair<taxonomy::item*, ifcopenshell::geometry::taxonomy::matrix4>>& openings,
					const IfcGeom::ConversionResults& entity_shapes, const ifcopenshell::geometry::taxonomy::matrix4& entity_trsf, IfcGeom::ConversionResults& cut_shapes);

#ifndef IFOPSH_SIMPLE_KERNEL
				CGAL::Nef_polyhedron_3<Kernel_> precision_cube() const { return create_precision_cube_(); }
#endif
			};

		}
	}
}
#endif