# -*- coding: UTF-8 -*-

import copy
import datetime
import os.path
from collections import OrderedDict
from math import sqrt, floor, ceil, log10, isnan
from scriptcontext import sticky as st
import Grasshopper.Kernel as ghKernel
import cPickle
import ghpythonlib.components as ghcomponents
import rhinoscriptsyntax as rs
from Grasshopper import DataTree
from Rhino import Display
from Rhino import Geometry
from System import Drawing
from System import Guid
from System.Drawing import Color
import os
import random

__author__ = "André Stephan & Fabian Prideaux"
__version__ = "1.02"
__date__ = 'May, 2024'
__message__ = 'EPiC Plugin ' + __version__ + '\n' + __date__
epic_version = 'AU2024'
EPIC_DATABASE_WEBSITE = 'http://www.msd.unimelb.edu.au/epic'
REPORT_A_BUG = 'https://bit.ly/EPiCGrasshopperBugs'
DISCLAIMER = """ 
The default service life and wastage coefficients are indicative only and can vary substantially. 

The authors disclaim any liability, in whole or in part, arising from information contained in this plugin.
They do not take any responsibility for any action taken, decision-made, or result associated with use of this plugin

Further information about the EPiC Database and EPiC Grasshopper can be found at <http://www.epicdatabase.com.au/>
To download a full copy of the database, goto <http://doi.org/10.26188/5dc228ef98c5a>
"""

# Colour scheme used for EPiC Grasshopper / EPiC Database
COLOURS = {
    'light_teal': Color.FromArgb(124, 189, 206),
    'teal': Color.FromArgb(63, 167, 196),
    'light_orange': Color.FromArgb(255, 164, 120),
    'orange': Color.FromArgb(231, 112, 82),
    'light_yellow': Color.FromArgb(255, 220, 162),
    'yellow': Color.FromArgb(236, 174, 101),
    'light_green': Color.FromArgb(152, 214, 195),
    'green': Color.FromArgb(89, 177, 127),
    'grey': Color.FromArgb(153, 162, 170),
    'dark_grey': Color.FromArgb(100, 100, 100),
    'light_blue': Color.FromArgb(173, 205, 240),
    'blue': Color.FromArgb(64, 116, 178),
    'light_purple': Color.FromArgb(176, 188, 225),
    'purple': Color.FromArgb(114, 131, 191),
    'light_pink': Color.FromArgb(255, 189, 204),
    'pink': Color.FromArgb(238, 136, 137)
}

# Generic variables used throughout
DEFINED_FLOWS = OrderedDict()
DEFINED_FLOWS['energy'] = {'code_name': 'energy', 'print_name': 'Energy', 'unit': 'MJ',
                           'colour': COLOURS['orange'], 'secondary_colour': COLOURS['light_orange']}
DEFINED_FLOWS['water'] = {'code_name': 'water', 'print_name': 'Water', 'unit': 'L',
                          'colour': COLOURS['teal'], 'secondary_colour': COLOURS['light_teal']}
DEFINED_FLOWS['ghg'] = {'code_name': 'ghg', 'print_name': 'Greenhouse Gas Emissions', 'unit': 'kgCO₂e',
                        'colour': COLOURS['yellow'], 'secondary_colour': COLOURS['light_yellow']}

HYBRID_VALUE_BREAKDOWN_DICT = {flow: {'process': None, 'io': None} for flow in DEFINED_FLOWS.keys()}

# Generic epic categories
EPIC_CATEGORIES = [
    "0: Concrete and plaster products",
    "1: Glass",
    "2: Insulation",
    "3: Metals",
    "4: Miscellaneous",
    "5: Plastics",
    "6: Sand, stone and ceramics",
    "7: Timber products"]

PICKLE_DB = "EPiC_Database_2024.pkl"


def remove_commas_and_flatten_list_for_csv_export(text_inputs, list_separator=' | ',
                                                  remove_spaces=False, limit_characters=False):
    """
    Remove any commas from text provided. Flatten if provided as a list of multiple strings.
    :param text_inputs: a string, or list of strings
    :param list_separator: separator (string) to use if a list is provided
    :param remove_spaces: change spaces to underscores
    :param limit_characters: limit string to 50 characters
    :return: string
    """
    if isinstance(text_inputs, list):
        flat_text = list_separator.join(text_inputs).replace(",", " ")
    elif isinstance(text_inputs, str):
        flat_text = text_inputs.replace(",", " ")
    else:
        return text_inputs

    if remove_spaces:
        flat_text = flat_text.replace(' ', '_')

    if limit_characters:
        flat_text = flat_text[:50]

    return flat_text


def version_mismatch(component_version):
    """
    Display error message if grasshopper component is a different version to epic.py
    :param component_version: Grasshopper component version
    :return: Error message as string
    """
    error = '*** WARNING VERSION MISMATCH, PLEASE UPDATE YOUR USER OBJECTS ***\n' \
            'DOWNLOAD NEW USER OBJECTS AND COPY + PASTE THE NEW CODE INTO THIS COMPONENT\n' \
            'EPiC Plugin version: {}\n' \
            'Component version: {}'.format(__version__, component_version)
    return error


def check_functional_unit_and_return_formatted_version(functional_unit):
    """
    Check the functional unit and return correctly formatted funcational unit.
    Will generate warning if incorrect input is used
    :param functional_unit: Functional unit for EPiC/Custom Material
    :return: warning message (or None), and formatted functional unit string
    """
    warning = None
    if functional_unit and isinstance(functional_unit, str):
        functional_unit = str(functional_unit).lower()
        if functional_unit in ('m', 'm²', 'm³', 'no.', 'm2', 'm3'):
            if functional_unit == 'm2':
                functional_unit = 'm²'
            elif functional_unit == 'm3':
                functional_unit = 'm³'
            else:
                pass
    else:
        warning = 'The functional unit can only be "m", "m²", "m³", "kg" or "no." ' \
                  '("m2" or "m3" are accepted and will be corrected).'
    return warning, functional_unit


def make_value_list_input_component(input_node, valuelist_values, ghenv, nickname=None, valuelist_names=None,
                                    xloc=0, yloc=0):
    # type: (int, list, object, str, list, int, int) -> str
    """
    Instantiate a new valuelist element in Grasshopper (dropdown list).
    This new valuelist will be connected to the specified component, with preset list of values
    :param input_node: Specify the input node number (in integers)
    :param valuelist_values: List of values to be used in the dropdown list
    :param ghenv: The current grasshopper running environment
    :param nickname: Nickname for the new component
    :param valuelist_names: List of names to be used in the dropdown list
    :param xloc: Move component to the left (negative value) / right (positive value)
    :param xloc: Move component up (negative value) / down (positive value)
    :return: new valuelist Instance Guid
    """
    # Ensure that the component expires, so that values load correctly
    # ghenv.Component.ExpireSolution(True)

    # Check if component already has input
    if ghenv.Component.Params.Input[input_node].SourceCount == 0:

        # Instantiate new value list
        new_component = ghKernel.Special.GH_ValueList()

        # Set up default values for the new component
        new_component.CreateAttributes()

        # Clear any existing list items
        new_component.ListItems.Clear()
        if nickname is not None:
            new_component.NickName = nickname

        if not xloc:
            xloc = max([len(x) for x in valuelist_values]) * -5 - 100

        # If no valuelist_names, or the list size is different, then use the values as a default
        if not valuelist_names or len(valuelist_names) != len(valuelist_values):
            valuelist_names = valuelist_values

        #  Populate the new valuelist with items from the selected category
        for num, vals in enumerate(valuelist_values):
            new_component.ListItems.Add(ghKernel.Special.GH_ValueListItem(str(valuelist_names[num]), '"'
                                                                          + str(valuelist_values[num]) + '"'))

        new_component.Attributes.Pivot = Drawing.PointF(ghenv.Component.Params.Input[input_node].Attributes.Bounds.X
                                                        + xloc - new_component.Attributes.Bounds.Width,
                                                        ghenv.Component.Params.Input[input_node].Attributes.Bounds.Y
                                                        + yloc)

        # Add valuelist to canvas
        ghdoc = ghenv.Component.OnPingDocument()
        ghdoc.AddObject(new_component, False)

        # Connect valuelist to component
        ghenv.Component.Params.Input[input_node].AddSource(new_component)
        ghenv.Component.Params.OnParametersChanged()

        def expire_solution():
            ghenv.Component.ExpireSolution(False)

        ghdoc.ScheduleSolution(5, expire_solution())

        return str(new_component.InstanceGuid)


def sum_numerical_dictionary_values(dict_1, dict_2):
    """
    Sum together 2 dictionaries (if values are int / float).
    :param dict_1: First dictionary (this will be used as the base dictionary).
    :param dict_2: Second dictionary to merge
    :return: New dictionary with summed values
    """
    dict_3 = copy.deepcopy(dict_1)
    for key, value in dict_2.items():
        if isinstance(value, (int, float)):
            dict_3[key] += value
        elif isinstance(value, (dict)):
            dict_3[key] = sum_numerical_dictionary_values(dict_3[key], dict_2[key])
    return dict_3


def list_to_datatree(nestedlist):
    """ Convert a nested python iterable to a datatree
    Adapted from code by Anders Deluran (2017)
    from https://discourse.mcneel.com/t/outputting-a-nested-python-list-as-tree/48188
    """

    dt = DataTree[object]()

    # Convert dictionary to list if needed
    if isinstance(nestedlist, dict):
        nestedList = nestedlist.values()

    if nestedlist:
        for i, l in enumerate(nestedlist):
            dt.AddRange(l, ghKernel.Data.GH_Path(i))
    else:
        return None
    return dt


def _flatten_list(list_of_lists):
    """
    Recursive function to iterate through list of lists and return a flattened list of objects
    :param list_of_lists: A list containing nested lists
    :return: A flattened list (no nested lists)
    """
    list_vals = []
    for list_item in list_of_lists:
        if isinstance(list_item, list):
            list_vals += _flatten_list(list_item)
        else:
            list_vals.append(list_item)
    return list_vals


def _get_accumulated_number_of_instances(period_of_analysis, service_life, include_initial=True):
    """
    Generates a list representing the number of replacements of a material or assembly to date. The length of that list is
    equal to period of built_assets
    :param period_of_analysis: the period of built_assets in years
    :param service_life: the service of the material or assembly
    :param include_initial: boolean flag that specifies if the initial installation should be included
    :return: a list of integers representing the accumulated number of material/assembly in the building at a given year
    """

    if include_initial:
        acc_num_instances = [1] * period_of_analysis
    else:
        acc_num_instances = [0] * period_of_analysis

    num_replacements = _get_num_replacements(period_of_analysis=period_of_analysis, service_life=service_life)

    if num_replacements == 0:
        pass
    else:
        for replacement in range(1, num_replacements + 1):
            acc_num_instances[replacement * service_life:] = [num_instances + 1 for num_instances in
                                                              acc_num_instances[replacement * service_life:]]

    return acc_num_instances


def _get_num_replacements(period_of_analysis, service_life):
    """
    Calculates the number of material replacements
    :param period_of_analysis: the period of built_assets in years
    :param service_life: the service_life in years
    :return: an integer, representing the number of replacements
    """
    if service_life >= period_of_analysis:
        return 0
    else:
        if period_of_analysis % service_life == 0:
            return period_of_analysis // service_life - 1
        else:
            return period_of_analysis // service_life


def print_csv(report_name, folder_location, period_of_analysis, analysis, epic_assemblies):
    """
    Print a csv report based on an EPiCAnalysis component
    :param report_name: Name of report to generate
    :param folder_location: Folder location pathway
    :param period_of_analysis: The period of built_assets for the life cycle assessment report
    :param analysis: EPiCAnalysis objects that are used for the csv report
    :param epic_assemblies: EPiCAssembly objects that are used for the csv report
    """

    message = "FAILED TO WRITE CSV. Folder location:" + folder_location
    report_name = remove_commas_and_flatten_list_for_csv_export(report_name, list_separator='_',
                                                                remove_spaces=True) \
        if report_name else 'EPiC Assembly'
    if not folder_location:
        raise ValueError('No folder location provided')

    counter = 1

    filepath = os.path.join(folder_location, report_name + '.csv')

    # Check if the file already exists. If so, rename. Maximum of 50 versions
    if os.path.exists(filepath):
        while os.path.exists(filepath) and counter < 50:
            counter += 1
            filepath = os.path.join(folder_location, report_name + '_' + str(counter) + '.csv')

    # Separate epic assemblies and built assets
    epic_built_assets = [x for x in epic_assemblies if x and x.component_type == 'EPiCBuiltAsset'
                         or x.component_type == 'EPiCAnalysis']
    epic_assemblies = [x for x in epic_assemblies if x and x.component_type == 'EPiCAssembly']

    with open(filepath, 'wb') as csv:
        _write_report_details_to_csv(csv, period_of_analysis, report_name)
        _write_flow_values_to_csv(analysis, csv)

        if len(epic_built_assets) > 0:
            _write_built_asset_flow_values_to_csv(epic_built_assets, csv)

        if len(epic_assemblies) > 0:
            _write_assembly_flow_info_to_csv(csv)
            _write_assembly_flows_to_csv(epic_assemblies, csv)

        _write_boq_to_csv(csv, analysis)
        message = "Successfully printed to .csv file: " + filepath
    return message


def _write_report_details_to_csv(csv, period_of_analysis, report_name):
    """
    Write report details to .csv file.
    :param csv: The csv file to write to
    :param period_of_analysis: Period of analysis for the report in years
    :param report_name: Name of the report (EPiCAnalysis name)
    """
    # csv.write('                                                 @@@@                          \n')
    # csv.write(' /////////////////      ///////////////         @@@@@@          ////////////   \n')
    # csv.write(' /////////////////      //////////////////       @@@@        ///////////////// \n')
    # csv.write(' /////                  /////         /////                 /////              \n')
    # csv.write(' /////                  /////          ////     /////      /////               \n')
    # csv.write(' /////                  /////         /////     /////     /////                \n')
    # csv.write(' ///////////////        /////     ////////      /////     /////                \n')
    # csv.write(' /////                  ////////////////        /////     //////               \n')
    # csv.write(' /////                  /////                   /////      /////               \n')
    # csv.write(' /////                  /////                   /////       /////              \n')
    # csv.write(' /////////////////      /////                   /////        ///////////////// \n')
    # csv.write(' /////////////////      /////                   /////           ////////////   \n')
    # csv.write('\n')
    csv.write(
        'This is a report generated by EPiC Grasshopper: A plugin for analysing hybrid embodied environmental flows')
    csv.write('\nReport date: ' + datetime.datetime.now().strftime("%d %B %Y"))
    csv.write('\nTime: ' + datetime.datetime.now().strftime("%H:%M"))
    csv.write('\n\nPlugin Version: ' + __version__)
    csv.write('\nEPiC Database Version: ' + epic_version)
    csv.write('\nThe authors disclaim any liability - in whole or in part - arising from information contained '
              'in this report.'
              '\nThey do not take any responsibility for any action taken - decision-made - or result '
              'associated with use of this plugin'
              '\n*Default service life and wastage coefficients are indicative only and can vary substantially.'
              '\nFurther information about the EPiC Database and EPiC Grasshopper can be found at: '
              '<http://www.epicdatabase.com.au/> '
              '\nTo download a full copy of the database - goto <http://doi.org/10.26188/5dc228ef98c5a>'
              '\n_______________________________________________________________________________________')
    csv.write('\n\n' + report_name)
    csv.write('\nPeriod of Analysis: {} years \n'.format(period_of_analysis))
    csv.write('\n')


def _write_flow_values_to_csv(analysis, csv):
    """
    Write to a .csv file. Include the total flow values for the analysis object, all assemblies and built asset objects
    :param analysis: EPiCAnalysis class object for calculations
    :param csv: The csv file to write to
    """

    # Life Cycle Total = lc
    lc_energy = analysis.flows['life_cycle']['energy']
    lc_water = analysis.flows['life_cycle']['water']
    lc_ghg = analysis.flows['life_cycle']['ghg']

    # Total Initial (excl. wastage) = i
    i_energy = analysis.flows['initial']['energy'] - analysis.flows['initial_wastage']['energy']
    i_water = analysis.flows['initial']['water'] - analysis.flows['initial_wastage']['water']
    i_ghg = analysis.flows['initial']['ghg'] - analysis.flows['initial_wastage']['ghg']

    # Initial Wastage = iw
    iw_energy = analysis.flows['initial_wastage']['energy']
    iw_water = analysis.flows['initial_wastage']['water']
    iw_ghg = analysis.flows['initial_wastage']['ghg']

    # Total Recurrent (excl. wastage) = r
    r_energy = analysis.flows['recurrent']['energy'] - analysis.flows['recurrent_wastage']['energy']
    r_water = analysis.flows['recurrent']['water'] - analysis.flows['recurrent_wastage']['water']
    r_ghg = analysis.flows['recurrent']['ghg'] - analysis.flows['recurrent_wastage']['ghg']

    # Total Recurrent Wastage = rw
    rw_energy = analysis.flows['recurrent_wastage']['energy']
    rw_water = analysis.flows['recurrent_wastage']['water']
    rw_ghg = analysis.flows['recurrent_wastage']['ghg']

    # Write Values to csv
    csv.write('{},{},{},{}\n'.format('', 'Total Energy (MJ)', 'Total Water (L)', 'Total GHG (kgCO2e)'))
    csv.write('{},{},{},{},{}\n'.format('Life Cycle Total', lc_energy, lc_water, lc_ghg, ''))
    csv.write('{},{},{},{},{}\n'.format('>> Total Initial (excl. wastage)', i_energy, i_water, i_ghg, ''))
    csv.write('{},{},{},{},{}\n'.format('>>>> Total Initial Wastage', iw_energy, iw_water, iw_ghg, ''))
    csv.write('{},{},{},{},{}\n'.format('>> Total Recurrent (excl. wastage)', r_energy, r_water, r_ghg, ''))
    csv.write('{},{},{},{},{}\n'.format('>>>> Total Recurrent Wastage', rw_energy, rw_water, rw_ghg, ''))
    csv.write('\n\n')


def _write_built_asset_flow_values_to_csv(built_assets, csv):
    """
    Write to a .csv file. For each build asset object, write a new section listing all of the flow values.
    :param built_assets: EPiCBuiltAsset items to include in the analysis
    :param csv: The csv file to write to
    """
    csv.write('*** BREAKDOWN BY BUILT ASSET ***\n\n')
    csv.write('{},{},{},{},{},{},{}\n'.format('', 'Total Energy (MJ)', 'Total Water (L)', 'Total GHG (kgCO2e)',
                                              'Qty', 'Functional Unit', 'Comments'))

    for built_asset in built_assets:
        built_asset_name = '<<-' + built_asset.name.replace(",", ".") + '->>'
        csv.write('\n')
        if built_asset.comments:
            csv.write('{},{},{},{},{},{},{}\n'.format(built_asset_name, '', '', '', '',
                                                      '', built_asset.comments.replace(",", ".")))
        else:
            csv.write(built_asset_name)

        csv.write('\n')
        _write_assembly_flows_to_csv(built_asset.epic_assemblies, csv)


def _write_assembly_flow_info_to_csv(csv):
    """
    Write to a .csv file. The title for the assembly section, and all column headings.
    :param csv: The csv file to write to
    """
    csv.write('*** BREAKDOWN BY ASSEMBLIES ***\n\n')
    csv.write('{},{},{},{},{},{},{}\n'.format('', 'Total Energy (MJ)', 'Total Water (L)', 'Total GHG (kgCO2e)',
                                              'Qty', 'Functional Unit', 'Comments'))


def _write_assembly_flows_to_csv(assemblies, csv):
    """
    Write to a .csv file. For each assembly item, write a new section listing all of the flow values, by material.
    :param assemblies: EPiCAssembly items to include in the analysis
    :param csv: The csv file to write to
    """
    for assembly in assemblies:
        if not assembly.comments:
            assembly.comments = ' '
        if len(assembly.selected_geometry) > 0 and assembly.total_units > 0:
            if assembly.category == assembly.name: # no category has been defined
                built_asset_name = "<{} ({} {})>".format(assembly.name.replace(",", "."),
                                                                      str(assembly.total_units),
                                                                      str(assembly.assembly_units))
            else:
                built_asset_name = "<{} | Category: {} ({} {})>".format(assembly.name.replace(",", "."),
                                                                      assembly.category.replace(",", "."),
                                                                      str(assembly.total_units),
                                                                      str(assembly.assembly_units))

            csv.write('{},{},{},{},{},{},{}\n'.format(built_asset_name, '', '', '', '', '',
                                                      assembly.comments.replace(",", ".")))
            for mat in assembly.recalculated_flows['by_material'].values():
                csv.write('{},{},{},{},{},{},{}\n'.format(mat['material_name'].replace(",", ".").encode('utf-8'),
                                                          '', '', '', (mat['quantity'] * assembly.total_units),
                                                          mat['material_object'].functional_unit,
                                                          mat['material_object'].comments))
                csv.write('{},{},{},{},{}\n'.format('>> Initial (excl. wastage)', mat['initial']['energy']
                                                    - mat['initial_wastage']['energy'], mat['initial']['water']
                                                    - mat['initial_wastage']['water'], mat['initial']['ghg']
                                                    - mat['initial_wastage']['ghg'], ''))

                if mat['initial_wastage']['energy'] > 0:
                    csv.write('{},{},{},{},{}\n'.format('>>>> Initial Wastage (' + str(
                        (mat['initial_wastage']['energy'] * 100) / mat['initial']['energy']) + '%)',
                                                        mat['initial_wastage']['energy'],
                                                        mat['initial_wastage']['water'],
                                                        mat['initial_wastage']['ghg'],
                                                        ''))

                if (mat['recurrent']['energy']) > 0:
                    csv.write('{},{},{},{},{}\n'.format('>> Recurrent (excl. wastage)',
                                                        mat['recurrent']['energy']
                                                        - mat['recurrent_wastage']['energy'],
                                                        mat['recurrent']['water']
                                                        - mat['recurrent_wastage']['water'],
                                                        mat['recurrent']['ghg']
                                                        - mat['recurrent_wastage']['ghg'], ''))

                if (mat['recurrent_wastage']['energy']) > 0:
                    csv.write('{},{},{},{},{}\n'.format('>>>> Recurrent Wastage',
                                                        mat['recurrent_wastage']['energy'],
                                                        mat['recurrent_wastage']['water'],
                                                        mat['recurrent_wastage']['ghg'], ''))
            csv.write('\n')


def _write_boq_to_csv(csv, analysis):
    """
    Write to a .csv file. Sum the total quantity for each material in all of the assemblies and built assets,
    :param analysis: :param analysis: EPiCAnalysis class object for calculations
    :param csv: The csv file to write to
    """
    boq = {}
    for mat in analysis.epic_materials:
        if str(mat[0].name) not in boq:
            boq[mat[0].name] = {'units': mat[0].functional_unit,
                                'total_units': mat[1]}
        else:
            boq[mat[0].name]['total_units'] += mat[1]

    csv.write('*** MATERIAL BOQ *** \n\n')
    csv.write('Material Name, Qty, Units \n')
    for x in boq:
        csv.write(
            '{}, {}, {} \n'.format(x.replace(",", ".").encode('utf-8'), boq[x]['total_units'],
                                   boq[x]['units']))


class EPiCVisualisations:
    """
    Custom geometry to be visualised in Grasshopper. This class stores all visualisation classes.
    """

    def __init__(self):
        pass

    class GraphSegmentGeometry(ghKernel.Types.GH_GeometricGoo[Geometry.Rectangle3d],
                               ghKernel.IGH_BakeAwareData, ghKernel.IGH_PreviewData):
        def __init__(self, rect, fill_colour=COLOURS['light_teal'], outline_colour=COLOURS['dark_grey'],
                     outline_thickness=1, show_hatch=False):
            """
            A custom coloured rectangle that represents a graph segment within EPiCGraphColumn.
            This class overrides DrawViewportWires and DrawViewportMeshes
            :param rect: A Rhino 3D Rectangle Object to be used as a base object
            """

            # Set the initial attributes
            self.m_value = rect
            self.fill_colour = fill_colour
            self.outline_colour = outline_colour
            self.outline_thickness = outline_thickness
            self.show_hatch = show_hatch

            # Create a fill and outline for the rectangle
            self.poly_line = self.m_value.ToPolyline()
            self.fill = Geometry.Hatch.Create(self.poly_line.ToPolylineCurve(), 0, 0, 0, 0)
            self.fill = self.fill[0]

        # region properties for grasshopper.
        def get_TypeName(self):
            return "Graph Segment"

        def get_TypeDescription(self):
            return "Graph Segment"

        def ToString(self):
            if self.m_value is None: return "<null>"
            return 'Graph Segment'

        def get_Boundingbox(self):
            if self.m_value is None:
                return Geometry.BoundingBox.Empty
            return self.m_value.BoundingBox

        def GetBoundingBox(self, xform):
            if self.m_value is None:
                return Geometry.BoundingBox.Empty
            box = self.m_value.BoundingBox
            corners = xform.TransformList(box.GetCorners())
            return Geometry.BoundingBox(corners)

        # region methods for grasshopper.
        def DuplicateGeometry(self):
            new_geometry = EPiCVisualisations.GraphSegmentGeometry(self.m_value)
            new_geometry.fill_colour = self.fill_colour
            new_geometry.outline_colour = self.outline_colour
            new_geometry.outline_thickness = self.outline_thickness
            new_geometry.show_hatch = self.show_hatch
            return new_geometry

        def Transform(self, xform):
            rect = self.m_value
            if rect is None: return EPiCVisualisations.GraphSegmentGeometry(None)

            plane = rect.Plane
            point = plane.PointAt(1, 1)

            plane.Transform(xform)
            point.Transform(xform)
            dd = point.DistanceTo(plane.Origin)

            new_geometry = EPiCVisualisations.GraphSegmentGeometry(
                Geometry.Rectangle3d(plane, rect.Width * dd / sqrt(2), rect.Height * dd / sqrt(2)))
            new_geometry.fill_colour = self.fill_colour
            new_geometry.outline_colour = self.outline_colour
            new_geometry.outline_thickness = self.outline_thickness
            new_geometry.show_hatch = self.show_hatch
            return new_geometry

        def Morph(self, xmorph):
            return self.DuplicateGeometry()

        # region preview properties for grasshopper.
        def get_ClippingBox(self):
            return self.get_Boundingbox()

        def DrawViewportWires(self, args):
            args.Pipeline.DrawBox(self.m_value.BoundingBox, self.outline_colour, self.outline_thickness)
            if self.show_hatch:
                corners = self.m_value.BoundingBox.GetCorners()
                args.Pipeline.DrawLine(Geometry.Line(Geometry.Point3d(corners[0]), Geometry.Point3d(corners[2])),
                                       self.outline_colour)
                args.Pipeline.DrawLine(Geometry.Line(Geometry.Point3d(corners[1]), Geometry.Point3d(corners[3])),
                                       self.outline_colour)

        def DrawViewportMeshes(self, args):
            args.Pipeline.DrawHatch(self.fill, self.fill_colour, Color.Transparent)

        # region baking for grasshopper.
        def BakeGeometry(self, doc, att, id):
            id = Guid.Empty
            if self.m_value is None:
                return False, id

            if att is None:
                att = doc.CreateDefaultAttributes()
            att.ObjectColor = self.fill_colour
            doc.Objects.AddRectangle(self.m_value, att)
            hatch_att = doc.CreateDefaultAttributes()
            hatch_att.ObjectColor = self.fill_colour
            doc.Objects.AddHatch(self.fill, hatch_att)
            id = doc.Objects

            return True, id

    @staticmethod
    def bakeable_text_from_str(text, text_size=1.0, text_location=(0, 0, 0), bold=False, italic=False, font='Arial',
                               text_rotation=0,
                               align_right=False, align_top=False):
        """
        Create bakeable text objects from string inputs
        :param text: Input string
        :param text_size: Size of the text, measured in Rhino units
        :param text_location: Location for the text. Defaults to (0,0,0)
        :param bold: If True, then the text will be bold
        :param italic: If True, then the text will be italic
        :param font: Font to use (default is Arial)
        :param text_rotation: Rotation angle for the text (in degrees)
        :param align_right: If True, then the text will be aligned to the right
        :param align_top: If True, then the text will be aligned to the top
        :return: EPiCText class object that can be visualised and baked from grasshopper
        """

        # Create a base plane for the text
        point = rs.AddPoint(*text_location)
        point2 = rs.AddPoint(10, 0, 0)
        point3 = rs.AddPoint(0, 10, 0)
        plane = rs.CreatePlane(point, point2, point3)

        # Rotate the text
        if text_rotation:
            plane = rs.RotatePlane(plane, text_rotation, plane.ZAxis)

        # Check if text input is a string, and convert to a Text3D object
        if isinstance(text, str):
            text = Display.Text3d(text, plane, text_size)
        elif isinstance(text, Display.Text3d):
            pass
        else:
            raise TypeError("bakeable_text_from_str: text input must be string or Text3D")

        if align_right:
            text_bounds_length = EPiCVisualisations.EPiCText(text).get_Boundingbox().GetEdges()[0].Length
            plane = rs.MovePlane(plane, (text_location[0] - text_bounds_length, text_location[1], text_location[2]))
            text = Display.Text3d(text.Text, plane, text_size)

        if align_top:
            text_bounds_length = EPiCVisualisations.EPiCText(text).get_Boundingbox().GetEdges()[1].Length
            plane = rs.MovePlane(plane, (text_location[0], text_location[1] - text_bounds_length, text_location[2]))
            text = Display.Text3d(text.Text, plane, text_size)

        text.Bold = bold
        text.Italic = italic
        text.FontFace = font

        return EPiCVisualisations.EPiCText(text)

    class EPiCText(ghKernel.Types.GH_GeometricGoo[Display.Text3d],
                   ghKernel.IGH_BakeAwareData,
                   ghKernel.IGH_PreviewData):

        """A Text object that can be baked and transformed in Grasshopper.
        The majority of the code for this class was taken from David Rutten and Giulio Piacentino's
        script described here:
        https://discourse.mcneel.com/t/creating-text-objects-and-outputting-them-as-normal-rhino-geometry/47834/7"""

        # region construction
        def __init__(self, text):
            self.m_value = text

        @staticmethod
        def DuplicateText3d(original):
            if original is None: return None
            text = Display.Text3d(original.Text, original.TextPlane, original.Height)
            text.Bold = original.Bold
            text.Italic = original.Italic
            text.FontFace = original.FontFace
            return text

        def DuplicateGeometry(self):
            return EPiCVisualisations.EPiCText(EPiCVisualisations.EPiCText.DuplicateText3d(self.m_value))

        # region properties
        def get_TypeName(self):
            return "3D Text"

        def get_TypeDescription(self):
            return "3D Text"

        def ToString(self):
            if self.m_value is None: return "<null>"
            return self.m_value.Text

        def get_Boundingbox(self):
            if self.m_value is None:
                return Geometry.BoundingBox.Empty;
            return self.m_value.BoundingBox;

        def GetBoundingBox(self, xform):
            if self.m_value is None:
                return Geometry.BoundingBox.Empty
            box = self.m_value.BoundingBox
            corners = xform.TransformList(box.GetCorners())
            return Geometry.BoundingBox(corners)

        # region methods
        def Transform(self, xform):
            text = EPiCVisualisations.EPiCText.DuplicateText3d(self.m_value)
            text = EPiCVisualisations.EPiCText.DuplicateText3d(self.m_value)
            if text is None: return EPiCVisualisations.EPiCText(None)
            plane = text.TextPlane
            point = plane.PointAt(1, 1)

            plane.Transform(xform)
            point.Transform(xform)
            dd = point.DistanceTo(plane.Origin)

            text.TextPlane = plane
            text.Height *= dd / sqrt(2)
            return EPiCVisualisations.EPiCText(text)

        def Morph(self, xmorph):
            return self.DuplicateGeometry()

        # region preview
        def get_ClippingBox(self):
            return self.get_Boundingbox()

        def DrawViewportWires(self, args):
            if self.m_value is None: return
            args.Pipeline.Draw3dText(self.m_value, args.Color)

        def DrawViewportMeshes(self, args):
            # Do not draw in meshing layer.
            pass

        # region baking
        def BakeGeometry(self, doc, att, id):
            id = Guid.Empty

            if self.m_value is None:
                return False, id

            if att is None:
                att = doc.CreateDefaultAttributes()

            id = doc.Objects.AddText(self.m_value, att)

            return True, id


class EPiCMaterial:
    """
    A class object that represents a single material from the EPiC Database
    """
    FUNCTIONAL_UNIT_SEP = '|'

    def __init__(self, name=str, energy=float, water=float, ghg=float, functional_unit=str, doi=str, category=str,
                 material_id=str, wastage=float, service_life=float, comments=str, density=float, process_shares=dict):
        """
        A material class object that can be passed to EPiCAssemblies and EPiCBuiltAssets
        :param name: Name of the material
        :param energy: Energy coefficient in MJ/Functional Unit
        :param water: Water coefficient in L/Functional Unit
        :param ghg: Greenhouse gas emissions coefficient in kgCO₂e/Functional Unit
        :param functional_unit: Functional unit for the material (e.g. kg, no., m, m², m³)
        :param doi: A link to the material information sheet in the EPiC Database
        :param category: Material category
        :param material_id: EPiCDatabase id for the material
        :param wastage: Estimated wastage percentage (%) for the material.
        :param service_life: Estimated service life for the material.
        :param comments: Material comments - these will be displayed in any reports
        :param density: Material density
        :param process_shares: A dictionary with flows as keys and the process data share of the hybrid coefficient as a value
        """

        self.component_type = 'EPiCMaterial'

        try:
            self.name = name
            self.functional_unit = functional_unit
            self.category = category
            self.doi = doi
            self.energy = energy
            self.water = water
            self.ghg = ghg
            self.density = density
            self.wastage = wastage / 100 if wastage else 0
            self.service_life = service_life
            self.process_shares = process_shares
            self.id = random.getrandbits(128)
            self.comments = remove_commas_and_flatten_list_for_csv_export(comments) if comments else ''
            self.material_id = material_id

        except TypeError:
            raise TypeError("Couldn't load material attributes...")

    def __str__(self):
        return self.print_report(print_to_str=True)

    @staticmethod
    def remove_func_unit_from_mat_name(mat_name_and_func_unit):
        """
        Remove the functional unit between "()" after the | sign, and the space beforehand
        :param mat_name_and_func_unit: the concatenated material name and its functional unit
        :return: the material name cleaned up
        """
        return mat_name_and_func_unit[:(mat_name_and_func_unit.index('|') - 1)]

    @staticmethod
    def _concatenate_mat_name_func_unit(mat_name, functional_unit):
        """
        Adds the funtional unit to a material name
        :param mat_name: a string represent an EPiC material name
        :param functional_unit: a string representing the functional unit of the material
        :return: a concatenated material_name and string
        """
        return mat_name + ' ' + '|' + ' (' + functional_unit + ')'

    def generate_breakdown_dict(self):
        """
        Generates a dictionary that will be provided to EPiCBreakdown, as per the HYBRID_VALUE_BREAKDOWN_DICT template
        :return: as dictionary representing the process and input-output shares of the hybrid value
        """
        breakdown_dict = copy.deepcopy(HYBRID_VALUE_BREAKDOWN_DICT)

        for flow in breakdown_dict.keys():
            breakdown_dict[flow]['process'] = self.process_shares[flow]
            breakdown_dict[flow]['io'] = 1 - self.process_shares[flow]

        return breakdown_dict

    @staticmethod
    def generate_material_and_category_dropdown_list(component_object, ghenv, epic_db,
                                                     category="Concrete and plaster products"):
        """
        Generate a material and category list for the EPiC_Material grasshopper component
        :param component_object: Component object to modify
        :param ghenv: The current grasshopper environment
        :param epic_db: EPiCDatabase object to query
        :param category: Default category to be used for initialising the valuelist
        """

        # Check if input[1] has a value list connected, if not, create one
        if component_object.Params.Input[1].SourceCount == 0:
            make_value_list_input_component(1, EPIC_CATEGORIES, ghenv, xloc=-230, yloc=0)

        # Check if input[2] has a value list connected, if not, create one, but only if input[1] is connected.
        if component_object.Params.Input[1].SourceCount == 1 and component_object.Params.Input[2].SourceCount == 0:

            list_of_mat_values, list_of_mat_names = (zip(*sorted(epic_db.dict_of_categories[category].items())))

            # Use the category created above (input[1]) to generate material list. Set the category to concrete.
            make_value_list_input_component(2, list_of_mat_values, ghenv,
                                            valuelist_names = list_of_mat_names, xloc=-365, yloc=0)
            ghenv.Component.OnPingDocument().ScheduleSolution(5, ghenv.Component.ExpireSolution(True))

    @staticmethod
    def generate_slider_input(component_object, ghenv, slider_value, input_node, slider_min = 0, slider_max = 100):
        """
        Generate a slider input attached to the current component object
        :param component_object: Component object to modify
        :param ghenv: The current grasshopper environment (not used)
        :param slider_value: value to set for the slider
        :param input_node: node number that the slider should be instantiated on
        :param slider_min: minimum value for the slider
        :param slider_max: maximum value for the slider
        """

        # Check if input has a slider connected
        if component_object.Params.Input[input_node].SourceCount == 0:

            num_slider = EPiCMaterial.create_slider(component_object, input_node, slider_max, slider_min, slider_value)

            # Connect slider to component
            component_object.Params.Input[input_node].AddSource(num_slider)

            # Expire the solution outside of current loop to refresh values
            component_object.OnPingDocument().ScheduleSolution(1, component_object.ExpireSolution(False))

            return str(num_slider.InstanceGuid)
        else:
            pass

    @staticmethod
    def create_slider(component_object, input_node, slider_max, slider_min, slider_value):
        ghdoc = component_object.OnPingDocument()
        num_slider = ghKernel.Special.GH_NumberSlider()
        num_slider.Slider.Minimum = slider_min
        # Check if the proposed slider value is more than the slider max value. If so, increase the max value.
        if slider_value > slider_max:
            num_slider.Slider.Maximum = slider_value
        else:
            num_slider.Slider.Maximum = slider_max
        num_slider.Slider.DecimalPlaces = 0
        num_slider.SetSliderValue(slider_value)
        num_slider.CreateAttributes()
        num_slider.Attributes.Pivot = Drawing.PointF(component_object.Params.Input[input_node].Attributes.Bounds.X
                                                     - num_slider.Attributes.Bounds.Width * 2,
                                                     component_object.Params.Input[input_node].Attributes.Bounds.Y)
        ghdoc.AddObject(num_slider, False)
        return num_slider

    @staticmethod
    def recreate_material_list(epic_db, ghObject, material_category, component, set_material=None):
        """
        Recreate the material list based on the currently selected material category
        :param epic_db: EPiCDatabase object
        :param ghObject: Grasshopper component
        :param material_category: Currently selected material category
        :param Params: The component parameters, this is needed to recreate the input values
        :pamam set_material: Specify the chosen material for the new list
        """

        # Create a sticky that makes sure itemlist won't continuously load
        if not "is_running" in st.keys():
            st["is_running"] = False

        # Check if the sticky is 0 (and therefore the list isn't in the middle of initialising)
        if st["is_running"] == False:
            try:
                # set the running to true at the start of the function, indicating that it is in progress
                st["is_running"] = True
                new_list = zip(*sorted(epic_db.dict_of_categories[material_category].items()))
                ghObject.ListItems.Clear()
                selected_material = 0
                list_number = 0
                for id, name in zip(new_list[0], new_list[1]):
                    _ = ghObject.ListItems.Add(ghKernel.Special.GH_ValueListItem(str(name), '"' + str(id) + '"'))
                    if set_material and set_material == id:
                        selected_material = list_number
                    list_number += 1

                # Select the chosen material
                if selected_material:
                    ghObject.SelectItem(selected_material)

                # Expire the current solution
                component.OnPingDocument().ScheduleSolution(5, ghObject.ExpireSolution(True))
                st["is_running"] = False
            except:
                # If the list loading fails, global running value will be reset
                st["is_running"] = False


    def print_report(self, print_to_str=False, custom_material=False):
        """
        Print a report, based on the material coefficient values and material attributes
        :param print_to_str: Print to string should be marked as true when outputting as a string, otherwise a list
        :param custom_material: switch to true to omit printing the DOI as a custom material won't have one
        :return: string(print_to_str=True) or list
        """

        results = []
        results.append('<< {} >>'.format(self.name))
        results.append('Category: {}'.format(self.category))
        results.append('Functional Unit: {}'.format(self.functional_unit))
        results.append('')
        results.append('Embodied Energy Coefficient: {} MJ/{}'.format(self.energy, self.functional_unit))
        results.append('Embodied Water Coefficient: {} L/{}'.format(self.water, self.functional_unit))
        results.append('Embodied GHG Coefficient: {} kgCO₂e/{}'.format(self.ghg, self.functional_unit))

        # Only include wastage / service life in the report if values exist
        if self.wastage > 0 or self.service_life > 0:
            results.append('')
            if self.wastage > 0:
                results.append('Wastage: {}%'.format(self.wastage * 100))
            if self.service_life > 0:
                results.append('Service Life: {} years'.format(self.service_life))

        results.append('')
        if not custom_material:
            results.append('DOI: {}'.format(self.doi))
            results.append('')
            results.append('Process-based data proportion of hybrid value')
            for flow_properties in DEFINED_FLOWS.values():
                results.append(flow_properties['print_name'] + ': {:.0%}'.format(
                    self.process_shares[flow_properties['code_name']]))

        return results if not print_to_str else '\n'.join(results)


class CustomMaterial(EPiCMaterial):
    """
    A class object that represents a single custom material, based on the EPiCMaterial template
    """

    def __init__(self, *args, **kwargs):
        EPiCMaterial.__init__(self, *args, **kwargs)

    def __str__(self):
        return self.print_report(print_to_str=True, custom_material=True)


class EPiCGraph:
    """
    Enables the visualisation of EPiC_Analysis, using data from associated EPiC_Assembly & EPiC_Material classes
    """

    seg_pref_template = OrderedDict([
        ('initial', {'flow_type': ['initial', 'initial_wastage'], 'colour': 'colour',
                     'label': 'Initial', 'hatch_type': 0, 'hatch_scale': 0.5,
                     'hatch_angle': 45}),
        ('initial_wastage', {'flow_type': 'initial_wastage', 'colour': 'colour',
                             'label': 'Initial wastage', 'hatch_type': 1, 'hatch_scale': 1,
                             'hatch_angle': 135}),
        ('recurrent', {'flow_type': ['recurrent', 'recurrent_wastage'],
                       'colour': 'secondary_colour', 'label': 'Recurrent', 'hatch_type': 0,
                       'hatch_scale': 0.5, 'hatch_angle': 45}),
        ('recurrent_wastage', {'flow_type': 'recurrent_wastage',
                               'colour': 'secondary_colour', 'label': 'Recurrent wastage',
                               'hatch_type': 1, 'hatch_scale': 1, 'hatch_angle': 135}),
        ('life_cycle', {'flow_type': ['life_cycle', 'life_cycle_wastage'],
                        'colour': 'colour', 'label': 'Life cycle', 'hatch_type': 0,
                        'hatch_scale': 0.5, 'hatch_angle': 45}),
        ('life_cycle_wastage', {'flow_type': 'life_cycle_wastage', 'colour': 'colour',
                                'label': 'Life cycle wastage', 'hatch_type': 1,
                                'hatch_scale': 1, 'hatch_angle': 135})])

    def __init__(self, data, graph_origin=(0, 0, 0), graph_height=10., graph_spacing=1., graph_width=1.,
                 graph_padding=6, analysis_type='by_material', graph_subset_2=None, show_recurrent=True,
                 flows=('energy', 'water', 'ghg'), sort_graph=True, graph_scale=1, column_width=0.7,
                 column_padding=0.2, space_between_graphs=5, hide_null_columns=True, minimum_spacing_for_graph=3,
                 text_size=0.3, heading_text_size=0.8, axis_label_text_size=0.65, tick_size=0.2, text_padding=0.3,
                 legend_box_size=0.5):

        # Set all instance attributes based on inputs
        vars = locals()  # dict of local names
        self.__dict__.update(vars)  # __dict__ holds and object's attributes
        del self.__dict__["self"]  # don't need `self`

        # Make sure origin is either a tuple or Rhino Point3d object.
        # If origin is a tuple, convert to Point3d Object.
        if isinstance(graph_origin, tuple):
            self.origin = Geometry.Point3d(graph_origin[0], graph_origin[1], graph_origin[2])
        elif isinstance(graph_origin, (Geometry.Point, Geometry.Point3d)):
            self.origin = graph_origin
        else:
            TypeError('The origin_point should be a tuple, eg (0,0,0) or a 3dPoint value')

        # only allow 'by_material' and 'analysis_type' as input for analysis_type.
        # All other values will default to 'total' (analysis_type = None)
        if 'by_material' not in analysis_type and 'by_assembly' not in analysis_type:
            analysis_type = None
        self.analysis_type = analysis_type

        # Make sure data input is in list format
        if not isinstance(data, list):
            data = [data]
        self.data = data

        # Number of comparison values for the graph
        self.num_comparisons = len(data)

        # Cycle through all of the materials to branch_count the number of unique materials
        _all_materials = _flatten_list([y.epic_materials for x in self.data for y in x.epic_assemblies])
        self.number_of_materials = len(set([x for x in _all_materials if not isinstance(x, (float, int))]))

        # Cycle through all of the assemblies to branch_count the number of unique assembly categories
        self.number_assembly_cats = len(set(_flatten_list([x.epic_assemblies for x in self.data])))

        # Set additional instance attributes
        self.graph_subset_2_colours = {}

        # Generate graphs
        self.graph_data = self._create_bar_graph_for_each_flow(self.data, analysis_type=analysis_type,
                                                               show_recurrent=show_recurrent)

    @property
    def elements_to_render(self):
        """
        A list of graph elements (legend, text, columns) to visualise
        :return: List of graph elements
        """
        graph_elements = _flatten_list([graph.elements_to_render for graph in self.graph_data])


        # Print error message if no values are found
        if not graph_elements:
            # Specific an offset value for the error message text.
            graph_offset = (1, 5, 0)
            text_origin = tuple(sum(x) for x in zip(self.graph_origin, graph_offset))
            error_msg = "No bar chart can be displayed.\nIt is likely that all embodied flows have zero values."\
                        "\nOR there has been a calculation error.\nCheck your assembly quantities."
            graph_elements = EPiCVisualisations.bakeable_text_from_str(error_msg,
                                                      text_size=self.heading_text_size,
                                                      text_location=text_origin)

        if self.graph_scale != 1:
            graph_elements = self._scale_graph_elements(graph_elements)

        return graph_elements

    def _scale_graph_elements(self, graph_elements):
        """
        Scale graph elements
        :param graph_elements: Graph elements to scale
        :return: Scaled graph elements
        :rtype: list
        """
        self.graph_scale = [self.graph_scale, self.graph_scale, 0]
        scaled_elements = []
        for graph_element in graph_elements:
            if isinstance(graph_element, Geometry.Line):
                transform = False
                try:
                    transform = graph_element.Transform(rs.XformScale(self.graph_scale, self.origin))
                except:
                    pass
                if transform:
                    scaled_elements.append(graph_element)

            elif isinstance(graph_element, (EPiCVisualisations.EPiCText, EPiCVisualisations.GraphSegmentGeometry)):
                try:
                    scaled_elements.append(graph_element.Transform(rs.XformScale(self.graph_scale, self.origin)))
                except:
                    pass
        return scaled_elements

    def _create_bar_graph_for_each_flow(self, data, analysis_type=None, show_recurrent=True):
        """
        Create a separate bar graph for each flow (energy, water and ghg)
        :param data: Graph data
        :param analysis_type: The type of built_assets to use for each graph (e.g. by_material, by_assembly, total)
        :param show_recurrent: Show breakdown of recurrent values
        :return: A list of epic.BarGraph object instances, one for each flow.
        """

        list_of_graphs = []
        graph_cumulative_width = 0
        sub_group_data = None
        graph_origin_point = Geometry.Point3d(self.origin.X, self.origin.Y, self.origin.Z)

        # Change graph visualisation style depending if breakdown of recurrent values is shown
        if show_recurrent:
            list_of_keys = ['initial', 'initial_wastage', 'recurrent', 'recurrent_wastage']
        else:
            list_of_keys = ['life_cycle', 'life_cycle_wastage']

        # Create a list of the stacked bar segments to be shown
        self.segment_properties = OrderedDict((key, copy.deepcopy(value)) for (key, value)
                                              in self.seg_pref_template.items() if key in list_of_keys)

        # Multiple graph values can be included for comparison
        for num, d in enumerate(data):
            pass

        # if the analysis_type is 'by_material' or 'by_assembly'
        if analysis_type == 'by_material' or analysis_type == 'by_assembly':
            if isinstance(data, list):
                data = [d.flows[analysis_type] if analysis_type in d.flows else {d.name: d.flows} for d in data]

        # if the analysis_type is 'by_assembly_and_material'

        elif analysis_type == 'by_assembly_and_material':
            if isinstance(data, list):
                if len(data) > 1:
                    sub_group_data = [
                        (d.flows['by_assembly'], d.name) if 'by_assembly' in d.flows else {d.name: d.flows}
                        for d in data]
                data = [d.flows['by_assembly'] if 'by_assembly' in d.flows else {d.name: d.flows} for d in data]

        # if the analysis_type is 'total'
        else:
            if isinstance(data, list):
                data = [{'total': data.flows} for data in data]

        # For each flow, create a new graph_origin point (based on the graph width + spacing)
        for flow_num, flow in enumerate(self.flows):
            # Set the graph_origin point
            graph_origin_point.X += graph_cumulative_width

            # Create a graph for each flow
            epic_graph = EPiCGraph.BarGraph(data,
                                            sub_group_data=sub_group_data,
                                            graph_preferences=self,
                                            origin=graph_origin_point,
                                            name=flow,
                                            flow=flow,
                                            flow_units=DEFINED_FLOWS[flow]['unit'],
                                            title=DEFINED_FLOWS[flow]['print_name'])
            list_of_graphs.append(epic_graph)

            # Move the graph_origin point for the next flow
            graph_cumulative_width = self.graph_width

        return list_of_graphs

    class BarGraph:
        def __init__(self, data, sub_group_data=None, graph_preferences=None, origin=Geometry.Point3d(0, 0, 0), name='',
                     flow='', title='', flow_units=''):
            """
            A bar graph based on an EPiCAnalysis class object
            :param data: Flow data for each EPiCAnalysis input, if multiple inputs, these will be used as a comparison
            :param graph_preferences: Graph preferences inherited from the EPiCGraph class instance
            :param origin: Origin point for the bar graph
            :param name: Name of the bar graph (environmental flow abbreviation)
            :param flow: Enironmental flow type
            :param title: Title of the bar graph (environmental flow)
            :param flow_units: Flow units used for the bar graph
            """

            self.data = data
            self.sub_group_data = sub_group_data
            self.graph_preferences = graph_preferences
            self.origin = origin
            self.name = name
            self.flow = flow
            self.title = title
            self.flow_units = flow_units

            # Set the graph origin plane based on the graph origin
            if isinstance(origin, tuple):
                self.origin = Geometry.Point3d(origin[0], origin[1], origin[2])
            elif isinstance(origin, (Geometry.Point, Geometry.Point3d)):
                self.origin = Geometry.Point3d(origin.X, origin.Y, origin.Z)
            else:
                TypeError('The origin_point should be a tuple, eg (0,0,0) or a 3dPoint value')
            self.origin_plane = rs.MovePlane(rs.WorldXYPlane(), self.origin)

            # Attributes used in graph creation process
            self.max_data_value = 0
            self.legend = None
            self.columns = []
            self.column_group_names = OrderedDict()
            self.cumulative_column_spacing = 0

            # Build the bar graph
            self.build_graph()

            # Create a list of all visualisation elements for the graph
            self.elements_to_render = self._render_elements()

        def _render_elements(self):
            """
            Create a list of all visualisation elements for the graph.
            These are taken from the individual graph segments and graph legend
            :return: a flattened list of elements to render
            :rtype: list
            """
            _items_to_render = {'graph': [], 'legend': {}}
            if self.legend:
                _items_to_render['legend'] = [y for y in [x for x in self.legend.elements_to_render.values()]]
            if self.segments:
                _items_to_render['graph'] = [seg.elements_to_render for seg in self.segments]
            return _flatten_list(_items_to_render['legend'] + _items_to_render['graph'])

        @property
        def segments(self):
            """
            A list of segment items for the graph
            :rtype: list
            """
            segs = []
            if self.columns:
                for col in self.columns:
                    segs += col.segments
            return segs

        def _get_max_values(self):
            """
            Get the maximum life_cycle value for this flow.
            This can be used to set the maximum y axis value for the graph
            :return: Maximum life cycle value
            :rtype: float
            """
            for _data in self.data:
                for _mat in _data.values():
                    if 'life_cycle' in _mat:
                        max_data_value = max([_mat['life_cycle'][self.flow]])
                        self.max_data_value = max(max_data_value, self.max_data_value)
            return self.max_data_value

        def build_graph(self):
            """
            Generate a new graph.
            This will override graphs already created in this class instance
            """

            self.cumulative_column_spacing = 0
            column_origin_plane = self.origin_plane.Clone()

            # Delete previous class instances
            for _col in self.columns:
                del _col
            self.columns = []

            # Get the unique names of each column (in both the original graph + comparison graphs)
            # If the graph has more than one column, the following code will run
            if self.graph_preferences.analysis_type:

                all_keys = list(set([key for d in self.data for key in d.keys()]))
                self.max_data_value = self._get_max_values()

                # Populate dictionary with life cycle flow values, based on column keys
                # Then rank the columns from highest life cycle value to lowest.
                dictionary_of_column_flow_values = self._get_life_cycle_flow_values_for_column_keys(all_keys)
                self.column_group_names = self._sort_dictionary_highest_to_lowest_value(
                    dictionary_of_column_flow_values)

            else:
                if isinstance(self.data, list):
                    for _ in self.data:
                        self.column_group_names = {'Total': {'group_label_origin': None}}
                        self.max_data_value = self._get_max_values()

            # Create the column groups. Each group might multiple columns (comparison values)
            for num, key in enumerate(self.column_group_names.keys()):
                self._create_column_group(self.data, column_origin_plane, key, num, sub_group=self.sub_group_data)

            # Delete previous class instances
            del self.legend

            # Create a legend for the graph
            self.legend = EPiCGraph.BarGraphLegend(self, graph_preferences=self.graph_preferences)

        def _create_column_group(self, group_data, column_origin_plane, column_group_name, column_number_in_group,
                                 sub_group=False, show_group_name=True):
            """
            Create a bar graph column group (can contain subgroups and multiple bars)
            :param group_data: data used to create the group of columns
            :param column_origin_plane: Origin plane for the column
            :param column_group_name: Name of the column group (this group might contain multiple columns)
            :param column_number_in_group: The order number in the column group. 0=First
            :param sub_group: data used to create a sub_group
            :param show_group_name: toggle for group name labels
            """

            # Condition for displaying the group column name
            if len(group_data) == 1 and self.graph_preferences.analysis_type != 'by_assembly_and_material':
                show_group_name = False

            # Condition for displaying sub-graphs
            if sub_group:
                group_data = sub_group

            # Create a column for each data point
            for column_number, data in enumerate(group_data):
                count = 0

                column_name = self._set_column_name(column_group_name, column_number, group_data)
                column_data, sub_group_name = self._extract_column_data(column_group_name, data, sub_group)

                # If hide_null_columns set to True, only show column if flow data > 0

                if self.graph_preferences.hide_null_columns:
                    if not column_data or column_data['life_cycle'][self.flow] == 0:
                        continue

                if self.graph_preferences.analysis_type == "by_assembly_and_material":
                    if column_data:
                        if self.graph_preferences.hide_null_columns:
                            columns = {key: mat for key, mat in column_data['by_material'].items()
                                       if mat['life_cycle'][self.flow] != 0}
                        else:
                            columns = column_data['by_material']
                        for key, mat in columns.items():

                            # Create location values for the legend labels.
                            # These are only needed when creating group labels
                            if show_group_name:
                                self._create_legend_attributes(column_group_name, column_number_in_group,
                                                               column_origin_plane, sub_group_name=sub_group_name)

                            # Create a BarGraphColumn object
                            self._create_column(mat, column_number_in_group, column_origin_plane,
                                                column_name=key, show_group_name=show_group_name, sub_group_count=count)

                else:
                    if column_data:

                        # Create location values for the legend labels.
                        # These are only needed when creating group labels
                        if show_group_name:
                            self._create_legend_attributes(column_group_name, column_number_in_group,
                                                           column_origin_plane, sub_group_name=sub_group_name)

                        # Create a BarGraphColumn object
                        self._create_column(column_data, column_number_in_group, column_origin_plane,
                                            column_name=column_name, show_group_name=show_group_name)

        def _set_column_name(self, column_group_name, column_number, group_data):
            """
            Set the column name, according to the number of data inputs and analysis type selected
            :param column_group_name: The name of the column group
            :param column_number: The column number, in the current column group
            :param group_data: The column group data
            :return: Name of the column
            :rtype: str
            """
            column_name = str(self.graph_preferences.data[column_number].name)

            # Condition where there are no comparison bars
            if len(group_data) == 1:
                if self.graph_preferences.analysis_type == 'by_material':
                    column_name = column_group_name

                elif self.graph_preferences.analysis_type == 'by_assembly':
                    column_name = column_group_name

                elif not self.graph_preferences.analysis_type:
                    column_name = 'Total'

            return column_name

        def _extract_column_data(self, column_group_name, data, sub_group):
            """
            Extract the column data, depending on the analysis type
            :param column_group_name: The name of the column group
            :param data: Data to extract the column data from
            :param sub_group: Data used to create a sub_group
            :return: The column data and subgroup name (if used, otherwise None)
            """

            sub_group_name = None

            if sub_group:
                if column_group_name in data[0]:
                    column_data = data[0][column_group_name]
                    sub_group_name = data[1]
                else:
                    column_data = None
                    sub_group_name = None

            elif self.graph_preferences.analysis_type in ['by_material', 'by_assembly', 'by_assembly_and_material']:
                if column_group_name in data:
                    column_data = data[column_group_name]
                else:
                    column_data = None

            else:
                if 'life_cycle' not in data:  # When 'total' value is used to generate graph
                    _temp_val = data[list(data.keys())[0]]
                    if 'life_cycle' in _temp_val:
                        column_data = _temp_val
                    else:
                        column_data = None
                else:
                    column_data = data
            return column_data, sub_group_name

        def _create_column(self, column_data, column_number_in_group, column_origin_plane,
                           column_name='', show_group_name=True, sub_group_count=0):
            """
            Create a BarGraphColumn that represents a column in EPiCGraph
            :param column_data: Data used to generate the column
            :param column_number_in_group: The column number - based on the current column group
            :param column_origin_plane: Origin plane for the column
            :param column_name: Name of the column
            :param show_group_name: Show group name if True
            :param sub_group_count:
            """
            graph_spacing = self.graph_preferences.graph_spacing

            # Move the column origin plane, based on the column number, graph spacing and sub-group count
            column_origin_plane = self._move_column_origin_plane(column_number_in_group, column_origin_plane,
                                                                 graph_spacing, sub_group_count)

            # If needed, increase the graph_width to make sure it fits all of the data
            self.graph_preferences.graph_width = max(self.graph_preferences.graph_width,
                                                     ((graph_spacing * column_number_in_group)
                                                      + self.cumulative_column_spacing
                                                      + self.graph_preferences.space_between_graphs))
            # Generate Column
            graph_column = EPiCGraph.BarGraphColumn(column_data,
                                                    graph_preferences=self.graph_preferences,
                                                    name=column_name,
                                                    column_group_name=column_number_in_group,
                                                    origin_plane=column_origin_plane,
                                                    flow=self.flow,
                                                    max_data_value=self.max_data_value,
                                                    show_group_name=show_group_name
                                                    )
            self.columns.append(graph_column)

        def _create_legend_attributes(self, column_group_name, column_number_in_group, column_origin_plane,
                                      sub_group_name=False):
            """
            Based on the column group - create attributes used to generate the graph legend.
            This includes location of break line (above group column name) for graph visualisation
            :param column_group_name: Column group name
            :param column_number_in_group: The column number, in the current column group 0=First
            :param column_origin_plane: Column origin plane
            """

            # Attributes are stored in the self.column_group_names dictionary
            attributes = self.column_group_names[column_group_name]

            if sub_group_name:
                # Populate the group attributes
                self._populate_attributes(attributes, column_number_in_group, column_origin_plane)

                # Populate the sub-group attributes
                _att = self.column_group_names[column_group_name]
                if 'sub_group' not in _att:
                    _att['sub_group'] = {}
                if sub_group_name not in _att['sub_group']:
                    _att['sub_group'][sub_group_name] = {}
                attributes = _att['sub_group'][sub_group_name]
                self._populate_attributes(attributes, column_number_in_group, column_origin_plane)
            else:
                self._populate_attributes(attributes, column_number_in_group, column_origin_plane)

        def _populate_attributes(self, attributes, column_number_in_group, column_origin_plane):
            """
            Populate the column attributes - these are used to calculate the location of the text for the legend
            :param attributes: Attributes dictionary to populate
            :param column_number_in_group: The column number, in the current column group 0=First
            :param column_origin_plane: Column origin plane
            """

            # Retrieve preferences from parent EPiCGraph class
            prefs = self.graph_preferences
            graph_spacing = prefs.graph_spacing

            # If label hasn't been created, generate the base attributes
            if 'group_label_origin_x_line_start' not in attributes:
                x_axis_value_for_column_group_line_start = self.origin.X + (graph_spacing * column_number_in_group) \
                                                           + self.cumulative_column_spacing + graph_spacing
                attributes['group_label_origin_x_line_start'] = x_axis_value_for_column_group_line_start
                attributes['group_label_origin_y'] = column_origin_plane.OriginY
                attributes['group_label_origin_z'] = column_origin_plane.OriginZ
                attributes['number_of_columns_in_group'] = 1

            # If label already exists, increase the 'number of columns' counter
            else:
                attributes['number_of_columns_in_group'] += 1
            centre_text = (prefs.column_padding * 2) + ((prefs.column_width + prefs.column_padding) / 2
                                                        * (attributes['number_of_columns_in_group'] - 1))
            end_text = (prefs.column_padding * 3) + ((prefs.column_width + prefs.column_padding)
                                                     * (attributes['number_of_columns_in_group'] - 1))
            attributes['group_label_origin_x_line_end'] = attributes['group_label_origin_x_line_start'] + end_text
            attributes['group_label_origin_x'] = attributes['group_label_origin_x_line_start'] + centre_text

        @staticmethod
        def _sort_dictionary_highest_to_lowest_value(dictionary_to_rank):
            """
            Sort dictionary based on it's values.
            Rank from highest to lowest.
            :param dictionary_to_rank: dictionary to rank, with float for value
            :return: New sorted dictionary
            :rtype: OrderedDict
            """

            ranked_dictionary = OrderedDict()
            while len(dictionary_to_rank) > 0:
                max_key = max(dictionary_to_rank, key=dictionary_to_rank.get)
                ranked_dictionary[max_key] = {'max_value': dictionary_to_rank.pop(max_key), 'group_label_origin': None}
            return ranked_dictionary

        def _get_life_cycle_flow_values_for_column_keys(self, column_keys):
            """
            Get life cycle flow values based on column keys. Values are collected from self.data
            Values must be above 0.
            :param column_keys: List of column keys
            :return: Dictionary with keys based on input list, and associated life cycle flow values
            :rtype: dict
            """

            column_values = {}
            for column_key in column_keys:
                column_values[column_key] = 0
                for d in self.data:
                    try:
                        if d[column_key]['life_cycle'][self.flow] > column_values[column_key]:
                            column_values[column_key] = d[column_key]['life_cycle'][self.flow]
                    except KeyError:  # Condition when comparison graph has different column names.
                        pass
            return column_values

        def _move_column_origin_plane(self, column_number_in_column_group, column_origin_plane, graph_spacing,
                                      sub_group_count=0):
            """
            Move the column origin plane based on the column number (in the column group) and graph spacing
            :param column_number_in_column_group: Column number in the column group (0=First column of the group)
            :param column_origin_plane: Previous column origin plane
            :param graph_spacing: Graph spacing
            :return: Origin plane, moved to the new location
            """

            self.cumulative_column_spacing += \
                (self.graph_preferences.column_padding + self.graph_preferences.column_width)
            x_axis_origin = self.origin.X + (graph_spacing * column_number_in_column_group) \
                            + (sub_group_count * column_number_in_column_group) + self.cumulative_column_spacing
            column_origin_plane.OriginX = x_axis_origin
            return column_origin_plane

    class BarGraphColumn:
        def __init__(self, data, graph_preferences=None, name='', origin_plane=rs.WorldXYPlane(), flow='',
                     max_data_value=0, column_group_name='', show_group_name=False):
            """
            A bar graph column element (inside BarGraph())
            :param data: Bar graph data
            :param graph_preferences: Graph preferences inherited from the EPiCGraph class instance
            :param name: Name of the column
            :param origin_plane: Origin plane for the column
            :param flow: Enironmental flow type
            :param max_data_value: the highest life cycle data value in the flow (sets the y-axis)
            :param column_group_name: Name of the column group
            """

            self.data = data
            self.graph_preferences = graph_preferences
            self.name = name
            self.origin_plane = origin_plane
            self.flow = flow
            self.max_data_value = max_data_value
            self.column_group_name = column_group_name
            self.show_group_name = show_group_name

            # Set the column attributes
            self.segments = []
            self.origin = Geometry.Point3d(origin_plane.OriginX, origin_plane.OriginY, origin_plane.OriginZ)

            if max_data_value == 0:
                self.elements_to_render = None

            else:
                self.max_data_value = max_data_value
                if self.data:
                    self.build_segments()
                self.elements_to_render = None

        def _build_segment(self, data, segment_type, segment_origin_plane, flow_type, colour=None):
            """
            Create a stacked bar segment for the current EPiCGraph column
            :param data: Data used to create the segment
            :param segment_type: The flow type that the segment represents (e.g initial, recurrent, initial wastage)
            :param segment_origin_plane: Origin plane for the segment
            :param flow_type: The flow type (e.g. Energy, Water, GHG)
            :param colour: segment colour
            :param subset:
            :return:
            """

            segment = segment_type

            # If no value provided, use the default colour based on the flow + segment type
            colour = DEFINED_FLOWS[self.flow][segment['colour']] if not colour else colour

            # Get the flow values to create the segment
            if isinstance(segment['flow_type'], list):
                if data[segment['flow_type'][1]][self.flow] > 0 and self.max_data_value > 0:
                    normalised_graph_value = ((data[segment['flow_type'][0]][self.flow]
                                               - data[segment['flow_type'][1]][self.flow])
                                              / self.max_data_value) * self.graph_preferences.graph_height
                elif data[segment['flow_type'][0]][self.flow] > 0 and self.max_data_value > 0:
                    normalised_graph_value = (data[segment['flow_type'][0]][self.flow]
                                              / self.max_data_value) * self.graph_preferences.graph_height
                else:
                    normalised_graph_value = 0

            # The other flows can be taken directly. Values are normalised for the graph height
            else:
                if data[segment['flow_type']][self.flow] > 0:
                    normalised_graph_value = (data[segment['flow_type']][self.flow]
                                              / self.max_data_value) * self.graph_preferences.graph_height
                else:
                    normalised_graph_value = 0

            # Only create a segment is the value is more than 0
            if normalised_graph_value > 0:
                self.segments.append(
                    EPiCGraph.BarGraphSegment(graph_preferences=self.graph_preferences,
                                              origin_plane=segment_origin_plane,
                                              height=normalised_graph_value,
                                              origin_point=(segment_origin_plane.OriginX,
                                                            segment_origin_plane.OriginY,
                                                            segment_origin_plane.OriginZ),
                                              colour=colour,
                                              show_hatch='wastage' in segment['label'],
                                              segment_type=segment['label'],
                                              label=flow_type
                                              ))
            return normalised_graph_value

        @staticmethod
        def make_tint(colour_tuple, tint_factor):
            """
            Create a tint value for a a specified colour
            :param colour_tuple: an aRBG colour tuple with values of 0-255 (A,R,G,B) A = alpha
            :param tint_factor: A tint factor from 0 to 1, 0 being a lighter value
            :return: (A,R,G,B) tuple
            :rtype: tuple
            """
            alpha = colour_tuple[0]
            newR = min([255, colour_tuple[1] + (255 - colour_tuple[1]) * tint_factor])
            newG = min([255, colour_tuple[2] + (255 - colour_tuple[2]) * tint_factor])
            newB = min([255, colour_tuple[3] + (255 - colour_tuple[3]) * tint_factor])
            return (alpha, newR, newG, newB)

        def build_segments(self):
            segment_origin_plane = rs.MovePlane(rs.WorldXYPlane(), self.origin)

            for key, segment in self.graph_preferences.segment_properties.items():
                normalised_graph_value = self._build_segment(self.data, segment, segment_origin_plane, key)
                segment_origin_plane = rs.MovePlane(segment_origin_plane, rs.AddPoint(
                    segment_origin_plane.OriginX,
                    segment_origin_plane.OriginY + normalised_graph_value,
                    segment_origin_plane.OriginZ))

    class BarGraphSegment:
        def __init__(self, graph_preferences=None, origin_plane=rs.WorldXYPlane(), height=0, colour=None,
                     segment_type='', origin_point=(0, 0, 0), label='', show_hatch=False):
            """
            A stacked bar segment for the current EPiCGraph column
            :param graph_preferences: Graph preference inherited from EPiCGraph
            :param origin_plane: The segment origin plane
            :param height: Height of the segment
            :param colour: Colour of the segment
            :param segment_type: The type of flow that the segment represents
            :param origin_point: Origin point for the segment
            :param label: The flow type for the segment
            :param show_hatch: Show hatch if True
            """

            self.graph_preferences = graph_preferences
            self.origin_plane = origin_plane
            self.origin = origin_point
            self.colour = colour
            self.show_hatch = show_hatch
            self.name = segment_type
            self.label = label

            # Create segment
            segment = EPiCVisualisations.GraphSegmentGeometry(Geometry.Rectangle3d(origin_plane,
                                                                                   self.graph_preferences.column_width,
                                                                                   height))
            segment.fill_colour = colour
            segment.show_hatch = show_hatch
            self.elements_to_render = segment

    class BarGraphLegend:

        def __init__(self, graph, graph_preferences=None):
            """
            Creates a legend for each graph component. This includes titles, labels, axis lines & legends.
            :param graph: BarGraph class object. Used to extract legend values.
            :param graph_preferences: Graph preference inherited from EPiCGraph
            """

            self.graph_preferences = graph_preferences
            self.graph = graph

            # Load the individual graph preferences
            self.column_spacing = graph_preferences.column_width + graph_preferences.text_padding
            self.legend_box_size = graph_preferences.legend_box_size
            self.text_size = graph_preferences.text_size
            self.heading_text_size = graph_preferences.heading_text_size
            self.tick_size = graph_preferences.tick_size
            self.text_padding = graph_preferences.text_padding
            self.axis_label_text = graph_preferences.axis_label_text_size

            # Create a dictionary for all geometry and text that needs to be visualised
            elements = {
                'legend_boxes': [],
                'legend_text': [],
                'column_names': None,
                'axis_lines': [],
                'axis': [],
                'y_axis_label': str}
            prefs = []

            # Extract preferences (the flow_types used in the graph) from each segment
            if self.graph and isinstance(self.graph, EPiCGraph.BarGraph):
                for column in self.graph.columns:
                    prefs += [seg.label for seg in column.segments if seg]
                self.segment_preferences = set(prefs)
                if len(self.segment_preferences) == 0:
                    self.segment_preferences = None
            else:
                self.segment_preferences = None

            # Build a legend for the graph, including all axis lines and labels.
            self.elements_to_render = {}
            self.create_legend(elements)

        def create_legend(self, elements):
            """
            Create a legend for the current EPiCBarGraph element
            :param elements: A dictionary of visualisation elements to be populated
            """

            # Create a legend for each of the flow types
            if self.segment_preferences:
                legend_top_y_axis = self._create_legend(elements)
                self._create_column_labels(elements)
                if len(self.graph.column_group_names) > 0:  # Only used when multiple column values
                    self._create_column_group_labels(elements)
                self._create_axis_lines(elements)
                self._create_ticks(elements)
                self._create_graph_title(elements, legend_top_y_axis)
                self._create_y_axis_labels(elements)

                # Create a dictionary entry for each geometry / text that needs to be rendered
                self.elements_to_render = elements

        def _create_y_axis_labels(self, elements):
            """
            Create the y-axis labels
            :param elements: A dictionary of visualisation elements to be populated
            """
            # find the minimum x origin value for the bounding boxes for the tick_text
            tick_text_x_limit = min(text.get_Boundingbox().GetCorners()[0].X for text in elements['tick_text'])
            # Create a label for the y-axis based on flow units
            elements['y_axis_label'] = EPiCVisualisations.bakeable_text_from_str(
                self.graph.flow_units,
                text_size=(self.axis_label_text),
                text_location=(tick_text_x_limit - 0.5,
                               self.graph.origin.Y + self.graph_preferences.graph_height / 2,
                               self.graph.origin.Z),
                text_rotation=90)

        def _create_graph_title(self, elements, legend_top_y_axis):
            """
            Create a graph title
            :param elements: A dictionary of visualisation elements to be populated
            :param legend_top_y_axis: location of the top y-axis element (legend)
            """

            elements['heading'] = EPiCVisualisations.bakeable_text_from_str(self.graph.title,
                                                                            text_size=self.heading_text_size,
                                                                            text_location=(self.graph.origin.X,
                                                                                           legend_top_y_axis
                                                                                           + self.column_spacing,
                                                                                           self.graph.origin.Z))

        def _create_legend(self, elements):
            """
            Create a legend for the graph
            :param elements: A dictionary of visualisation elements to be populated
            :return: The y-axis location of the legend, needed to calculate the Title location
            """

            for num, legend in enumerate(self.segment_preferences):
                legend = self.graph_preferences.seg_pref_template[legend]
                x_axis = self.graph.origin.X
                y_axis = self.graph.origin.Y + self.graph_preferences.graph_height \
                         + self.graph_preferences.graph_spacing \
                         + (self.column_spacing * num)
                z_axis = self.graph.origin.Z
                legend_origin = rs.MovePlane(rs.WorldXYPlane(),
                                             Geometry.Point3d(x_axis, y_axis, z_axis))
                legend_colour = DEFINED_FLOWS[self.graph.flow][legend['colour']]
                show_hatch = 'wastage' in legend['label']
                legend_box = EPiCVisualisations.GraphSegmentGeometry(
                    Geometry.Rectangle3d(legend_origin, self.legend_box_size, self.legend_box_size))
                legend_box.show_hatch = show_hatch
                legend_box.fill_colour = legend_colour

                elements['legend_boxes'].append(legend_box)
                elements['legend_text'].append(
                    EPiCVisualisations.bakeable_text_from_str(legend['label'],
                                                              text_size=self.text_size,
                                                              text_location=(
                                                                  (legend_origin.OriginX + self.column_spacing),
                                                                  legend_origin.OriginY,
                                                                  legend_origin.OriginZ)))
            return y_axis

        def _create_ticks(self, elements):
            """
            Create the y-axis ticks and tick text for the graph
            :param elements: A dictionary of visualisation elements to be populated
            """

            # Create list of ticks
            tick_values = (self.create_list_of_ticks([0, self.graph.max_data_value],
                                                     normalised_y_axis_height=self.graph_preferences.graph_height))
            tick_values_not_normalised = (self.create_list_of_ticks([0, self.graph.max_data_value]))

            # Create ticks
            elements['axis'] += [Geometry.Line(self.graph.origin.X, self.graph.origin.Y + tick, self.graph.origin.Z,
                                               self.graph.origin.X - self.tick_size, self.graph.origin.Y + tick,
                                               self.graph.origin.Z) for tick in tick_values]
            # Tick values
            elements['tick_text'] = [EPiCVisualisations.bakeable_text_from_str(str(int(tick)),
                                                                               text_size=self.text_size,
                                                                               align_right=True,
                                                                               text_location=((
                                                                                                      self.graph.origin.X - self.tick_size - self.text_padding),
                                                                                              self.graph.origin.Y + tick_normalised - (
                                                                                                      self.text_size / 2),
                                                                                              self.graph.origin.Z)) for
                                     tick_normalised, tick in
                                     zip(tick_values, tick_values_not_normalised)]

        def _create_axis_lines(self, elements):
            """
            Create the axis lines for the graph
            :param elements: A dictionary of visualisation elements to be populated
            """
            elements['axis_lines'] = [Geometry.Line(self.graph.origin.X, self.graph.origin.Y, self.graph.origin.Z,
                                                    self.graph.origin.X,
                                                    self.graph.origin.Y + self.graph_preferences.graph_height,
                                                    self.graph.origin.Z),
                                      Geometry.Line(self.graph.origin.X, self.graph.origin.Y, self.graph.origin.Z,
                                                    self.graph.origin.X + self.graph_preferences.graph_width
                                                    - self.graph_preferences.space_between_graphs, self.graph.origin.Y,
                                                    self.graph.origin.Z)]

        def _create_column_group_labels(self, elements):
            """
            Create the column group names (and sub-group names) for the graph
            :param elements: A dictionary of visualisation elements to be populated
            """
            if 'sub_group' in [y for x in self.graph.column_group_names.values() for y in x.keys()]:
                for subgroup in self.graph.column_group_names.values():
                    if 'sub_group' in subgroup:
                        new_text_box_y_extent = self._generate_group_labels(elements, subgroup['sub_group'])
                self._generate_group_labels(elements, self.graph.column_group_names, new_text_box_y_extent)
            else:
                self._generate_group_labels(elements, self.graph.column_group_names)

        def _generate_group_labels(self, elements, labels, text_box_y_extent=False):
            """
            Generate a group label, or sub-group label for the graph
            :param elements: A dictionary of visualisation elements to be populated
            :param labels: A list of labels and label locations
            :param text_box_y_extent: y_axis location of the nearest test (above)
            :return: text_box_y_extent needed to generate sub-label locations
            """

            if not text_box_y_extent:
                text_box_y_extent = min(text.get_Boundingbox().GetCorners()[0].Y for text in elements['column_names'])

            for key, value in labels.items():
                if 'group_label_origin_x' in value:
                    if 'column_section_names' not in elements:
                        elements['column_section_names'] = []
                    if 'column_section_lines' not in elements:
                        elements['column_section_lines'] = []
                    elements['column_section_names'].append(EPiCVisualisations.bakeable_text_from_str(key,
                                                                                                      text_size=self.text_size,
                                                                                                      bold=True,
                                                                                                      text_rotation=90,
                                                                                                      align_top=True,
                                                                                                      text_location=(
                                                                                                          value[
                                                                                                              'group_label_origin_x'],
                                                                                                          text_box_y_extent
                                                                                                          - (
                                                                                                              self.graph_preferences.graph_spacing),
                                                                                                          (value[
                                                                                                              'group_label_origin_z'])
                                                                                                      )))

                    elements['column_section_lines'].append(Geometry.Line(value['group_label_origin_x_line_start'],
                                                                          text_box_y_extent - (
                                                                                  self.graph_preferences.graph_spacing / 3),
                                                                          self.graph.origin.Z,
                                                                          value['group_label_origin_x_line_end'],
                                                                          text_box_y_extent
                                                                          - (self.graph_preferences.graph_spacing / 3),
                                                                          self.graph.origin.Z))
            if 'column_section_names' in elements:
                text_box_y_extent = min(text.get_Boundingbox().GetCorners()[0].Y for text
                                        in elements['column_section_names'])
            return text_box_y_extent

        def _create_column_labels(self, elements):
            """
            Create column labels for the graph
            :param elements: A dictionary of visualisation elements to be populated
            """

            elements['column_names'] = [EPiCVisualisations.bakeable_text_from_str(column.name,
                                                                                  text_size=self.text_size,
                                                                                  text_rotation=90,
                                                                                  align_top=True,
                                                                                  text_location=(
                                                                                      column.origin.X + self.column_spacing / 2,
                                                                                      column.origin.Y -
                                                                                      (self.column_spacing / 2),
                                                                                      column.origin.Z)) for num, column
                                        in
                                        enumerate(self.graph.columns)]

        @staticmethod
        def create_list_of_ticks(data_list, zero_val=0, max_ticks=10, normalised_y_axis_height=False):
            """
            A tool that calculates optimal tick sizes based on list values
            Adapted from code by Shaobo Guan (2017)
            https://stackoverflow.com/questions/4947682/intelligently-calculating-chart-tick-positions

            :param data_list: a list to evaluate
            :param max_ticks: max number of ticks, an interger, defaults to 10
            :param zero_val: y-axis zero value for the graph, defaults to 0
            :return: tick size
            """

            data_span = max(data_list) - zero_val

            # scale data by the order of 10
            scale = 10.0 ** floor(log10(data_span))

            # possible tick sizes in range [1, 10]
            standard_tick_size = [5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01]

            # initial tick size for normalised data
            initial_tick_size = 1.0

            # every loop reduces tick size
            for i in range(len(standard_tick_size)):

                # number of ticks for the current tick size
                num_tick = data_span / scale / standard_tick_size[i]

                # break loop when tick limit reached
                if num_tick > max_ticks:
                    initial_tick_size = standard_tick_size[i - 1]
                    break

            # resize to original data
            tick_size = initial_tick_size * scale
            ticks = ceil(tick_size)

            # Normalise the y-axis height
            if normalised_y_axis_height:
                return [((ticks * num) / max(data_list)) * normalised_y_axis_height for num in range(10) if
                        ticks * num < max(data_list)]
            else:
                return [ticks * num for num in range(10) if ticks * num < max(data_list)]


class EPiCAssembly:
    """
    An EPiC Assembly, enabling the combination of various EPiC materials and the calculation of associated embodied
    environmental flows
    """

    template_flows = OrderedDict([('initial', dict()),
                                  ('initial_wastage', dict()),
                                  ('recurrent', dict()),
                                  ('recurrent_wastage', dict()),
                                  ('life_cycle', dict()),
                                  ('life_cycle_wastage', dict()),
                                  ])

    unit_calculation = {'no.': None,
                        'm': ghcomponents.Length,
                        'm²': ghcomponents.Area,
                        'm³': ghcomponents.Volume}

    def __str__(self):
        return self.print_report(print_as_str=True)

    def __init__(self, selected_geometry, name, service_life, wastage, comments,
                 epic_materials, assembly_units, category=None):
        """
        :param selected_geometry: a list of rhino geometries
        :param name: the name of the assembly (str)
        :param service_life: the service_life of the assembly, overriding the service_span of all nested materials (int)
        :param wastage: wastage coefficient of the assembly in %, overriding the wastage coeffs of nested mats (float)
        :param comments: a custom comment (str)
        :param epic_materials: a list of tuples, item 0 the epic mat instance and item 1 being the quantity of material
        :param assembly_units: the functional unit of the assembly (str), e.g. m²
        :param category: the assembly category, used in graph comparisons e.g. Interior Walls, Exterior Walls
        """

        self.output_geometry = []
        self.component_type = 'EPiCAssembly'
        self.name = remove_commas_and_flatten_list_for_csv_export(name) if name else 'EPiC Assembly'
        self.category = self.name if not category else remove_commas_and_flatten_list_for_csv_export(category)
        self.comments = remove_commas_and_flatten_list_for_csv_export(comments) if comments else ''
        self.service_life = abs(service_life) if service_life else None
        self.assembly_units = assembly_units

        # A zero value will override the EPiCDB wastage coefficient
        if wastage:
            self.wastage_override = abs(wastage) / 100
        elif wastage == 0:
            self.wastage_override = 0.
        else:
            self.wastage_override = None

        self.total_units, self.individual_units = \
            self.verify_input_and_calculate_geometry_units(selected_geometry, assembly_units)

        self.selected_geometry = selected_geometry
        # create attribute to store inputted geometry

        # list of lists of EPiC materials, sublists contain an instance of an EPiC material
        # in index 0 and the quantity in 1
        self.epic_materials = [[y[0][0], abs(y[1])] for y in epic_materials]

        # run calculations
        self.flows = self.calculate_flows()
        self.recalculated_flows = self.calculate_flows()

    def verify_input_and_calculate_geometry_units(self, selected_geometry, assembly_units):
        """
        Verify input geometry based on the FU of the selected assembly. Calculate unit values for each item
        :param selected_geometry: a list of geometry inputs and numerical input values
        :param assembly_units: functional unit used for the selected geometry
        :return: total_units, individual_units
        """

        individual_units = []
        total_units = 0

        for num, geometry in enumerate(selected_geometry):
            if geometry:
                # Allow numerical input
                if isinstance(geometry, (int, float)):
                    _value = geometry

                # Count each geometry item
                elif assembly_units == 'no.':
                    _value = 1

                elif assembly_units == 'm':
                    # Test if geometry is a line, curve or polyline
                    if not isinstance(geometry, (Geometry.ArcCurve,
                                                 Geometry.BezierCurve,
                                                 Geometry.BrepEdge,
                                                 Geometry.BrepLoop,
                                                 Geometry.Curve,
                                                 Geometry.Line,
                                                 Geometry.LineCurve,
                                                 Geometry.NurbsCurve,
                                                 Geometry.Polyline,
                                                 Geometry.PolyCurve,
                                                 Geometry.PolylineCurve)):
                        raise TypeError()
                    _value = self.unit_calculation[assembly_units](geometry)

                elif assembly_units == 'm²':
                    # Test if this is a surface
                    # Create surface from polyline inputs
                    if isinstance(geometry, (Geometry.PolylineCurve, Geometry.Polyline)):
                        if geometry.IsClosed and geometry.IsPlanar():
                            geometry = Geometry.Brep.CreatePlanarBreps(geometry)[0]
                        else:
                            raise TypeError()
                    # Allow Brep - but only if it is not a solid
                    elif isinstance(geometry, Geometry.Brep):
                        if geometry.IsSolid:
                            raise TypeError()
                    elif not isinstance(geometry, (Geometry.BezierSurface,
                                                   Geometry.BrepFace,
                                                   Geometry.Surface,
                                                   Geometry.Rectangle3d,
                                                   Geometry.Mesh,
                                                   Geometry.MeshNgon,
                                                   Geometry.NurbsSurface,
                                                   Geometry.PlaneSurface,
                                                   Geometry.SubD,
                                                   Geometry.SubDFace)):
                        raise TypeError()
                    _value = self.unit_calculation[assembly_units](geometry)[0]

                elif assembly_units == 'm³':
                    # Test if this is a Brep, line or surface
                    if not isinstance(geometry, (Geometry.Brep,
                                                 Geometry.Extrusion)):
                        raise TypeError()
                    _value = self.unit_calculation[assembly_units](geometry)[0]

                else:
                    raise ValueError('No functional unit found for assembly')

                total_units += _value
                individual_units.append(_value)
                if not isinstance(geometry, (int, float)):
                    self.output_geometry.append(geometry)
        return abs(total_units), individual_units

    def _calculate_flows(self, materials_list, flow, wastage_only=False, period_of_analysis=None, quantity=None):
        """
        Calculates embodied environmental flows
        :param materials_list: the list of EPiC materials for which to run the calculations
        :param flow: an embodied environmental flow, e.g. energy
        :param period_of_analysis: period of analysis for calculating the flows
        :param wastage_only: specify if we only want to calculate wastage
        :param quantity: the quantity of assembly to use, specify when we want results by geometry
        :return:
        """

        if wastage_only:
            base_quantity = 0.
        else:
            base_quantity = 1.

        if quantity is None:
            quantity = self.total_units

        if self.wastage_override:
            result = [quantity * abs(m[1]) * getattr(m[0], flow) * (base_quantity + self.wastage_override) for m
                      in materials_list]

        elif self.wastage_override == 0:  # Forcing wastage to be zero
            result = [quantity * abs(m[1]) * getattr(m[0], flow) * base_quantity for m in materials_list]
        else:
            result = [quantity * abs(m[1]) * getattr(m[0], flow) * (base_quantity + getattr(m[0], 'wastage'))
                      for m in
                      materials_list]

        if period_of_analysis is None:
            pass
        elif period_of_analysis == 0:  # we are forcing recurrent env flows to be zero
            result = [0.]
        elif period_of_analysis > 0 and self.service_life:  # we calculate only the recurrent embodied flows

            replacements = _get_num_replacements(period_of_analysis, self.service_life)
            result = [ef * replacements for ef in result]
        elif period_of_analysis > 0 and not self.service_life:
            recurrent_results = []
            for embodied_flow, material in zip(result, materials_list):
                try:
                    recurrent_results.append(
                        embodied_flow * _get_num_replacements(period_of_analysis, getattr(material[0], 'service_life')))
                except (ZeroDivisionError, TypeError):  # if the material service life is 0 or None
                    recurrent_results.append(0.)  # no replacement
            result = recurrent_results

        return sum(result)

    def _fill_flows_dict(self, period_of_analysis=None, materials_list=None, quantity=None):
        """
        Calculates the initial embodied environmental flows for a list of materials
        :param period_of_analysis: the period of analysis in years (int)
        :param materials_list: a list of EPiC materials (list of tuples)
        :param quantity: the quantity of assembly to run the calculation for, use only when calculating by geometry
        """

        if materials_list is None:
            materials_list = self.epic_materials

        results = copy.deepcopy(self.template_flows)
        for flow_type in results.keys():
            for env_flow in DEFINED_FLOWS.keys():
                setup = {'materials_list': materials_list, 'flow': env_flow, 'quantity': quantity}
                if 'wastage' in flow_type:
                    setup['wastage_only'] = True
                if 'recurrent' in flow_type:
                    if period_of_analysis is None:
                        # set the period of built_assets to zero to force zero recurrent flows
                        setup['period_of_analysis'] = 0
                    else:
                        setup['period_of_analysis'] = period_of_analysis

                if 'life' not in flow_type:
                    results[flow_type][env_flow] = self._calculate_flows(**setup)
                else:
                    if 'wastage' in flow_type:
                        initial = results['initial_wastage'][env_flow]
                        recurrent = results['recurrent_wastage'][env_flow]
                    else:
                        initial = results['initial'][env_flow]
                        recurrent = results['recurrent'][env_flow]

                    results[flow_type][env_flow] = initial + recurrent
        return results

    def calculate_flows(self, period_of_analysis=None):
        """
        Calculates all flows, at the assembly level, as well as by material and by geometry
        :param period_of_analysis: The period of built_assets used for the calculation of environmental flows
        :return: a dictionary, that follows the template dictionary
        """
        result = self._fill_flows_dict(period_of_analysis)

        # calculate the same by material
        result['by_material'] = {}
        for material, quantity in self.epic_materials:
            mat_name = material.name
            by_material = self._fill_flows_dict(period_of_analysis, materials_list=[[material, quantity]])
            if mat_name not in result['by_material']:
                by_material.update([('quantity', quantity), ('material_object', material), ('material_name', mat_name)])
            else:
                # Merge together any materials that have the same name
                by_material = sum_numerical_dictionary_values(result['by_material'][mat_name], by_material)
                by_material['quantity'] += quantity
                if by_material['material_object'].material_id == material.material_id:
                    pass
                else:
                    raise ValueError("Mismatched material name in 'by_material' calculation")
            result['by_material'][mat_name] = by_material
        return result

    def print_report(self, initial_flow=True, assembly_part_details=True, print_as_str=False):
        """
        Print a report for the Assembly with all of the flow and material values & metadata
        :param initial_flow: Specify if this is the initial flow
        :param assembly_part_details: Provide details on the different geometry in the assembly
        :param print_as_str: returns the results as a string
        :return: string (if print_as_str=True), otherwise a list
        """

        assembly_units_dict = {
            'm³': ['Total volume: ', 'Number of volumes (parts): ', 'Volume: '],
            'm²': ['Total area: ', 'Number of surfaces (parts): ', 'Area: '],
            'm': ['Total linear meters: ', 'Number of lines/curves (parts): ', 'Linear meters: '],
            'no.': ['Total number of units: ', 'Number of units (parts): ', 'Units: '],
        }

        mat_attributes = []
        assembly_attributes = []
        assembly_attributes.append('<< {} >>'.format(self.name))
        selected_geometry_count = str(len(self.selected_geometry))
        unit = self.assembly_units

        assembly_attributes.append(assembly_units_dict[unit][0] + str(self.total_units) + unit)
        if unit != 'no.':
            assembly_attributes.append(assembly_units_dict[unit][1] + selected_geometry_count)

        if self.wastage_override:
            assembly_attributes.append('Wastage override: {}%'.format(str(self.wastage_override * 100)))

        if self.service_life:
            assembly_attributes.append('Service Life override: {} years'.format(str(self.service_life)))

        if self.comments:
            assembly_attributes.append('Comments: {}'.format(str(self.comments)))
        assembly_attributes.append('')

        if initial_flow is True:
            results_dict = self.flows
        else:
            results_dict = self.recalculated_flows

        for flow in DEFINED_FLOWS.keys():
            if results_dict['recurrent'][flow] > 0:
                assembly_attributes.append(
                    '{}: {}'.format(
                        'Life cycle embodied ' + DEFINED_FLOWS[flow]['print_name'] + ' (' + DEFINED_FLOWS[flow][
                            'unit'] + ')',
                        results_dict['life_cycle'][flow]))
                if results_dict['life_cycle_wastage'][flow] > 0:
                    assembly_attributes.append(
                        '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                            results_dict['life_cycle_wastage'][flow]))

            assembly_attributes.append(
                '{}: {}'.format(
                    'Initial embodied ' + DEFINED_FLOWS[flow]['print_name'] + ' (' + DEFINED_FLOWS[flow]['unit'] + ')',
                    results_dict['initial'][flow]))

            if results_dict['initial_wastage'][flow] > 0:
                assembly_attributes.append(
                    '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                        results_dict['initial_wastage'][flow]))

            if results_dict['recurrent'][flow] > 0:
                assembly_attributes.append(
                    'Recurrent embodied ' + DEFINED_FLOWS[flow]['print_name'] + ' (' + DEFINED_FLOWS[flow][
                        'unit'] + '): {}'.format(results_dict['recurrent'][flow]))
            if results_dict['recurrent_wastage'][flow] > 0:
                assembly_attributes.append(
                    '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                        results_dict['recurrent_wastage'][flow]))
            assembly_attributes.append('')

        assembly_attributes.append('Materials in assembly: {}'.format(str(len(self.epic_materials))))

        for mat_num, mat in enumerate(self.epic_materials):
            assembly_attributes.append('Material {}: {}'.format(mat_num + 1, mat[0].name))
            assembly_attributes.append(
                '--- Qty: {}{} / {}'.format(mat[1], mat[0].functional_unit, self.assembly_units))
            assembly_attributes.append(
                '--- Total: {}{}'.format(mat[1] * self.total_units, mat[0].functional_unit))

        mat_attributes.append(assembly_attributes)

        if assembly_part_details is True:
            if self.assembly_units != 'no.':
                for num, geom in enumerate(self.selected_geometry):
                    part_attributes = list()
                    part_attributes.append('')
                    part_attributes.append(
                        'Assembly Part {} of {}'.format(str(num + 1), selected_geometry_count))
                    if isinstance(geom, (int, float)):
                        part_units = geom
                    else:
                        if self.assembly_units == 'm²':
                            part_units = ghcomponents.Area(geom)[0]
                        elif self.assembly_units == 'm³':
                            part_units = ghcomponents.Volume(geom)[0]
                        elif self.assembly_units == 'm':
                            part_units = ghcomponents.Length(geom)

                    part_attributes.append(assembly_units_dict[unit][2] + str(part_units) + self.assembly_units)
                    mat_attributes.append(part_attributes)

        if print_as_str:
            print_str = []
            for mat in mat_attributes:
                print_str.append('\n'.join(mat))
            print_str = '\n'.join(print_str)
            return print_str

        return mat_attributes

    @staticmethod
    def create_list_of_input_materials_and_qty(component, units, args):
        """
        Create a list of input materials and their quantity. Only create an extry when there is valid data for both.
        :param component: Base component to modify
        :param units: Functional unit used for component
        :param args: Arguments to iterate through
        :return: A nested list containing each material and quantity [[mat, qty], [mat, qty]]
        """
        material_list = []
        for num, arg in enumerate(args):  # Make a list of all the valid materials and material quantities

            # Handle list values passed from component. Only use first list item
            #todo develop cleaner way to deal with list items, rather than using try except
            try:
                arg = arg[0]
            except:
                pass

            # todo changing the NickName with Rhino 8 will break the component. Future fix.
            if (num + 2) % 2 == 0:
                if arg and 'functional_unit' in dir(arg):  # Check if material has the attribute (functional unit). Will return False for a number or string
                    material = [arg]
                    component.Params.Input[7+num].NickName = component.Params.Input[7+num].Name \
                        = "Material: " + str(arg.name)
                    component.Params.Input[8+num].NickName = component.Params.Input[8+num].Name \
                        = "({0} / {1})".format(arg.functional_unit, units)
                else:
                    material = None
                    component.Params.Input[7 + num].NickName = "Material " + str(num/2 + 1)
                    component.Params.Input[8 + num].NickName = "Material " + str(num/2 + 1) + \
                                                               ": Quantity (FU / {0})".format(units)
            else:
                if arg and material:
                    material_list.append([material, arg])
        return material_list

class EPiCAnalysis:
    """
        A component that visualises life cycle assessment results and generates CSV reports.
        Uses EPiCAssembly and EPiCBuiltAssets items to generate assessment report.
        """

    def __str__(self):
        return self.print_report()

    def __init__(self, name='EPiCAnalysis', epic_assemblies=None, period_of_analysis=100,
                 graph_origin=(0, 0, 0), analysis_type='total', sort_graph=True, graph_scale=1, generate_graph=True,
                 comments=''):
        """
        :param name: Name of the built_assets
        :param epic_assemblies: A single, or multiple EPiCAssembly items. These are used to calculate the assessment.
        :param period_of_analysis: The period of time (in years) used for the life cycle assessment
        :param graph_origin: Origin point for the graph visualisation element. defaults to (0, 0, 0)
        :param analysis_type: Type of built_assets to conduct ('total', 'by_smaterial' OR 'by assembly')
        :param sort_graph: Specifies if the graph should be sorted from highest value to lowest. True/False.
        :param graph_scale: Scale of the graph visualisation. 1=normal size 0.5=half size 2=double size
        :param generate_graph: Specifies if a graph visualisation should be generated. True/False.
        :param comments: Comments will be shown the in report .csv.
        """

        # Set attributes and variables
        self.component_type = 'EPiCAnalysis'
        self.name = remove_commas_and_flatten_list_for_csv_export(name) if name else 'EPiCAnalysis'
        self.comments = remove_commas_and_flatten_list_for_csv_export(comments) if comments else ''
        self.period_of_analysis = period_of_analysis

        list_of_assembly_names = []

        # Code to enable built_assets for built_assets / comparison of multiple assemblies.
        built_asset_objects = [x for x in epic_assemblies if x.component_type == 'EPiCBuiltAsset'
                               or x.component_type == 'EPiCAnalysis']

        epic_assemblies = [x for x in epic_assemblies if x.component_type == 'EPiCAssembly']

        if built_asset_objects:
            for asset in built_asset_objects:
                epic_assemblies += asset.epic_assemblies

        self.epic_assemblies = epic_assemblies

        # Create a list of all of the materials (and qty) in the Analysis component
        self.epic_materials = [(y[0], y[1] * x.total_units) for x in epic_assemblies for y in x.epic_materials if x]

        # Recalculate the flows, based on the period of analysis
        for assembly in epic_assemblies:
            assembly.recalculated_flows = assembly.calculate_flows(period_of_analysis)

        for assembly in epic_assemblies:
            list_of_assembly_names.append(assembly.name)

        self.flows = self.sum_by_assembly_and_material()

        # Generate a graph element if this is set to true.
        if generate_graph:
            if built_asset_objects:
                self.graph_visualisations = EPiCGraph(built_asset_objects, graph_origin=graph_origin,
                                                      analysis_type=analysis_type,
                                                      sort_graph=sort_graph, graph_scale=graph_scale)
            else:
                self.graph_visualisations = EPiCGraph(self, graph_origin=graph_origin, analysis_type=analysis_type,
                                                      sort_graph=sort_graph, graph_scale=graph_scale)
            self.elements_to_render = self.graph_visualisations.elements_to_render
        else:
            self.graph_visualisations = None
            self.elements_to_render = None

    @staticmethod
    def process_inputs(epic_inputs, analysis_type='total', graph_origin=(0, 0, 0), graph_scale=1,
                       period_of_analysis=None, report_name='EPiC Analysis',
                       epic_assemblies_name='Assembly Collection'):
        """
        :param epic_inputs: Inputs - either EPiC_Assembly and/or EPiC_Built_Asset components
        :param analysis_type: Type of built_assets to be used for graph visualisations. 'total', 'by_material',
        'by_assembly', or 'by_assembly_and_material'
        :param graph_origin: Origin point for the graph. Defaults to (0, 0, 0)
        :param graph_scale: Graph scale. 1=Default scale
        :param period_of_analysis: The period of built_assets to be used for calculations.
        Default value of None - indicating that no recurrent calculations will be made.
        :param report_name: Name for the Analysis Report
        :param epic_assemblies_name: Default name for a group of EPiCAssembly inputs
        :return:
        epic_analysis - an EPiCAnalysis class instance
        epic_inputs - sorted list of inputs
        """

        # Set default values for the variables
        graph_origin = (0, 0, 0) if not graph_origin else graph_origin
        graph_scale = 1 if not graph_scale else graph_scale
        analysis_type = 'total' if not analysis_type else analysis_type

        # Initialise variables
        epic_analysis = None
        _epic_analyses = []

        # Remove null values from input list
        epic_inputs = [x for x in epic_inputs if x]

        # Clean the epic_inputs list, and separate EPiCAssembly and EPiCBuiltAsset items for built_assets
        epic_inputs = [x for x in epic_inputs if x.component_type == 'EPiCAssembly'
                       or x.component_type == 'EPiCBuiltAsset']
        epic_assemblies = [x for x in epic_inputs if x.component_type == 'EPiCAssembly']
        built_assets = [x for x in epic_inputs if x.component_type == 'EPiCBuiltAsset']

        if built_assets:
            for built_asset in built_assets:
                _epic_analyses.append(EPiCAnalysis(built_asset.name,
                                                   [built_asset],
                                                   period_of_analysis, graph_origin=graph_origin,
                                                   analysis_type=analysis_type, graph_scale=graph_scale,
                                                   generate_graph=False))
        if epic_assemblies:
            _epic_analyses.append(EPiCAnalysis(epic_assemblies_name,
                                               epic_assemblies,
                                               period_of_analysis, graph_origin=graph_origin,
                                               analysis_type=analysis_type, graph_scale=graph_scale,
                                               generate_graph=False))
        if _epic_analyses:
            epic_analysis = EPiCAnalysis(report_name,
                                         _epic_analyses,
                                         period_of_analysis, graph_origin=graph_origin,
                                         analysis_type=analysis_type, graph_scale=graph_scale,
                                         generate_graph=True)
        return epic_analysis, epic_inputs

    # Region baking
    # TODO: Fix colouring for baked objects
    def BakeGeometry(self, doc, att, id):
        id = Guid.Empty
        if self.elements_to_render is None:
            return False, id

        if att is None:
            att = doc.CreateDefaultAttributes()

        if self.elements_to_render:
            for graph_element in self.elements_to_render:

                # Bake legend lines
                if isinstance(graph_element, Geometry.Line):
                    doc.Objects.AddLine(graph_element, att)

                # Bake graph text
                elif isinstance(graph_element, EPiCVisualisations.EPiCText):
                    if graph_element.m_value is None:
                        pass
                    else:
                        doc.Objects.AddText(graph_element.m_value, att)

                # Bake graph columns
                elif isinstance(graph_element, EPiCVisualisations.GraphSegmentGeometry):
                    doc.Objects.AddRectangle(graph_element.m_value, att)
                    att.ObjectColor = graph_element.fill_colour
                    doc.Objects.AddHatch(graph_element.fill, att)

        id = doc.Objects
        return True, id

    def sum_by_assembly_and_material(self):
        """
        Sums all flows by assembly and material
        :return:a dictionary, containing the same keys as the flows dictionary in an assembly and materials
        """
        result = OrderedDict()

        for assembly in self.epic_assemblies:
            self._sum_by_assembly_and_material(result, assembly.recalculated_flows,
                                               by_material=True,
                                               assembly=assembly)

            # create the 'by_assembly' dictionary. This will contain a nested 'by_material' dict
            if 'by_assembly' not in result:
                result['by_assembly'] = dict()
            if assembly.category not in result['by_assembly']:
                result['by_assembly'][assembly.category] = dict()
            self._sum_by_assembly_and_material(result['by_assembly'][assembly.category], assembly.recalculated_flows,
                                               by_material=True)

        return result

    def fetch_geometry_as_list(self):
        """
        Compiles a list of all geometries contained within each EPiC Assembly and EPiC Built Assets
        :return: a list of geometries
        """

        # Exclude numbers from geometry output and change to datatree structure
        return list_to_datatree([[x for x in assembly.output_geometry if not isinstance(x, (float, int))]
                                 for assembly in self.epic_assemblies])

    def _sum_by_assembly_and_material(self, final_dict_result, iterative_dict_result,
                                      by_material=False, assembly=False):
        """
        Recursive method to move within nested dicts and calculate the sum
        :param final_dict_result: The final dictionary result
        :param iterative_dict_result: The iterative dictionary result
        :param by_material: if True, iterate through the by_material dictionary
        :param assembly: An EPiCAssembly item to get materials from
        """
        for k, v in iterative_dict_result.items():

            if isinstance(v, dict) or isinstance(v, OrderedDict):
                if k == 'by_material':
                    if by_material:
                        self._sum_by_assembly_and_material(final_dict_result.setdefault(k, dict()), v,
                                                           by_material=True, assembly=assembly)
                else:
                    # Create a new 'by_assembly' dictionary nested within each material dictionary and populate
                    self._sum_by_assembly_and_material(final_dict_result.setdefault(k, dict()), v)
                    if assembly and by_material:
                        if len(assembly.epic_materials) > 0:
                            if k in [mat[0].name for mat in assembly.epic_materials]:
                                if 'by_assembly' not in final_dict_result[k]:
                                    final_dict_result[k]['by_assembly'] = dict()
                                if assembly.name not in final_dict_result[k]['by_assembly']:
                                    final_dict_result[k]['by_assembly'][assembly.name] = dict()
                                self._sum_by_assembly_and_material(
                                    final_dict_result[k]['by_assembly'][assembly.name], v)


            elif isinstance(v, float):
                final_dict_result[k] = final_dict_result.get(k, 0) + v

            elif isinstance(v, str):  # for material column_group_name
                if k in final_dict_result:
                    if not final_dict_result[k] == v:
                        final_dict_result[k] = final_dict_result.get(k, '') + '/' + v
                else:
                    final_dict_result[k] = v
            else:  # for EPiCMaterial object file
                final_dict_result[k] = v

    def generate_analysis_breakdown_for_outputs(self, analysis_type='total'):
        """
        Generate outputs for the EPiCAnalysis component based on the built_assets type
        :param analysis_type: Type of built_assets used ('total,'by_material' OR 'by_assembly')
        :return: list of outputs for the EPiCAnalysis component
        """
        results_list = []
        output_keys = []

        if not analysis_type:
            analysis_type = 'total'

        for flow in DEFINED_FLOWS.keys():
            results_list.append(None)
            for flow_type in self.flows.keys():
                if flow_type != 'by_material' and flow_type != 'by_assembly':
                    if analysis_type == 'by_assembly_and_material':
                        _mats = set([y for x in self.flows['by_assembly'].values() for y in x['by_material'].keys()])
                        _assemblies = self.flows['by_assembly'].keys()
                        nested_list = []
                        output_keys = []
                        for key, assembly in self.flows['by_assembly'].items():
                            _assembly_container = []
                            mat_keys = []
                            for mat in _mats:
                                mat_keys.append(str(key) + ': ' + mat)
                                if mat in assembly['by_material']:
                                    _assembly_container.append(assembly['by_material'][mat][flow_type][flow])
                                else:
                                    _assembly_container.append(0)
                            nested_list.append(_assembly_container)
                            output_keys.append(mat_keys)
                        results_list.append(list_to_datatree(nested_list))
                        output_keys = list_to_datatree(output_keys)
                    elif analysis_type == 'by_assembly':
                        results_list.append([x[flow_type][flow] for x in self.flows['by_assembly'].values()])
                        output_keys = self.flows['by_assembly'].keys()
                    elif analysis_type == 'by_material':
                        results_list.append([x[flow_type][flow] for x in self.flows['by_material'].values()])
                        output_keys = self.flows['by_material'].keys()
                    elif analysis_type == 'total':
                        results_list.append(self.flows[flow_type][flow])
                        output_keys = 'total'

        return [self, self.elements_to_render, output_keys] + results_list + [None] + [self.fetch_geometry_as_list()]

    def print_report(self):
        """
        Print all EPiCAssembly inputs/outputs and results of the life cycle assessment calculation
        :return: A string with all of the report results
        """

        report_writer = []
        temp_report = []
        for assembly in self.epic_assemblies:
            if self.period_of_analysis:
                pass
            else:
                self.period_of_analysis = None
            assembly.recalculated_flows = assembly.calculate_flows(self.period_of_analysis)
        temp_report.append('<<<' + str(self.name) + '>>>')
        if isinstance(self, EPiCBuiltAsset):
            temp_report.append('Built Asset')
        else:
            temp_report.append('Assessment duration: {} years'.format(self.period_of_analysis))
        temp_report.append('Number of Assemblies: {}'.format(len(self.epic_assemblies)))

        for flow in DEFINED_FLOWS.keys():
            temp_report.append('Total embodied ' + flow + ' (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                sum([x.recalculated_flows['life_cycle'][flow] for x in self.epic_assemblies])))
            temp_report.append(
                '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                    sum([x.recalculated_flows['life_cycle_wastage'][flow] for x in self.epic_assemblies])))

            temp_report.append('Initial embodied ' + flow + ' (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                sum([x.recalculated_flows['initial'][flow] for x in self.epic_assemblies])))
            temp_report.append(
                '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                    sum([x.recalculated_flows['initial_wastage'][flow] for x in self.epic_assemblies])))

            temp_report.append('Recurrent embodied ' + flow + ' (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                sum([x.recalculated_flows['recurrent'][flow] for x in self.epic_assemblies])))
            temp_report.append(
                '--- of which wastage (' + DEFINED_FLOWS[flow]['unit'] + '): {}'.format(
                    sum([x.recalculated_flows['recurrent_wastage'][flow] for x in self.epic_assemblies])))

        report_writer.append(temp_report)

        for num, assembly in enumerate(self.epic_assemblies):
            temp_report = assembly.print_report(assembly_part_details=False, initial_flow=False)[0]
            report_writer.append(temp_report)

        # Return string value
        print_str = []
        for report in report_writer:
            print_str.append('\n'.join(report))
        return '\n'.join(print_str)


class EPiCBuiltAsset(EPiCAnalysis):
    """
    A single built asset containing multiple EPiCAssembly items
    """

    def __init__(self, *args, **kwargs):
        EPiCAnalysis.__init__(self, *args, **kwargs)
        self.period_of_analysis = 0
        self.component_type = 'EPiCBuiltAsset'


class EPiCBreakdown:
    """
    Enables breaking down embodied environmental flows into their shares of process data and input-output data.
    Works on EPiC Material, EPiC Assembly, EPiC Built Asset and EPiC Analysis - (only on the total).
    """

    def __init__(self, epic_entity):
        if isinstance(epic_entity, (EPiCMaterial, EPiCAssembly, EPiCBuiltAsset, EPiCAnalysis)):
            self.epic_entity = epic_entity
            self.breakdown_dict = copy.deepcopy(HYBRID_VALUE_BREAKDOWN_DICT)
        else:
            raise TypeError(
                'You can only breakdown the embodied environmental flows of an EPiCMaterial, EPiCAssembly, EPiCBuiltAsset and EPiCAnalysis')

    def breakdown_embodied_flows(self):
        """
        Breaks down the embodied environmental flows of the EPiC entity into its process and input-output components
        :return: the populated breakdown dict
        """
        return self.epic_entity.generate_breakdown_dict()


class EPiCDatabase:
    """
    Provides access to the EPiCDatabase through the use of queries. Data is held as a class attribute (database)
    """

    database = {}

    def __init__(self, local_directory=None):
        self.component_type = 'EPiCDatabase'
        self.custom_database = None

        if not self.database:
            if local_directory:
                with open(local_directory + os.sep + r'EPiC Grasshopper' + os.sep + PICKLE_DB, 'rb') as f:
                    self.database = cPickle.load(f)

        # Load set of categories in the database

        self.categories = EPiCDatabase.get_categories(self.database)
        self.dict_of_categories = EPiCDatabase.get_dict_of_categories(self.database)
        self.dict_of_ids_and_names = {key: self.database[key]['name'] for key in self.database.keys()}
        self.dict_of_legacy_names = {key: self.database[key]['Legacy_names'] for key in self.database.keys()}

    @staticmethod
    def get_categories(database):
        """
        Returns a set containing all categories in the database
        """
        return {x['Category'] for x in database.values() if x['Latest_Version']}

    @staticmethod
    def get_dict_of_categories(database):
        """
        Returns a dictionary of categories, which contains a list of mat ids [(mat_id, mat_name), (... , ...)]
        """
        # if the class instance already has a set of categories, use that, otherwise create a set

        if hasattr(database, 'categories'):
            categories = database.categories

        else:
            categories = EPiCDatabase.get_categories(database)

        return {category: dict([(id, EPiCMaterial._concatenate_mat_name_func_unit(mat['name'], mat['Functional Unit']))
                for id, mat in database.items() if mat['Category'] == category]) for category in categories}

    def load_custom_database(self, file_path, file_name):
        """
        Load a custom database file
        :param file_path: The full file path directory
        :param file_name: Name of database file
        """

        if file_path and file_name:
            try:
                with open(file_path + r'//' + file_name, 'rb') as f:
                    self.custom_database = cPickle.load(f)

                    # Overwrite categories
                    self.categories = EPiCDatabase.get_categories(self.custom_database)
                    self.dict_of_categories = EPiCDatabase.get_dict_of_categories(
                        self.custom_database)
                    self.dict_of_ids_and_names = {key: self.custom_database[key]['name']
                                                for key in self.custom_database.keys()}
                    self.dict_of_legacy_names = self.dict_of_ids_and_names
            except:
                self.custom_database = 'Error'
                raise (RuntimeError("Couldn't load database from: " + file_path + r'//' + file_name))

    def _query_for_name_or_old_mat_id(self, lookup_item):
        """
        Lookup material based on name, or legacy name.
        :param lookup_item: Name of the material to lookup
        :return: material ID as string
        """
        lookup_item = str(lookup_item)

        # Remove decoration from material name (if it exists)
        if '|' in lookup_item:
            lookup_item = EPiCMaterial.remove_func_unit_from_mat_name(lookup_item)

        # Search in the list of material names followed by a search of legacy names
        if lookup_item in self.dict_of_ids_and_names.values():
            return [key for key, value in self.dict_of_ids_and_names.items() if lookup_item == value][0]
        elif lookup_item in self.dict_of_legacy_names.values():
            return [key for key, value in self.dict_of_legacy_names.items() if lookup_item == value][0]
        return None

    def query(self, material_id, material_attributes=None):
        """
        Query the EPiC Database using a material name & optional attribute
        :param material_id: ID of the material S-String, I-Integer Region(SS)Year(IIII)Cat(SS)Material(III)Variation(II)
        :param material_attributes: Name of the attribute to return (e.g DOI, Functional Unit), or list of attributes
        :return: material dictionary OR material attribute (if specified)
        """
        query = None
        # Use the default database unless a custom database has been provided
        database = self.database if not self.custom_database else self.custom_database

        try:
            _ = database[material_id]
        except KeyError:
            material_id = self._query_for_name_or_old_mat_id(material_id)

        if material_attributes is None:
            try:
                query = database[material_id]
            except KeyError:
                raise TypeError('Material not found')

        else:
            try:
                if isinstance(material_attributes, list):
                    # if an attribute doesn't exist, return None for that list item
                    query = [database[material_id][attribute] if attribute in database[material_id]
                             else 'None'
                             for attribute in material_attributes]
                else:
                    query = database[material_id][material_attributes]
            except KeyError:
                raise TypeError('Material or material attribute not found')

        # Return None if there are no results
        if not isinstance(query, list):
            if isnan(query):
                return None
            else:
                return query
        else:
            # Remove nan values from the results and return
            return [x if not isnan(x) else None for x in query]
