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
Select a material from the EPiC Database

    Inputs:
        >>**Connect_Toggle_Switch_to_Activate: Connect a toggle switch and set to 'True' to activate this component.
        (**REQUIRED)

        **Material_Category: Once the EPiC Material component has been activated,
        a value list will be automatically generated with pre-filled categories wired to this input.
        *** To reset this input, delete any connected wires, and re-activate the button ***

        **Selected_Material: Once the EPiC Material component has been activated,
        a value list will be automatically generated with pre-filled materials, based on the selected category (above).
        *** To reset this input, delete any connected wires, and re-activate the button ***

        Wastage_Coefficient_(%): Estimated wastage percentage (%) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates no wastage, 100 indicates 100% wastage.
        ***Optional***

        Material_Service_Life_(Years): Estimated service_life (in years) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates that the material will never need to be replaced.
        ***Optional***

        Energy_Reduction_Factor_(%): Reduce the value of the energy coefficient by a percentage
        0(%) indicates no change, 50(%) half of the value, and 100(%) reduces the energy coefficient to zero
        ***Optional***

        Water_Reduction_Factor_(%): Reduce the value of the water coefficient by a percentage
        0(%) indicates no change, 50(%) half of the value, and 100(%) reduces the water coefficient to zero
        ***Optional***

        GHG_Reduction_Factor_(%): Reduce the value of the GHG emissions coefficient by a percentage
        0(%) indicates no change, 50(%) half of the value, and 100(%) reduces the GHG emissions coefficient to zero
        ***Optional***
        Comments: Comments about the material - these will appear in the printed/exported reports.
        ***Optional***

        >>Connect_Toggle_Switch_to_Open_EPiC_Database: Connect a toggle switch and set to True.
        This will open https://bit.ly/EPiC_Database in a web browser

    Outputs:
        EPiC_Material: Outputs a class object (EPiCMaterial) containing all of the embedded material attributes:
        (name, energy, water, ghg, functional_unit, doi, category, material_id, wastage, service_life, comments)
        ***Connect that output to a panel for a summary***

        Embodied_Energy_Coefficient_(MJ/FU): The Embodied Energy Coefficient for this material.
        Values are imported from the EPiC Database
        ***Note this does not include wastage in the calculation***

        Embodied_Water_Coefficient_(L/FU): The Embodied Water Coefficient for this material.
        Values are imported from the EPiC Database.
        ***Note this does not include wastage in the calculation***

        Embodied_GHG_Coefficient_(kgCO₂e/FU): The Embodied Greenhouse Gas Emissions Coefficient for this material.
        Values are imported from the EPiC Database.
        ***Note this does not include wastage in the calculation***

        Digital Object Identifier (DOI): A link to the material information sheet in the EPiC Database

        Density_(kg/m³): Material density, as provided in the EPiC Database

        Functional_Unit: Functional Unit, as provided in the EPiC Database

        Wastage_Coefficient_(%): Estimated wastage percentage (%) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates no wastage, 100 indicates 100% wastage

        Material_Service_Life_(Years): Estimated service_life (in years) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates that the material will never need to be replaced

        Disclaimer: Disclaimer of the authors associated with the use of the EPiC Grasshopper plugin
"""

import webbrowser

from Grasshopper import Folders
from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
from ghpythonlib.componentbase import executingcomponent as component
from scriptcontext import sticky as st

import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)


class EPiCMaterialComponent(component):

    def RunScript(self, connect_button, material_category, selected_material, comments, _null, wastage, service_life,
                  _null2,
                  energy_reduction, water_reduction, ghg_reduction, _null3, epic_help):

        # Component and version information
        __author__ = epic.__author__
        __version__ = "1.01"
        if __version__ == epic.__version__:
            self.Message = epic.__message__
        else:
            self.Message = epic.version_mismatch(__version__)
            self.AddRuntimeMessage(RML.Remark, self.Message)
        self.Name = "EPiC Material"
        self.NickName = "EPiC Material"

        # Setup a global sticky variable for the component, ensuring sliders component are not continuously generated.
        component_id = ghenv.Component.InstanceGuid
        if component_id not in st:
            st[component_id] = selected_material

        # Open the EPiC Database or EPiC Grasshopper Bugs / Suggestions Google Form
        if epic_help:
            webbrowser.open("https://bit.ly/EPiC_Database", new=1)

        # Specify the directory where the EPiC Database is stored (usually the grasshopper library folder)
        epic_db = epic.EPiCDatabase(Folders.DefaultAssemblyFolder)

        # Generate a material and category list when button is turned on
        if connect_button:
            if not selected_material or not material_category:
                epic.EPiCMaterial.generate_material_and_category_dropdown_list(self, ghenv, epic_db)
                # Reset the global sticky value
                st[component_id] = None

        # Make sure that a material category & material have been selected
        if selected_material and material_category:
            selected_material = epic.EPiCMaterial.remove_func_unit_from_mat_name(selected_material)
            # Test if the selected material is in the selected category
            if epic_db.query(selected_material, 'Category') not in material_category[0]:
                # Get a list of objects in the grasshopper document, so that material list object can be recreated
                ghObjects = self.OnPingDocument().Objects
                epic.EPiCMaterial.recreate_material_list(epic_db, ghObjects, material_category, self.Params)

            # Load the material values from the database
            energy, water, ghg, functional_unit, name, doi, category, material_ID, density = \
                epic_db.query(selected_material, ['Energy', 'Water', 'GHG', 'Functional Unit', 'name',
                                                  'DOI', 'Category', 'ID', 'Density'])

            process_shares = {flow: epic_db.query(selected_material, 'hybrid_process_proportion_' + str(flow)) for
                              flow in epic.DEFINED_FLOWS.keys()}

            # Only run this code if the material selection has changed. Uses global sticky to track material choice.
            if selected_material != st[component_id]:
                # Fetch the wastage/service life coefficient from the EPiCDB (if exists)
                try:
                    # In db, wastage coefficient of 1 = 0%, 1.1 = 10%. Scale accordingly
                    # In db, service life of -1 = no service life.
                    epic_wastage = (epic_db.query(selected_material, 'Wastage') - 1) * 100
                    epic_service_life = (epic_db.query(selected_material, 'Service Life'))
                    if epic_service_life == -1 or not epic_service_life:
                        epic_service_life = 0
                except TypeError:
                    epic_wastage = 0
                    epic_service_life = 0

                # Generate a slider input and set wastage/service life. If one already exists, change the value to new material.
                for input in [(5, epic_wastage), (6, epic_service_life)]:
                    if not self.Params.Input[input[0]].Sources:
                        epic.EPiCMaterial.generate_slider_input(self, ghenv, input[1], input[0])
                    else:
                        for obj in self.OnPingDocument().Objects:
                            if obj.InstanceGuid == self.Params.Input[input[0]].Sources[0].InstanceGuid:
                                self.OnPingDocument().ScheduleSolution(5, ScheduleCallback(obj, input[1]))
                                break

                # Reset global sticky value to the current material selection choice
                st[component_id] = selected_material

            # Include reduction factor for materials
            if water and ghg and energy:
                energy = energy if not energy_reduction and energy_reduction != 0 \
                    else energy / 100 * abs(100 - energy_reduction)
                water = water if not water_reduction and water_reduction != 0 else water / 100 * abs(
                    100 - water_reduction)
                ghg = ghg if not ghg_reduction and ghg_reduction != 0 else ghg / 100 * abs(100 - ghg_reduction)

            # Create the EPiCMaterial class object
            output_epic_material = epic.EPiCMaterial(name=name, water=water, ghg=ghg, energy=energy,
                                                     functional_unit=functional_unit, doi=doi, category=category,
                                                     material_id=material_ID, wastage=wastage,
                                                     service_life=service_life, comments=comments, density=density,
                                                     process_shares=process_shares)

            # Component outputs
            return output_epic_material, None, output_epic_material.energy, output_epic_material.water, \
                   output_epic_material.ghg, None, output_epic_material.doi, output_epic_material.density, \
                   output_epic_material.functional_unit, wastage, service_life, epic.DISCLAIMER

        # Raise error when there is no material and category selected
        else:
            warning = 'Connect a button to the first input, and activate to generate a material & category list'
            self.AddRuntimeMessage(RML.Warning, warning)
            return [warning] * 11 + [epic.DISCLAIMER]

def ScheduleCallback(obj, val):
    if val > 100:
        obj.Slider.Maximum = val
    obj.Slider.Value = val
    obj.ExpireSolution(True)
