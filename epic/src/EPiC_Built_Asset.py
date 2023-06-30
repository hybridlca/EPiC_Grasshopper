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
Creates a built asset object using multiple EPiC_Assembly items

    Inputs:

        Asset_Name: Name for the Built Asset
        ***Optional***

        EPiC_Assemblies: In input one or more EPiC_Assembly objects
        (**REQUIRED)

    Outputs:
        EPiC_Built_Asset: Built Asset class with detailed report
        ***Connect that output to a panel for a summary***

        Geometry_by_Assembly: A collection of all selected geometries for each EPiC Assembly
"""

from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
import Grasshopper.Kernel.Data as ghp
from ghpythonlib.componentbase import executingcomponent as component
import ghpythonlib.treehelpers as th
import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)


class MyComponent(component):
    def RunScript(self, input_name, input_comments, null, epic_assemblies):

        # Component and version information
        __author__ = epic.__author__
        __version__ = "1.01"
        if __version__ == epic.__version__:
            self.Message = epic.__message__
        else:
            self.Message = epic.version_mismatch(__version__)
            self.AddRuntimeMessage(RML.Remark, self.Message)
        self.Name = "EPiC Built Asset"
        self.NickName = "EPiC Built Asset"

        if epic_assemblies:

            # Convert inputs to flat list
            epic_assemblies.Flatten(ghp.GH_Path(0))
            epic_assemblies = th.tree_to_list(epic_assemblies)

            # Provide a default name if none provided
            input_name = 'EPiC Built Asset' if not input_name else input_name[0]

            # Generate an EPiCBuiltAsset class object
            built_asset = epic.EPiCBuiltAsset(input_name, epic_assemblies, comments=input_comments)
            return [built_asset, None, built_asset.fetch_geometry_as_list()]
        else:
            self.AddRuntimeMessage(RML.Warning, "No input detected, please provide one/multiple EPiC_Assembly objects")
