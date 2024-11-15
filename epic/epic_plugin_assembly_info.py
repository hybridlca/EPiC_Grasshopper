# -*- coding: UTF-8 -*-

from datetime import date
import GhPython
import System

__author__ = "André Stephan & Fabian Prideaux"
__version__ = "1.02"
__date__ = date.today().strftime("%B %d, %Y")
__message__ = 'EPiC Plugin ' + __version__ + '\n' + __date__
epic_version = 'AU2024'


class AssemblyInfo(GhPython.Assemblies.PythonAssemblyInfo):
    def get_AssemblyName(self):
        return "EPiC"

    def get_AssemblyDescription(self):
        return """EPiC Grasshopper: A Plugin for analysing embodied environmental flows"""

    def get_AssemblyVersion(self):
        return __version__

    def get_AuthorName(self):
        return __author__

    def get_Id(self):
        return System.Guid("1f4e9641-a2a2-4578-a8af-dbb844d7e281")


