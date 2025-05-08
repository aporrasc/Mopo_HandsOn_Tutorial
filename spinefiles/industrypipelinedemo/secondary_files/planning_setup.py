import spinedb_api as api
from spinedb_api import DatabaseMapping
from spinedb_api.dataframes import to_dataframe
from sqlalchemy.exc import DBAPIError
import datetime
import pandas as pd
import sys
import numpy as np
import json
import yaml 
import time as time_lib


if len(sys.argv) > 1:
    url_spineopt = sys.argv[1]
else:
    exit("Please provide spineopt database url as argument. They should be of the form ""sqlite:///path/db_file.sqlite""")
if len(sys.argv) > 2:
    url_results = sys.argv[2]
else:
    print("WARNING: Missing result database url. They should be of the form ""sqlite:///path/db_file.sqlite""")

def add_or_update_parameter_value(db_map : DatabaseMapping, class_name : str,parameter : str,alternative : str,elements : tuple,value : any) -> None:
    db_value, value_type = api.to_database(value)
    db_map.add_or_update_parameter_value(entity_class_name=class_name,entity_byname=elements,parameter_definition_name=parameter,alternative_name=alternative,value=db_value,type=value_type)
    
def add_entity(db_map : DatabaseMapping, class_name : str, name : tuple, ent_description = None) -> None:
    _, error = db_map.add_entity_item(entity_byname=name, entity_class_name=class_name, description = ent_description)
    if error is not None:
        raise RuntimeError(error)

def add_parameter_value(db_map : DatabaseMapping,class_name : str,parameter : str,alternative : str,elements : tuple,value : any) -> None:
    db_value, value_type = api.to_database(value)
    _, error = db_map.add_parameter_value_item(entity_class_name=class_name,entity_byname=elements,parameter_definition_name=parameter,alternative_name=alternative,value=db_value,type=value_type)
    if error:
        raise RuntimeError(error)

def add_entity_group(db_map : DatabaseMapping, class_name : str, group : str, member : str, ent_description = None) -> None:
    _, error = db_map.add_entity_group_item(group_name = group, member_name = member, entity_class_name=class_name)
    if error is not None:
        raise RuntimeError(error)
    
def add_scenario(db_map : DatabaseMapping,name_scenario : str) -> None:
    _, error = db_map.add_scenario_item(name=name_scenario)
    if error is not None:
        raise RuntimeError(error)

def add_scenario_alternative(db_map : DatabaseMapping,name_scenario : str, name_alternative : str, rank_int = None) -> None:
    _, error = db_map.add_scenario_alternative_item(scenario_name = name_scenario, alternative_name = name_alternative, rank = rank_int)
    if error is not None:
        raise RuntimeError(error)

def investment_cost_update(sopt_db):
    
    entities = ["unit","connection","node"]
    icost = ["unit_investment_cost","connection_investment_cost","storage_investment_cost"]
    fcost = ["fom_cost","","storage_fom_cost"]
    ilife = ["unit_investment_econ_lifetime","connection_investment_econ_lifetime","storage_investment_econ_lifetime"]
    tlife = ["unit_investment_tech_lifetime","connection_investment_tech_lifetime","storage_investment_tech_lifetime"]
    irate = ["unit_discount_rate_technology_specific","connection_discount_rate_technology_specific","storage_discount_rate_technology_specific"]
    
    for index, entity_class_name in enumerate(entities): 

        for parameter_map in sopt_db.get_parameter_value_items(entity_class_name = entities[index], parameter_definition_name = icost[index]):
            
            lifetime_dict = sopt_db.get_parameter_value_item(entity_class_name = entities[index], parameter_definition_name = ilife[index], alternative_name = parameter_map["alternative_name"], entity_byname = parameter_map["entity_byname"])
            if not lifetime_dict:
                exit("Annuities are implemented using economic lifetime. Economic lifetime not found.")
            else:
                lifetime = int(json.loads(lifetime_dict["value"])["data"][:-1])
                sopt_db.remove_item("parameter_value",lifetime_dict["id"])
                techlife_dict = sopt_db.get_parameter_value_item(entity_class_name = entities[index], parameter_definition_name = tlife[index], alternative_name = parameter_map["alternative_name"], entity_byname = parameter_map["entity_byname"])
                sopt_db.remove_item("parameter_value",techlife_dict["id"])

            rate_dict = sopt_db.get_parameter_value_item(entity_class_name = entities[index], parameter_definition_name = irate[index], alternative_name = parameter_map["alternative_name"], entity_byname = parameter_map["entity_byname"])
            if not rate_dict:
                rate_list = sopt_db.get_parameter_value_items(parameter_definition_name = "discount_rate")
                if not rate_list:
                    print("Model discount rate not found. Using 0.05 as default")
                    rate = 0.05
                else:
                    rate = rate_list[0]["parsed_value"]
            else:
                rate = rate_dict["parsed_value"]
            annuity_factor = rate*(1+rate)**(lifetime)/((1+rate)**(lifetime)-1)

            # fom cost
            fom_dict = sopt_db.get_parameter_value_item(entity_class_name = entities[index], parameter_definition_name = fcost[index], alternative_name = parameter_map["alternative_name"], entity_byname = parameter_map["entity_byname"])
            if not fom_dict:
                fom_cost_condition = False
                print("FOM cost not found for ", parameter_map["entity_name"])
            else:
                fom_cost_condition = True
                fom_cost = fom_dict["parsed_value"]
                sopt_db.remove_item("parameter_value",fom_dict["id"])
            
            if parameter_map["type"] == "float":
                new_value = parameter_map["parsed_value"] * annuity_factor + (fom_cost*8760 if fom_cost_condition else 0.0)
            else:
                new_value = {"type":parameter_map["type"], "data": dict(zip([pd.Timestamp(i).isoformat() for i in parameter_map["parsed_value"].indexes.tolist()],parameter_map["parsed_value"].values * annuity_factor + (fom_cost.values*8760 if fom_cost_condition else 0.0)))}
            add_or_update_parameter_value(sopt_db, parameter_map["entity_class_name"], parameter_map["parameter_definition_name"], parameter_map["alternative_name"], parameter_map["entity_byname"], new_value)

    for index, econ_life_param in enumerate(ilife):
        for lifetime_dict in sopt_db.get_parameter_value_items(entity_class_name = entities[index], parameter_definition_name = econ_life_param):
            sopt_db.remove_item("parameter_value",lifetime_dict["id"])
            techlife_dict = sopt_db.get_parameter_value_item(entity_class_name = entities[index], parameter_definition_name = tlife[index], alternative_name = lifetime_dict["alternative_name"], entity_byname = lifetime_dict["entity_byname"])
            sopt_db.remove_item("parameter_value",techlife_dict["id"])

def scenario_development(sopt_db):

    add_parameter_value(sopt_db,"temporal_block","weight","Base",("operations",),8760.0)

    for py in ["y2030","y2040","y2050"]:

        add_or_update_parameter_value(sopt_db,"model","model_end",py,("capacity_planning",),{"type":"date_time","data":(py[1:] if py!="y2040" else "2041")+"-01-01T01:00:00"})

        add_scenario(sopt_db,f"{py}")
        add_scenario_alternative(sopt_db,f"{py}","Base",3)
        add_scenario_alternative(sopt_db,f"{py}","medium_bio",2)
        add_scenario_alternative(sopt_db,f"{py}",f"{py}",1)

    for entity_main, parameter_name in {"atmosphere":"fix_storages_invested_available","CO2":"node_state_cap","biomass-stock_ES":"initial_node_state"}.items():
        for param_map in sopt_db.get_parameter_value_items(parameter_definition_name = parameter_name, entity_class_name = "node", entity_byname = (entity_main,)):
            if param_map["type"] == "time_series":
                indexes_ = [pd.Timestamp(i).isoformat() for i in param_map["parsed_value"].indexes]
                values_  = param_map["parsed_value"].values/30/8760
                value_param = {"type":"time_series","data":dict(zip(indexes_,values_))}
            elif param_map["type"] == "float":
                value_param = param_map["parsed_value"]/8760 if entity_main != "CO2" else param_map["parsed_value"]/30/8760
            add_or_update_parameter_value(sopt_db,"node",parameter_name,param_map["alternative_name"],param_map["entity_byname"],value_param)    

def main():

    with DatabaseMapping(url_spineopt) as sopt_db:
        print("Updating invesment costs and removing FOM costs")
        investment_cost_update(sopt_db)
        print("adding scenarios to be analyzed")
        scenario_development(sopt_db)

        sopt_db.commit_session("Added scenario")

if __name__ == "__main__":
    main()