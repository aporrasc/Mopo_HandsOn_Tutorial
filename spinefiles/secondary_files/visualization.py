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
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

url_results = sys.argv[1]
result_db = DatabaseMapping(url_results)

def from_DB_to_df():

    alternatives = [i["name"] for i in result_db.get_alternative_items()]
    latest_alternatives = {}
    for alternative in alternatives:
        if "@" in alternative:
            name, timestamp = alternative.split('@')
            timestamp = pd.Timestamp(timestamp)
        
            if name not in latest_alternatives or timestamp > latest_alternatives[name]:
                latest_alternatives[name] = timestamp

    dfs = {"from_node":{name.split("__")[0]:{} for name in latest_alternatives},"to_node":{name.split("__")[0]:{} for name in latest_alternatives}}
    demand = {name.split("__")[0]:{} for name in latest_alternatives}
    ats = {name.split("__")[0]:{} for name in latest_alternatives}
    co2 = {name.split("__")[0]:{} for name in latest_alternatives}
    
    for param_map in result_db.get_parameter_value_items(parameter_definition_name = "unit_flow"):
        
        scenario_name, timestamp = param_map["alternative_name"].split("@")
        timestamp = pd.Timestamp(timestamp)
        if scenario_name in latest_alternatives:
            if timestamp == latest_alternatives[scenario_name]:
                alte_name = scenario_name.split("__")[0]
                if "from_node" in param_map["entity_byname"]:
                    unit_name = param_map["entity_byname"][1]
                    node_name = param_map["entity_byname"][2]

                    if unit_name not in dfs["from_node"][alte_name]:
                        dfs["from_node"][alte_name][unit_name] = {}

                    if node_name == "atmosphere":
                        if unit_name not in ats[alte_name]:
                            ats[alte_name][unit_name] = {}
                        ats[alte_name][unit_name]["from_node"] = float(param_map["parsed_value"].values[0])
                    elif node_name == "CO2":
                        if unit_name not in co2[alte_name]:
                            co2[alte_name][unit_name] = {}
                        co2[alte_name][unit_name]["from_node"] = float(param_map["parsed_value"].values[0])
                    else:
                        dfs["from_node"][alte_name][unit_name][node_name.split("_")[0]] = float(param_map["parsed_value"].values[0])
                         
                elif "to_node" in param_map["entity_byname"]:
                    unit_name = param_map["entity_byname"][1]
                    node_name = param_map["entity_byname"][2]

                    if node_name == "atmosphere":
                        if unit_name not in ats[alte_name]:
                            ats[alte_name][unit_name] = {}
                        ats[alte_name][unit_name]["to_node"] = float(param_map["parsed_value"].values[0])
                    elif node_name == "CO2":
                        if unit_name not in co2[alte_name]:
                            co2[alte_name][unit_name] = {}
                        co2[alte_name][unit_name]["to_node"] = float(param_map["parsed_value"].values[0])
                        if "DAC" in unit_name:
                            dfs["to_node"][alte_name][unit_name] = "DAC"                          
                    elif unit_name not in dfs["to_node"][alte_name]:
                        dfs["to_node"][alte_name][unit_name] = node_name.split("_")[0]
                        demand[alte_name][unit_name] = {"demand":float(param_map["parsed_value"].values[0]),"product":node_name.split("_")[0]}
    return dfs,ats,co2,demand

def df_to_bar(df_com,df_atm,df_co2):
    
    dfs = []
    for scenario, df in df_com.items():
        df = df.reset_index()
        df['Scenario'] = scenario
        dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True)
    melted_df = combined_df.melt(id_vars=['index', 'Scenario'], var_name='commodity', value_name='TWh')
    melted_df.set_index(['index', 'Scenario'],inplace=True)
    pos = 0
    for index in melted_df.reset_index()["index"].unique():
        for scenario in melted_df.reset_index()["Scenario"].unique():
            melted_df.loc[(index,scenario),"pos"] = pos
            melted_df.loc[(index,scenario),"label"] = f"{scenario} - {index}"
            pos += 1
        pos += 1
    melted_df = melted_df.reset_index()
    fig = px.bar(melted_df, x='pos', y='TWh', color='commodity', barmode='stack')
    fig.update_layout(title='Commodity used per product',xaxis_title = "Product - Scenario",xaxis=dict(tickvals=melted_df["pos"].to_list(),ticktext=melted_df["label"].to_list(),tickangle=-45))
    fig.write_html("results/Commodity_usage.html")

    dfs = []
    for scenario, df in df_atm.items():
        df = df.reset_index()
        df['Scenario'] = scenario
        dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df["emissions"] = combined_df["to_node"].values - combined_df["from_node"].values
    combined_df = combined_df[combined_df["emissions"]!= 0.0][["index","Scenario","emissions"]]
    melted_df = combined_df.melt(id_vars=['index', 'Scenario'], var_name='emissions', value_name='MtCO2')
    melted_df.set_index(['index', 'Scenario'],inplace=True)
    pos = 0
    for index in melted_df.reset_index()["index"].unique():
        for scenario in melted_df.reset_index()["Scenario"].unique():
            melted_df.loc[(index,scenario),"pos"] = pos
            melted_df.loc[(index,scenario),"label"] = f"{scenario} - {index}"
            pos += 1
        pos += 1
    melted_df = melted_df.reset_index()
    fig = px.bar(melted_df, x='pos', y='MtCO2', color='index', barmode='stack')
    fig.update_layout(title='Emissions per product',xaxis_title = "Product - Scenario",xaxis=dict(tickvals=melted_df["pos"].to_list(),ticktext=melted_df["label"].to_list(),tickangle=-45))
    fig.write_html("results/Emissions.html")
    
    dfs = []
    for scenario, df in df_co2.items():
        df = df.reset_index()
        df['Scenario'] = scenario
        dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df["consumption"] = combined_df["from_node"].values - combined_df["to_node"].values
    combined_df = combined_df[combined_df["consumption"]!= 0.0][["index","Scenario","consumption"]]
    melted_df = combined_df.melt(id_vars=['index', 'Scenario'], var_name='consumption', value_name='MtCO2')
    melted_df.set_index(['index', 'Scenario'],inplace=True)
    pos = 0
    for index in melted_df.reset_index()["index"].unique():
        for scenario in melted_df.reset_index()["Scenario"].unique():
            melted_df.loc[(index,scenario),"pos"] = pos
            melted_df.loc[(index,scenario),"label"] = f"{scenario} - {index}"
            pos += 1
        pos += 1
    melted_df = melted_df.reset_index()
    fig = px.bar(melted_df, x='pos', y='MtCO2', color='index', barmode='stack')
    fig.update_layout(title='CO2 consumption per product',xaxis_title = "Product - Scenario",xaxis=dict(tickvals=melted_df["pos"].to_list(),ticktext=melted_df["label"].to_list(),tickangle=-45))
    fig.write_html("results/CO2_consumption.html")


def main():
    dfs,ats,co2,demand = from_DB_to_df()
    df_com = {}
    df_atm = {}
    df_co2 = {}
    df_dem = {}
    for alte_name in dfs["from_node"]:
        df_com[alte_name] = pd.DataFrame.from_dict(dfs["from_node"][alte_name],orient="index")
        df_atm[alte_name] = pd.DataFrame.from_dict(ats[alte_name],orient="index")
        df_co2[alte_name] = pd.DataFrame.from_dict(co2[alte_name],orient="index")
        df_dem[alte_name] = pd.DataFrame.from_dict(demand[alte_name],orient="index")

        df_com[alte_name].fillna(0,inplace=True)
        df_atm[alte_name].fillna(0,inplace=True)
        df_co2[alte_name].fillna(0,inplace=True)
        df_dem[alte_name].fillna(0,inplace=True)

        com_conversion = pd.concat([df_com[alte_name],df_dem[alte_name]],axis=1,ignore_index=False)        
        com_conversion[com_conversion.select_dtypes(include=['number']).columns] *= 8760/1e3
        com_conversion.to_csv(f"results/commodities_{alte_name}.csv")

        units_dict = {}
        for unit_name in com_conversion.index:
            if com_conversion.at[unit_name,"demand"] > 0.0:
                units_dict[unit_name.split("_")[0]] = {"status":True}
            else:
                units_dict[unit_name.split("_")[0]] = {"status":False}

        df_com[alte_name].index = df_com[alte_name].index.map(dfs["to_node"][alte_name])
        df_com[alte_name] = df_com[alte_name].groupby(df_com[alte_name].index).sum()*8760/1e6
        df_atm[alte_name].index = [dfs["to_node"][alte_name][unit_name] for unit_name in df_atm[alte_name].index]
        df_atm[alte_name] = df_atm[alte_name].groupby(df_atm[alte_name].index).sum()*8760/1e6
        df_co2[alte_name].index = [dfs["to_node"][alte_name][unit_name] for unit_name in df_co2[alte_name].index]
        df_co2[alte_name] = df_co2[alte_name].groupby(df_co2[alte_name].index).sum()*8760/1e6

    df_to_bar(df_com,df_atm,df_co2)

if __name__ == "__main__":
    main()