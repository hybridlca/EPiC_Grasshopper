# -*- coding: UTF-8 -*-
# EPiC Grasshopper: A Plugin for analysing embodied environmental flows
#
# Copyright (c) 2022, EPiC Grasshopper.
# You should have received a copy of the GNU General Public License
# along with EPiC Grasshopper; If not, see <http://www.gnu.org/licenses/>.
#
# Further information about the EPiC Database can be found at <https://bit.ly/EPiC_Database>
# To download a full copy of the database, goto <http://doi.org/10.26188/5dc228ef98c5a>
#
# @license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>

"""
Calculates Embodied Environmental Flows and plots a stacked bar chart of the results, with the ability to generate a csv report

    Inputs:

        Analysis_Name: Name for the Analysis Report
        ***Optional***

        **EPiC_Assemblies_or_Built_Assets: Input EPiC_Assembly and/or EPiC_Built_Asset items for built_assets
        (**REQUIRED)

        Comparison_Values_(EPiC_Assemblies): Input EPiC_Assembly items to compare (not shown in .csv report)
        ***Optional***

        Period_of_Analysis_(Years): The period of analysis to be used for calculations.
        Default value of None - indicating that no recurrent calculations will be made.
        ***Optional***

        >>Connect_Button_to_Load_Analysis_Types: Connect and activate a button.
        This will generate a dropdown list for the Analysis Type input

        Analysis_Type: Input the type of built_assets to be used for graph visualisations.
        Possible inputs include: 'total', 'by_material', 'by_assembly', or 'by_assembly_and_material'
        Defaults to: 'total'
        ***Optional***

        Graph_Origin_Point: Specify the origin point for graph visualisations. Defaults to 0,0,0.
        ***Optional***

        Graph_Scale: Specify the scale of the graph visualisations. 1=normal size, 0.5=half size, 2=double size
        ***Optional***

        csv_Folder_location: Folder location for generation of a csv report. Use the 'path' object in grasshopper
        (**REQUIRED for report generation)

        >>Connect_Button_to_Generate_csv: Connect a Button to Generate the csv. report

    Outputs:
        Detailed_Report_Information: Detailed report information
        ***Connect that output to a panel for a summary***

        Graph_Outputs: Outputs a list of bakeable geometry for the graph visualisation

        Output_Breakdown: Text detailing the flow outputs, depending on the analysis type.
        For 'by_assembly_and_by_material' this will be a nested list

        Initial_Embodied_Energy_(MJ): Initial Embodied Energy (MJ)
        This includes wastage

        Initial_Wastage_Embodied_Energy_(MJ): Initial Wastage Embodied Energy (MJ)

        Recurrent_Embodied_Energy_(MJ): Recurrent Embodied Energy (MJ)
        This includes wastage

        Recurrent_Wastage_Embodied_Energy_(MJ): Recurrent Wastage Embodied Energy (MJ)

        Life_Cycle_Embodied_Energy_(MJ): Life Cycle Embodied Energy (MJ)
        This includes initial, recurrent, and wastage flows

        Life_Cycle_Wastage_Embodied_Energy_(MJ): Life Cycle Wastage Embodied Energy (MJ)

        Initial_Embodied_Water_(L): Initial Embodied Water (L)
        This includes wastage

        Initial_Wastage_Embodied_Water_(L): Initial Wastage Embodied Water (L)

        Recurrent_Embodied_Water_(L): Recurrent Embodied Water (L)
        This includes wastage

        Recurrent_Wastage_Embodied_Water_(L): Recurrent Wastage Embodied Water (L)

        Life_Cycle_Embodied_Water_(L): Life Cycle Embodied Water (L)
        This includes initial, recurrent, and wastage flows

        Life_Cycle_Wastage_Embodied_Water_(L): Life Cycle Wastage Embodied Water (L)

        Initial_Embodied_GHG_(kgCO₂e): Initial Embodied GHG (kgCO₂e)
        This includes wastage

        Initial_Wastage_Embodied_GHG_(kgCO₂e): Initial Wastage Embodied GHG (kgCO₂e)

        Recurrent_Embodied_GHG_(kgCO₂e): Recurrent Embodied GHG (kgCO₂e)
        This includes wastage

        Recurrent_Wastage_Embodied_GHG_(kgCO₂e): Recurrent Wastage Embodied GHG (kgCO₂e)

        Life_Cycle_Embodied_GHG_(kgCO₂e): Life Cycle Embodied GHG (kgCO₂e)
        This includes initial, recurrent, and wastage flows

        Life_Cycle_Wastage_Embodied_GHG_(kgCO₂e): Life Cycle Wastage Embodied GHG (kgCO₂e)

        Geometry_by_Assembly: A collection of all selected geometries for each EPiC Assembly (including within EPiC Built Assets)

"""

import os.path as path
from collections import OrderedDict

from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
from Rhino import RhinoApp
from ghpythonlib.componentbase import executingcomponent as component

import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)
no_inputs_warning = "No assemblies nor built assets linked, lease input assemblies and/or built assets"


class EPiCAnalysisComponent(component):
    def RunScript(self, report_name, epic_inputs, period_of_analysis, _null, analysis_button,
                  analysis_type, graph_origin, graph_scale, _null2, folder_location, button):

        # Component and version information
        __author__ = epic.__author__
        __version__ = "1.00"
        if __version__ == epic.__version__:
            self.Message = epic.__message__
        else:
            self.Message = epic.version_mismatch(__version__)
            self.AddRuntimeMessage(RML.Remark, self.Message)
        self.Name = "EPiC Analysis"
        self.NickName = "EPiC Analysis"

        # Remove any file names from folder path
        if folder_location:
            folder_location = path.dirname(folder_location)

        # Component variables
        analysis_types = OrderedDict([('Total', 'total'),
                                      ('By Material', 'by_material'),
                                      ('By Assembly', 'by_assembly'),
                                      ('By Assembly and material', 'by_assembly_and_material')])

        # Default name for built_assets report
        report_name = 'EPiC Analysis' if not report_name else report_name

        # Default name for EPiC_Assembly inputs
        epic_assemblies_name = 'Assembly Collection'
        if analysis_button:
            epic.make_value_list_input_component(5, analysis_types.values(), ghenv,
                                                 valuelist_names=analysis_types.keys(),
                                                 xloc=-170,
                                                 yloc=10)

        if epic_inputs:
            # Process the built_assets inputs and create an EPiCAnalysis class instance
            epic_analysis, epic_inputs = epic.EPiCAnalysis.process_inputs(epic_inputs,
                                                                          analysis_type,
                                                                          graph_origin=graph_origin,
                                                                          graph_scale=graph_scale,
                                                                          period_of_analysis=period_of_analysis,
                                                                          report_name=report_name,
                                                                          epic_assemblies_name=epic_assemblies_name)
            # Create CSV report when button is pressed
            if button and folder_location:
                message = epic.print_csv(report_name, folder_location, period_of_analysis, epic_analysis, epic_inputs)
                RhinoApp.WriteLine(message)

            # Generate component outputs depending on the analysis_type
            return epic_analysis.generate_analysis_breakdown_for_outputs(analysis_type=analysis_type)
        else:
            self.AddRuntimeMessage(RML.Warning, "Input EPiCAssembly or EPiCBuiltAsset items for built_assets")
