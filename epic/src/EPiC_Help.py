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
Link to EPiC resources and information

    Inputs:
        >>Connect_Toggle_Switch_to_Open_EPiC_Database: Connect a toggle switch and set to True.
        This will open https://bit.ly/EPiC_Database in a web browser

        >>Connect_Toggle_Switch_to_Open_GitHub: Connect a toggle switch and set to True.
        This will open https://bit.ly/EPiCGrashopper_Bug in a web browser

        >>Connect_Toggle_Switch_to_Suggest_Feature: Connect a toggle switch and set to True.
        This will open https://bit.ly/EPiCGrasshopper_FeatureSuggestion in a web browser

        >>Connect_Toggle_Switch_to_Report_Issue/Bug: Connect a toggle switch and set to True.
        This will open https://bit.ly/EPiCGrashopper_Bug in a web browser
"""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel import GH_RuntimeMessageLevel as RML
import webbrowser

import epic

# Allow realtime feedback with external python files in grasshopper
epic = reload(epic)


class EPiCHelp(component):

    def RunScript(self, epic_database, github, suggest_feature, report_issue):

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

        # Open the EPiC Database or EPiC Grasshopper Bugs / Suggestions Google Form
        if epic_database:
            webbrowser.open("https://bit.ly/EPiC_Database", new=1)
        if report_issue:
            webbrowser.open("https://bit.ly/EPiCGrashopper_Bug", new=1)
        if suggest_feature:
            webbrowser.open("https://bit.ly/EPiCGrasshopper_FeatureSuggestion", new=1)
        if github:
            webbrowser.open("https://bit.ly/EPiCGrasshopperGitHub", new=1)
