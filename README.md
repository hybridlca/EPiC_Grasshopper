# EPiC Grasshopper
*A Plugin for analysing embodied environmental flows*

![EPiC Grasshopper](epic/img/EPiC_GH_Logo.jpg)

**Authors:** André Stephan, Fabian Prideaux

*Funded by the [Université Catholique de Louvain](https://www.uclouvain.be), Belgium*

## About:

EPiC Grasshopper is a plug-in for Grasshopper (Rhinoceros3D) used to quantify
life cycle embodied energy, greenhouse emissions and water for buildings and other built assets. It enables designers, 
engineers and other actors of the built environment to use the EPiC database directly within Grasshopper, 
in order to improve the life cycle embodied environmental performance of buildings and infrastructure assets.

Calculations are made using hybrid embodied environmental flow coefficients from the EPiC Database. 
EPiC Grasshopper enables direct access to all EPiC materials, allows combining them into construction assemblies, 
and in turn, into built assets. The plug-in provides advanced data visualisation and slicing capabilities, 
enabling its users to quickly evaluate the total life cycle embodied environmental flows of assemblies 
and/or built assets, compare them, and break them down by material contribution. 
EPiC Grasshopper enables users to define their own custom materials, to export results to csv and 
to suggest a feature or report a bug directly from Grasshopper.

### EPiC Database

![The EPiC Database](epic/img/EPiC_logo.png)

The EPiC Database is a comprehensive and consistent open-access Life Cycle Inventory of environmental flow coefficients for construction materials developed by the University of Melbourne. The database contains over 850 coefficients that can be incorporated into existing Life Cycle Assessment workflows and processes. 

Further information about the database, how it was compiled, and access to detailed datasets can be found at: www.epicdatabase.com.au

### License agreement
EPiC Grasshopper is open-source, and licensed under a GNU GPLv3 license agreement.
For more information visit: https://www.gnu.org/licenses/

### Plug-in download:
Download the latest compiled version of the plugin at [food4Rhino.](https://www.food4rhino.com/en/app/epic-grasshopper)

### Requirements and dependencies:
1. [Rhino3d](https://www.rhino3d.com/)
2. [Grasshopper](https://www.grasshopper3d.com/) (included in Rhino 7)

### Installation

- Download the latest compiled version of the plugin at [food4Rhino.](https://www.food4rhino.com/en/app/epic-grasshopper)
- Expand the downloaded zip file
- Delete any previous versions of EPiC Grasshopper

> **Windows Installation:**
> 1. Use the 220318_EPiC_Plugin_v<version>_installer.exe file and follow the prompts
> 2. Start Rhino/GH and enjoy EPiC Grasshopper

> **Manual installation (MAC OS and Windows):**
>
> 1. Copy the folder 'Libraries\EPiC Grasshopper' to the 'Components' folder of Grasshopper (in Grasshopper hit File>Special Folders>Components Folder)
> 2. Copy the folder 'User Objects\EPiC Grasshopper' to the 'User Objects' folder of Grasshopper (in Grasshopper hit File>Special Folders>User Objects Folder)
> 3. Restart Rhino
> 4. Enjoy EPiC Grasshopper

### Feedback
Please reach out on https://bit.ly/EPiCGrashopper_Bug, or get in contact via www.epicdatabase.com.au

### Disclaimer
The authors disclaim any liability, in whole or in part, arising from information contained in this plugin.
They do not take any responsibility for any action taken, decision-made, or result associated with use of this plugin

## EPiC Grasshopper Components


> ### EPiC Material
>*Select a material from the EPiC Database*
>
>![EPiC Material](epic/img/EPiC_Material_icon.png)
>
>> **Inputs:** *(Toggle_Switch_to_Activate, Material_Category, Selected_Material, Wastage_Coefficient_(%), Material_Service_Life_(Years), Energy_Reduction_Factor_(%), Water_Reduction_Factor_(%), GHG_Reduction_Factor_(%), Comments, Toggle_Switch_to_Open_EPiC_Database)*
>
>> **Outputs:** *(EPiC_Material, Embodied_Energy_Coefficient_(MJ/FU), Embodied_Water_Coefficient_(L/FU), Embodied_GHG_Coefficient_(kgCO₂e/FU), Digital Object Identifier (DOI), Density_(kg/m³), Functional_Unit, Wastage_Coefficient_(%),  Material_Service_Life_(Years), Disclaimer*)


>### EPiC Custom Material
> *Creates a custom material using custom environmental flows*
> 
>![EPiC Custom Material](epic/img/EPiC_Custom_Material_icon.png)
>
>> **Inputs:** *(Material_Name, Material_Category, Functional_Unit_(m,m²,m³,kg,no.), Density_(kg/m³), Embodied_Energy_Coefficient_(MJ/FU), Embodied_Water_Coefficient_(L/FU), Embodied_GHG_Coefficient_(kgCO₂e/FU), Wastage_Coefficient_(%), Material_Service_Life_(Years), Comments)*
>
>> **Outputs:** *(Custom_Material, Embodied_Energy_Coefficient_(MJ/FU), Embodied_Water_Coefficient_(L/FU), Embodied_GHG_Coefficient_(kgCO₂e/FU), Density_(kg/m³), Functional_Unit, Wastage_Coefficient_(%),  Material_Service_Life_(Years)*)

> ### EPiC Assembly — Units
> *Creates a unit assembly based on the selected geometry and EPiC Materials*
> 
> ![EPiC Assembly — Units](epic/img/EPiC_Unit_Assembly_icon.png)
>
>> **Inputs:** *(Assembly_Name, Assembly_Category, Assembly_Comments, Selected_Units_(no.), Service_Life_(Years)_Assembly_Override, Wastage_Coefficient_(%)_Assembly_Override)*
>
>> **Outputs:** *(EPiC_Assembly, Initial_Embodied_Energy_(MJ), Initial_Embodied_Water_(L), Initial_Embodied_GHG_(kgCO₂e), Geometry)*


> ### EPiC Assembly — Linear
> *Creates a linear assembly based on the selected geometry and EPiC Materials*
> 
> ![EPiC Assembly — Linear](epic/img/EPiC_Linear_Assembly_icon.png)
>
>> **Inputs:** *(Assembly_Name, Assembly_Category, Assembly_Comments, Selected_Lines_(m), Service_Life_(Years)_Assembly_Override, Wastage_Coefficient_(%)_Assembly_Override)*
>
>> **Outputs:** *(EPiC_Assembly, Initial_Embodied_Energy_(MJ), Initial_Embodied_Water_(L), Initial_Embodied_GHG_(kgCO₂e), Geometry)*

> ### EPiC Assembly — Surface
> *Creates a surface assembly based on the selected geometry and EPiC Materials*
>
> ![EPiC Assembly — Surface](epic/img/EPiC_Surface_Assembly_icon.png)
>
>> **Inputs:** *(Assembly_Name, Assembly_Category, Assembly_Comments, Selected_Surfaces_(m²), Service_Life_(Years)_Assembly_Override, Wastage_Coefficient_(%)_Assembly_Override)*
>
>> **Outputs:** *(EPiC_Assembly, Initial_Embodied_Energy_(MJ), Initial_Embodied_Water_(L), Initial_Embodied_GHG_(kgCO₂e), Geometry)*


> ### EPiC Assembly — Volumetric
> *Creates a volumetric assembly based on the selected geometry and EPiC Materials*
> 
> ![EPiC Assembly — Volumetric](epic/img/EPiC_Volumetric_Assembly_icon.png)
>
>> **Inputs:** *(Assembly_Name, Assembly_Category, Assembly_Comments, Selected_Volumes_(m³), Service_Life_(Years)_Assembly_Override, Wastage_Coefficient_(%)_Assembly_Override)*
>
>> **Outputs:** *(EPiC_Assembly, Initial_Embodied_Energy_(MJ), Initial_Embodied_Water_(L), Initial_Embodied_GHG_(kgCO₂e), Geometry)*


> ### EPiC Built Asset
> *Creates a built asset object using multiple EPiC_Assembly items*
> 
> ![EPiC Built Asset](epic/img/EPiC_Built_Asset_icon.png)
>
>> **Inputs:** *(Asset_Name, EPiC_Assemblies)*
>
>> **Outputs:** *(EPiC_Built_Asset, Geometry_by_Assembly)*

> ### EPiC Analysis
> *Calculates Embodied Environmental Flows and plots a stacked bar chart of the results, with the ability to generate a csv report*
>
> ![EPiC Analysis](epic/img/EPiC_Analysis_icon.png)
>
>
>> **Inputs:** *(Analysis_Name, EPiC_Assemblies_or_Built_Assets, Comparison_Values_(EPiC_Assemblies), Period_of_Analysis_(Years), Connect_Button_to_Load_Analysis_Types, Analysis_Type, Graph_Origin_Point, Graph_Scale, csv_Folder_location, Connect_Button_to_Generate_csv)*
>
>> **Outputs:** *(Detailed_Report_Information, Graph_Outputs, Output_Breakdown, Initial_Embodied_Energy_(MJ), Initial_Wastage_Embodied_Energy_(MJ), Recurrent_Embodied_Energy_(MJ), Recurrent_Wastage_Embodied_Energy_(MJ), Life_Cycle_Embodied_Energy_(MJ), Life_Cycle_Wastage_Embodied_Energy_(MJ), Initial_Embodied_Water_(L), Initial_Wastage_Embodied_Water_(L), Recurrent_Embodied_Water_(L), Recurrent_Wastage_Embodied_Water_(L), Life_Cycle_Embodied_Water_(L), Life_Cycle_Wastage_Embodied_Water_(L), Initial_Embodied_GHG_(kgCO₂e), Initial_Wastage_Embodied_GHG_(kgCO₂e), Recurrent_Embodied_GHG_(kgCO₂e), Recurrent_Wastage_Embodied_GHG_(kgCO₂e), Life_Cycle_Embodied_GHG_(kgCO₂e), Life_Cycle_Wastage_Embodied_GHG_(kgCO₂e), Geometry_by_Assembly)*

>### EPiC Help
> *Link to EPiC resources and information*
> 
> ![EPiC Help](epic/img/EPiC_Help_icon.png)
>
> > **Inputs:** *(Toggle_Switch_to_Open_EPiC_Database, Connect_Toggle_Switch_to_Suggest_Feature, Connect_Toggle_Switch_to_Report_Issue/Bug)*
