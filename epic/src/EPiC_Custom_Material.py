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
Creates a custom material using custom environmental flows

    Inputs:
        Material_Name: Name of the material- this will appear in the printed/exported reports
        ***Optional***

        Material_Category: Name of the material category
        ***Optional***

        **Functional_Unit_(m,m²,m³,kg,etc): Functional unit for the material (e.g m, m² ,m³,no. or kg)
        (**REQUIRED)

        Density_(kg/m³): The density of the material in kg/m³
        ***Optional***

        **Embodied_Energy_Coefficient_(MJ/FU): The embodied energy coefficient for the material in MJ/Functional Unit
        (**REQUIRED)

        **Embodied_Water_Coefficient_(L/FU): The embodied water coefficient for the material in L/Functional Unit
        (**REQUIRED)

        **Embodied_GHG_Coefficient_(kgCO₂e/FU): The embodied greenhouse gas emissions coefficient for the material
        in kgCO₂e/Functional Unit
        (**REQUIRED)

        Wastage_Coefficient_(%): Estimated wastage percentage (%) for the material.
        0 indicates no wastage, 100 indicates 100% wastage.
        ***Optional***

        Material_Service_Life_(Years): Estimated service_life (in years) for the material.
        0 indicates that the material will never need to be replaced
        ***Optional***

        Comments: Comments about the material - these will appear in the printed/exported reports.
        ***Optional***

    Outputs:
        Custom_Material: Outputs a class object (CustomMaterial) containing all of the embedded material attributes:
        (name, energy, water, ghg, functional_unit, doi, category, material_id, wastage, service_life, comments)
        ***Connect that output to a panel for a summary***

        Embodied_Energy_Coefficient_(MJ/FU): The Embodied Energy Coefficient for this material.
        Note this does not include wastage in the calculation

        Embodied_Water_Coefficient_(L/FU): The Embodied Water Coefficient for this material.
        Note this does not include wastage in the calculation

        Embodied_GHG_Coefficient_(kgCO₂e/FU): The Embodied Greenhouse Gas Emissions Coefficient for this material.
        Note this does not include wastage in the calculation

        Density_(kg/m³): Material density, as provided in the EPiC Database

        Functional_Unit: Functional Unit, as provided in the EPiC Database

        Wastage_Coefficient_(%): Estimated wastage percentage (%) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates no wastage, 100 indicates 100% wastage

        Material_Service_Life_(Years): Estimated service_life (in years) for the material.
        This will use the default value for the material (if it exists in the database), otherwise it will default to 0.
        0 indicates that the material will never need to be replaced
"""

from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
from ghpythonlib.componentbase import executingcomponent as component

import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)


class EPiCCustomMaterialComponent(component):

    def RunScript(self, name, category, _null, functional_unit, density, _null2, energy, water, ghg, _null3,
                  wastage, service_life, comments):

        # Component and version information
        __author__ = epic.__author__
        __version__ = "1.01"
        if __version__ == epic.__version__:
            self.Message = epic.__message__
        else:
            self.Message = epic.version_mismatch(__version__)
            self.AddRuntimeMessage(RML.Remark, self.Message)
        self.Name = "EPiC Custom Material"
        self.NickName = "EPiC Custom Material"

        # Create attribute values if none exist for custom material
        name = 'Custom Material' if not name else name
        density = 0 if not density else density
        wastage = 0 if not wastage else wastage
        service_life = 0 if not service_life else service_life
        comments = '' if not comments else comments
        warning = None

        # check if functional unit is acceptable
        if functional_unit is not None:
            warning, functional_unit = epic.check_functional_unit_and_return_formatted_version(str(functional_unit))
            if warning:
                self.AddRuntimeMessage(RML.Warning, warning)
                return [warning] * 7

        # Output CustomMaterial class object if inputs have been provided
        if None not in (functional_unit, energy, ghg, water):
            output_epic_material = epic.CustomMaterial(name=name, water=water, ghg=ghg, energy=energy,
                                                       functional_unit=functional_unit, category=category,
                                                       wastage=wastage, service_life=service_life,
                                                       comments=comments, density=density)
            return output_epic_material, None, output_epic_material.energy, output_epic_material.water, \
                   output_epic_material.ghg, None, output_epic_material.density, output_epic_material.functional_unit, \
                   wastage, service_life

        # Output error message if inputs not provided
        else:
            warning = 'Provide required inputs, specified with ** (functional_unit, energy, ghg, water)'
            self.AddRuntimeMessage(RML.Warning, warning)
            return [warning] * 7
