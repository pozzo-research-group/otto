import numpy as np
import pandas as pd
import os
import csv
import ast
import datetime
from pytz import timezone

mass_dictionary = {'g':1} # should build a dictionary of units people can add to such that not restricted to hardcoded ones


##### Set up the experiment plan dictionary to be referenced for useful information throughout a design of experiments. This is not necessary if loading in volumes directly#####

def get_experiment_plan(filepath):
    """
    Parse a .csv file to create a dictionary of instructions.
    """
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        plan_dict = {}
        for i, row in enumerate(reader):
            assert len(row) == 2
            plan_dict[row[0]] = ast.literal_eval(row[1])
    
    #chem_data = pd.read_csv(chemical_database_path)
    #chem_data_names = chem_data['Component Abbreviation']
    #chem_data.index = chem_data_names
    #plan_dict['Chemical Database'] = chem_data.T.to_dict()
    
    return plan_dict
