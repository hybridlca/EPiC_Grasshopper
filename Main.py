import clr
import epic.epic as epic

clr.CompileModules("EPiC_Plugin_Modules_Only_v" + '_' + epic.__version__.replace('.','-') + ".ghpy",
                   "epic/epic.py", "epic/epic_plugin_assembly_info.py")

