# IfcSverchok - IFC Sverchok extension
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of IfcSverchok.
#
# IfcSverchok is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IfcSverchok is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with IfcSverchok.  If not, see <http://www.gnu.org/licenses/>.

from copy import deepcopy
from email.policy import default
import bpy
import ifcopenshell
import ifcsverchok.helper
import ifcopenshell.api
from ifcsverchok.ifcstore import SvIfcStore
import blenderbim.tool as tool
import blenderbim.core.geometry as core
from bpy.props import StringProperty, EnumProperty, IntProperty, BoolProperty, PointerProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import (updateNode, flatten_data, fixed_iter, flat_iter)
from blenderbim.bim.module.root.prop import get_contexts
from sverchok.data_structure import zip_long_repeat, node_id
from sverchok.core.socket_data import sv_get_socket

from itertools import chain, cycle

class SvIfcBMeshToIfcRepr(bpy.types.Node, SverchCustomTreeNode, ifcsverchok.helper.SvIfcCore):
    """
    Triggers: BMesh to Ifc Repr
    Tooltip: Blender mesh to Ifc Shape Representation
    """
    bl_idname = "SvIfcBMeshToIfcRepr"
    bl_label = "IFC Blender Mesh to IFC Repr"
    node_dict = {}

    is_scene_dependent = True  # if True and is_interactive then the node will be updated upon scene changes

    def refresh_node(self, context):
        if self.refresh_local:
            self.process()
            self.refresh_local = False

    refresh_local: BoolProperty(name="Update Node", description="Update Node", update=refresh_node)

    n_id: StringProperty()
    context_types = [
        ('Model', 'Model', 'Context type: Model', 0),
        ('Plan', 'Plan', 'Context type: Plan', 1),
    ]

    context_identifiers = [
        ('Body', 'Body', 'Context identifier: Body', 0),
        ('Annotation', 'Annotation', 'Context identifier: Annotation', 1),
        ('Box', 'Box', 'Context identifier: Box', 2),
        ('Axis', 'Axis', 'Context identifier: Axis', 3),
    ]
    target_views = [
        ('MODEL_VIEW', 'MODEL_VIEW', 'Target View: MODEL_VIEW', 0),
        ('PLAN_VIEW', 'PLAN_VIEW', 'Target View: PLAN_VIEW', 1),
        ('GRAPH_VIEW', 'GRAPH_VIEW', 'Target View: GRAPH_VIEW', 2),
        ('SKETCH_VIEW', 'SKETCH_VIEW', 'Target View: SKETCH_VIEW', 3),
    ]
    paradigms = [
        ('Tessellation', 'Tessellation', 'Geometry paradigm: Tessellation', 0),
        ('Extrusion', 'Extrusion', 'Geometry paradigm: Extrusion', 1),
    ]
    blender_objects: PointerProperty(name="Blender Mesh(es)", description="Blender Mesh Object(s)",update=updateNode, type=bpy.types.Object)
    context_type: EnumProperty(name="Context Type", description="Default: Model", default="Model",items=context_types,update=updateNode)
    context_identifier: EnumProperty(name="Context Identifier", description="Default: Body", default="Body", items=context_identifiers, update=updateNode)
    target_view: EnumProperty(name="Target View", description="Default: MODEL VIEW", default="MODEL_VIEW",items=target_views, update=updateNode)
    paradigm: EnumProperty(name="Paradigm", description="Which geometry type to convert to. Choose between tessellation or extrusion. Default: Tessellation.",default="Tessellation",items=paradigms, update=updateNode)
    tooltip: StringProperty(name="Tooltip")


    def sv_init(self, context):
        self.inputs.new("SvStringsSocket", "context_type").prop_name = "context_type"
        self.inputs.new("SvStringsSocket", "context_identifier").prop_name = "context_identifier"
        self.inputs.new("SvStringsSocket", "target_view").prop_name = "target_view"
        self.inputs.new("SvStringsSocket", "paradigm").prop_name = "paradigm"
        self.inputs.new("SvObjectSocket", "blender_objects").prop_name = "blender_objects" #no prop for now
        self.outputs.new("SvVerticesSocket", "file")
        self.outputs.new("SvVerticesSocket", "Representations")
        self.width = 210
        self.node_dict[hash(self)] = {}


    def draw_buttons(self, context, layout):
        layout.operator("node.sv_ifc_tooltip", text="", icon="QUESTION", emboss=False).tooltip = "Blender mesh to Ifc Shape Representation"
        
        row = layout.row(align=True)
        row.prop(self, 'is_interactive', icon='SCENE_DATA', icon_only=True)
        row.prop(self, 'refresh_local', icon='FILE_REFRESH')

    def process(self):
        print("#"*20, "\n running bmesh_to_ifc3 PROCESS()... \n", "#"*20,)
        print("#"*20, "\n hash(self):", hash(self), "\n", "#"*20,)
        
        self.sv_input_names = [i.name for i in self.inputs]

        if hash(self) not in self.node_dict:
            self.node_dict[hash(self)] = {} #happens if node is already on canvas when blender loads
        if not self.node_dict[hash(self)]:
            self.node_dict[hash(self)].update(dict.fromkeys(self.sv_input_names, 0))
        
        print("node_dict: ", self.node_dict)
        if not self.inputs["blender_objects"].sv_get()[0]:
            return
        edit = False
        for i in range(len(self.inputs)):
            input = self.inputs[i].sv_get(deepcopy=False)
            # print("input: ", input)
            # print("self.node_dict[hash(self)][self.inputs[i].name]: ", self.node_dict[hash(self)][self.inputs[i].name])
            if isinstance(self.node_dict[hash(self)][self.inputs[i].name], list) and input != self.node_dict[hash(self)][self.inputs[i].name]:
                edit = True
            self.node_dict[hash(self)][self.inputs[i].name] = input
        
        #temporary
        if self.paradigm == "Extrusion":
            raise Exception("Extrusion not yet implemented.")
            return

        if self.refresh_local:
            edit = True

        blender_objects = self.inputs["blender_objects"].sv_get()
        # print("\ncontext_type: ", self.context_type)
        # print("context_identifier: ", self.context_identifier)
        # print("blender_objects: ", blender_objects)

        self.file = SvIfcStore.get_file()

        self.context = self.get_context()
        if self.node_id not in SvIfcStore.id_map:
            representations = self.create(blender_objects)
        else:
            if edit is True:
                self.edit()
                representations = self.create(blender_objects)
            else:
                representations = self.get_existing_element()
        
        print("representations: ", representations)
        print("SvIfcStore.id_map: ", SvIfcStore.id_map)

        self.outputs["Representations"].sv_set(representations)
        self.outputs["file"].sv_set([[self.file]])

    def create(self, blender_objects):
        results = []
        for blender_object in blender_objects:
            representation = ifcopenshell.api.run("geometry.add_representation", self.file, should_run_listeners=False,blender_object = blender_object, geometry=blender_object.data, context = self.context)
            if not representation:
                raise Exception("Couldn't create representation. Possibly wrong context.")
            results.append([representation])
            SvIfcStore.id_map.setdefault(self.node_id, {}).setdefault("Representations", []).append(representation.id())
        return results

    def edit(self):
        # results = self.get_existing_element()
        if "Representations" not in SvIfcStore.id_map[self.node_id]:
            return
        for step_id in SvIfcStore.id_map[self.node_id]["Representations"]:
            #if self.file.by_id(step_id).is_a('IfcShapeRepresentation'):
            print("step_id: ", step_id)
            ifcopenshell.api.run("geometry.remove_representation", self.file, representation=self.file.by_id(step_id))
        del SvIfcStore.id_map[self.node_id]["Representations"]
        return 

    def get_existing_element(self):
        results = []
        for step_id in SvIfcStore.id_map[self.node_id]["Representations"]:
            results.append([self.file.by_id(step_id)])
        return results

    def get_context(self):
        context = ifcopenshell.util.representation.get_context(self.file, self.context_type, self.context_identifier, self.target_view)
        
        if not context:
            parent = ifcopenshell.util.representation.get_context(self.file, self.context_type)
            if not parent:
                parent = ifcopenshell.api.run("context.add_context", self.file, context_type=self.context_type)
            print("\nParent: ", parent)
            context = ifcopenshell.api.run(
                "context.add_context",
                self.file,
                context_type=self.context_type,
                context_identifier=self.context_identifier,
                target_view=self.target_view,
                parent=parent,
            )
            # SvIfcStore.id_map.setdefault(self.node_id, []).append(context.id())
            SvIfcStore.id_map.setdefault(self.node_id, {}).setdefault("Contexts", []).append(context.id())

        return context
    
    def sv_free(self):
        
        try:
            print('DELETING')
            self.file = SvIfcStore.get_file()
            if "Representations" in SvIfcStore.id_map[self.node_id]:
                for step_id in SvIfcStore.id_map[self.node_id]["Representations"]:
                    print("step_id: ", step_id)
                    ifcopenshell.api.run("geometry.remove_representation", self.file, representation=self.file.by_id(step_id))

            if "Contexts" in SvIfcStore.id_map[self.node_id]:
                for context_id in SvIfcStore.id_map[self.node_id]["Contexts"]:
                    if not self.file.get_inverse(self.file.by_id(self.context.id())):
                        ifcopenshell.api.run("context.remove_context", self.file, representation=self.file.by_id(context_id))
                        print("Removed context with step ID: ", context_id)
                        SvIfcStore.id_map[self.node_id]["Contexts"].remove(context_id)
            del SvIfcStore.id_map[self.node_id]
            del self.node_dict[hash(self)]
            print('Node was deleted')
        except KeyError or AttributeError:
            pass
        

def register():
    bpy.utils.register_class(SvIfcBMeshToIfcRepr)
    


def unregister():
    bpy.utils.unregister_class(SvIfcBMeshToIfcRepr)