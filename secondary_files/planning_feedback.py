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
    exit("WARNING: Missing result database url. They should be of the form ""sqlite:///path/db_file.sqlite""")

def add_or_update_parameter_value(db_map : DatabaseMapping, class_name : str,parameter : str,alternative : str,elements : tuple,value : any) -> None:
    db_value, value_type = api.to_database(value)
    db_map.add_or_update_parameter_value(entity_class_name=class_name,entity_byname=elements,parameter_definition_name=parameter,alternative_name=alternative,value=db_value,type=value_type)

def existing_capacity_update():
    
    result_db = DatabaseMapping(url_results)
    alternatives = [i["name"] for i in result_db.get_alternative_items()]
    
    latest_alternatives = {}
    for alternative in alternatives:
        if "@" in alternative:
            name, timestamp = alternative.split('@')
            timestamp = pd.Timestamp(timestamp)
            
            if name not in latest_alternatives or timestamp > latest_alternatives[name]:
                latest_alternatives[name] = timestamp
            
    print(latest_alternatives)
    alternatives_management = {"y2030":"y2040","y2040":"y2050"}
    with DatabaseMapping(url_spineopt) as sopt_db:

        variables = ["units_invested_available", "connections_invested_available", "storages_invested_available"]
        parameters = ["initial_units_invested_available", "initial_connections_invested_available", "initial_storages_invested_available"]
        entities  = ["unit","connection","node"]
        cap = {}
        for index,variable in enumerate(variables):
            cap[entities[index]] = {}
            for param_map in result_db.get_parameter_value_items(parameter_definition_name = variable):
                if param_map["entity_byname"][1] not in cap[entities[index]]:
                    cap[entities[index]][param_map["entity_byname"][1]] = {}
                
                scenario_name, timestamp = param_map["alternative_name"].split("@")
                timestamp = pd.Timestamp(timestamp)
                if scenario_name in latest_alternatives:
                    if timestamp == latest_alternatives[scenario_name]:
                        cap[entities[index]][param_map["entity_byname"][1]][scenario_name] = param_map["parsed_value"].values[0]
        for entity_class in cap:
            for entity_name in cap[entity_class]:
                for past_alternative in alternatives_management:
                    array_values = [cap[entity_class][entity_name][i] for i in cap[entity_class][entity_name] if past_alternative in i]
                    value_cap = np.array(array_values).max() if len(array_values) > 0 else 0.0

                    if value_cap > 0.0:
                        add_or_update_parameter_value(sopt_db,entity_class,parameters[entities.index(entity_class)],alternatives_management[past_alternative],(entity_name,),value_cap)

        try:
            sopt_db.commit_session("Update Investment Costs")
        except DBAPIError as e:
            print("commit error")  

def main():

    print("Updating existing capacity")
    existing_capacity_update()

if __name__ == "__main__":
    main()