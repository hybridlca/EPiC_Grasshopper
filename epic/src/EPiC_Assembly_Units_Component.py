# -*- coding: UTF-8 -*-
# EPiC Grasshopper: A Plugin for analysing embodied environmental flows
#
# Copyright (c) 2023, EPiC Grasshopper.
# You should have received a copy of the GNU General Public License
# along with EPiC Grasshopper; If not, see <http://www.gnu.org/licenses/>.
#
# Further information about the EPiC Database can be found at <https://bit.ly/EPiC_Database>
# To download a full copy of the database, goto <http://doi.org/10.26188/5dc228ef98c5a>
#
# @license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>

"""
Creates a unit assembly based on the selected geometry and EPiC Materials

    Inputs:
        Assembly_Name: Name for the assembly - this will appear in data EPiC Built Assets and reports.
        ***Optional***

        Assembly_Category: Name for the assembly category. Will use assembly name if none specified.
        Note that assemblies in the same category will be grouped together in the EPiC Built Assets.
        ***Optional***

        Assembly_Comments: Comments about the assembly - these will appear in the data EPiC Built Assets and reports.
        ***Optional***

        **Selected_Units_and/or_Numerical_Values_(no.): A selection of geometry that represent the EPiC Assembly AND/OR values in no.
        Geometry will be counted to calculate embodied environmental flows.
        (**REQUIRED)

        Service_Life_(Years)_Assembly_Override: Estimated service_life (in years) for the assembly.
        Note this will override all material service_life attributes.
        ***Optional***

        Wastage_Coefficient_(%)_Assembly_Override: Estimated wastage percentage (%) for the material.
        Note this will override all material wastage attributes.
        ***Optional***

    Outputs:
        EPiC_Assembly: Outputs a class object (EPiC_Assembly) to be used in EPiC_Analysis.
        This contains all of the embedded assembly attributes.
        (selected_geometry, name, thickness, service_life, wastage, comments, epic_materials, assembly_units)
        ***Connect that output to a panel for a summary***

        Initial_Embodied_Energy_(MJ): The total initial Embodied Energy (MJ) for the assembly.
        This includes the wastage coefficient but does NOT include service_life calculations.

        Initial_Embodied_Water_(L): The total initial Embodied Water (L) for the assembly.
        This includes the wastage coefficient but does NOT include service_life calculations.

        Initial_Embodied_GHG_(kgCO₂e): The total initial Embodied Greenhouse Gas Emissions (kgCO₂e) for the assembly.
        This includes the wastage coefficient but does NOT include service_life calculations.

        Geometry: The geometry used to define the assembly.
"""

from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
from ghpythonlib.componentbase import executingcomponent as component
import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)

# Specify component attributes and units to use for the assembly
units = 'no.'
component_name = "EPiC Assembly - Units (no.)"
geometry_warning = "Brep/surface/line input detected, please input point/unit geometry"


class EPiCAssemblyVolumetricComponent(component):

    def RunScript(self, input_assembly_name, input_assembly_category, input_assembly_comments, input_selected_geometry,
                  input_service_life_override, input_wastage_override, _input_null, *args):

        # Component and version information
        __author__ = epic.__author__
        __version__ = "1.01"
        if __version__ == epic.__version__:
            self.Message = epic.__message__
        else:
            self.Message = epic.version_mismatch(__version__)
            self.AddRuntimeMessage(RML.Remark, self.Message)
        self.Name = component_name
        self.NickName = component_name

        # Sort the material inputs and quantities
        material_list = epic.EPiCAssembly.create_list_of_input_materials_and_qty(self, units, args)

        # Create an EPiCAssembly class object
        try:
            assembly = epic.EPiCAssembly(input_selected_geometry, input_assembly_name, input_service_life_override,
                                         input_wastage_override, input_assembly_comments, material_list,
                                         assembly_units=units, category=input_assembly_category)
        except TypeError:
            self.AddRuntimeMessage(RML.Warning, geometry_warning)
            return [geometry_warning]*5

        # Test to see if geometry is connected to the component
        if not input_selected_geometry:
            self.AddRuntimeMessage(RML.Warning, "No geometry is connected to the assembly")

        # Test to see if any material inputs exist
        if len(material_list) < 1:
            self.AddRuntimeMessage(RML.Warning, "No input EPiC_Material inputs or material quantities have been found ")

        # Calculate the environmental flows for the assembly
        assembly.calculate_flows()

        # Specify the component outputs
        output_initial_energy = assembly.flows['initial']['energy']
        output_initial_water = assembly.flows['initial']['water']
        initial_ghg = assembly.flows['initial']['ghg']

        # Return all component outputs
        return assembly, None, output_initial_energy, output_initial_water, initial_ghg, None, assembly.output_geometry
