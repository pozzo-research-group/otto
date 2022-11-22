import glob
import os
import json
import opentrons.simulate as simulate


# All logic is based on api 2.2+ from opentrons, please read: https://docs.opentrons.com/OpentronsPythonAPIV2.pdf
# Keep in mind the following: All row based (while OT2 'default' is column based), all sequential (i.e sample 100 will be sample 4 in 96 well plate 2 of 2.) and many arugments are hardcoded to pull from a csv templete (hesistate to change template csv, can add but try not take away). 

#### Load in custom labware dictionry if necessary #####
def custom_labware_dict(labware_dir_path): 
    """Given the path of a folder of custom labware .json files will create dict
    of key = name and value = labware definition to be loaded using protocol.load_labware_from_definition 
    versus typical protocol.load_labware"""
    labware_dict = {}
    for file in glob.glob(labware_dir_path + '/**/*.json', recursive=True):
        with open(file) as labware_file:
            labware_name = os.path.splitext(file)[0] # removes the .json extnesion
            labware_def = json.load(labware_file)
            labware_dict[labware_name] = labware_def
    return labware_dict 


##### These next functions will help you create a labware dictionary which will contain all information tied to protocol object to run a protocol. The four main things are: source/destination labware, pipettes and tipracks #####


def object_list_to_well_list(labware_objects):
    """Labware list loaded is made into concatenated list of the all labwares
    in order of the object in the initally loaded list."""
    
    all_wells_row_order = [] 
    for labware in labware_objects:
        rows = [well for row in labware.rows() for well in row]
        all_wells_row_order = all_wells_row_order + rows
    
    return all_wells_row_order

def loading_labware(protocol, experiment_dict):
    """ Loads the required labware given information from a loaded csv dictionary. The labware, which
    include pipettes, plates and tipracks are tied to the protocol object argurment. Returned is a dcitonary 
    containing the important object instances to be used in subsequent functions alongside the original protocol instance."""
    
    protocol.home() 
      
    # Loading Destination Labware
    dest_labware_names = experiment_dict['OT2 Destination Labwares']
    dest_labware_slots = experiment_dict['OT2 Destination Labware Slots']
    if 'OT2 Destination Labwares Offset' in experiment_dict.keys():
        dest_labware_offset = experiment_dict['OT2 Destination Labwares Offset']
        dest_labware = object_to_object_list(
        protocol, dest_labware_names, dest_labware_slots,
        offset = dest_labware_offset)
    else:
        dest_labware = object_to_object_list(
            protocol, dest_labware_names, dest_labware_slots)
    dest_wells = object_list_to_well_list(dest_labware)
    
    # Loading Trasnfer Labware (Labware that the destination samples are transfrred to)
    if 'OT2 Transfer Labwares' in experiment_dict.keys():                                    
        transfer_labware_names = experiment_dict['OT2 Transfer Labwares']
        transfer_labware_slots = experiment_dict['OT2 Transfer Labware Slots']
        if 'OT2 Transfer Labwares Offset' in experiment_dict.keys():
            transfer_labware_offset = experiment_dict['OT2 Transfer Labwares Offset']
            transfer_labware_objects = object_to_object_list(
            protocol, transfer_labware_names, transfer_labware_slots,
        offset = transfer_labware_offset)
            transfer_wells = object_list_to_well_list(transfer_labware_objects)
        else:
            transfer_labware = object_to_object_list(
                protocol, transfer_labware_names, transfer_labware_slots)
            transfer_labware_objects = object_to_object_list(protocol, transfer_labware_names, transfer_labware_slots)
            transfer_wells = object_list_to_well_list(transfer_labware_objects)
        
    if 'OT2 Resevoir Labwares' in experiment_dict.keys():
        resevoir_labware_names = experiment_dict['OT2 Resevoir Labwares']
        resevoir_labware_slots = experiment_dict['OT2 Resevoir Labware Slots']
        resevoir_labware_objects = object_to_object_list(protocol, resevoir_labware_names, resevoir_labware_slots)
        resevoir_wells = object_list_to_well_list(resevoir_labware_objects)
     
    stock_labware_names = experiment_dict['OT2 Stock Labwares']
    stock_labware_slots = experiment_dict['OT2 Stock Labware Slots']
    stock_labware_objects = object_to_object_list(protocol, stock_labware_names, stock_labware_slots)
    stock_wells = object_list_to_well_list(stock_labware_objects)
    
    
    # Loading pipettes and tipracks
    right_tiprack_names = experiment_dict['OT2 Right Tipracks']
    right_tiprack_slots = experiment_dict['OT2 Right Tiprack Slots']
    if 'OT2 Right Tiprack Offset' in experiment_dict.keys():
        right_tiprack_offset = experiment_dict['OT2 Right Tiprack Offset']
        right_tipracks = object_to_object_list(
        protocol, right_tiprack_names, right_tiprack_slots,
        offset= right_tiprack_offset)
    else:
        right_tipracks = object_to_object_list(
            protocol, right_tiprack_names, right_tiprack_slots)
    right_tiprack_wells = object_list_to_well_list(right_tipracks)
    right_pipette = protocol.load_instrument(experiment_dict['OT2 Right Pipette'], 'right', tip_racks = right_tipracks)
    right_pipette.flow_rate.aspirate = experiment_dict['OT2 Right Pipette Aspiration Rate (uL/sec)']
    right_pipette.flow_rate.dispense = experiment_dict['OT2 Right Pipette Dispense Rate (uL/sec)']    
    right_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)']

    left_tiprack_names = experiment_dict['OT2 Left Tipracks']
    left_tiprack_slots = experiment_dict['OT2 Left Tiprack Slots']
    if 'OT2 Left Tiprack Offset' in experiment_dict.keys():
        left_tiprack_offset =\
            experiment_dict['OT2 Left Tiprack Offset']
        left_tipracks = object_to_object_list(
            protocol, left_tiprack_names, left_tiprack_slots,
            offset= left_tiprack_offset)
    else:
        left_tipracks = object_to_object_list(
            protocol, left_tiprack_names, left_tiprack_slots)
    left_tiprack_wells = object_list_to_well_list(left_tipracks)
    left_pipette = protocol.load_instrument(experiment_dict['OT2 Left Pipette'], 'left', tip_racks = left_tipracks) # is there a way to ensure the correct tiprack is laoded? maybe simple simualtion test a function
    left_pipette.flow_rate.aspirate = experiment_dict['OT2 Left Pipette Aspiration Rate (uL/sec)']
    left_pipette.flow_rate.dispense = experiment_dict['OT2 Left Pipette Dispense Rate (uL/sec)']   
    left_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)']

    loaded_labware_dict = {'Destination Wells': dest_wells, 
                       'Stock Wells': stock_wells,
                       'Left Pipette': left_pipette,
                       'Left Tiprack Wells': left_tiprack_wells,
                       'Right Pipette': right_pipette,
                       'Right Tiprack Wells': right_tiprack_wells
                       }
    
    if 'OT2 Transfer Labwares' in experiment_dict.keys():
        loaded_labware_dict['Transfer Wells'] = transfer_wells
    
    if 'OT2 Resevoir Labwares' in experiment_dict.keys():
        loaded_labware_dict['Resevoir Wells'] = resevoir_wells
    
    if "OT2 Left Tiprack Offset" in experiment_dict.keys():
        loaded_labware_dict['Left_tiprack_offset'] = experiment_dict['OT2 Left Tiprack Offset']
    
    if "OT2 Right Tiprack Offset" in experiment_dict.keys():
        loaded_labware_dict['Right_tiprack_offset'] = experiment_dict['OT2 Right Tiprack Offset']
    
    loaded_labware_dict = determine_pipette_resolution(loaded_labware_dict)
    
    return loaded_labware_dict

def determine_pipette_resolution(loaded_labware_dict):
    """Given the opentrons only uses two pipettes one as always designated as a small or large pipette to ensure a wide range 
    of volumes is covered. We designate one as small and one as large to ensure we are using the highest precision possible"""
    
    left_pipette = loaded_labware_dict['Left Pipette']
    left_tiprack = loaded_labware_dict['Left Tiprack Wells']
    right_pipette= loaded_labware_dict['Right Pipette']
    right_tiprack = loaded_labware_dict['Right Tiprack Wells']


    if left_pipette.max_volume < right_pipette.max_volume:
        small_pipette = left_pipette 
        small_tiprack = left_tiprack
        large_pipette = right_pipette
        large_tiprack = right_tiprack

    if left_pipette.max_volume > right_pipette.max_volume:
        small_pipette = right_pipette
        small_tiprack = right_tiprack
        large_pipette = left_pipette
        large_tiprack = left_tiprack

    loaded_labware_dict['Small Pipette'] = small_pipette
    loaded_labware_dict['Large Pipette'] = large_pipette
    loaded_labware_dict['Small Tiprack'] = small_tiprack
    loaded_labware_dict['Large Tiprack'] = large_tiprack

    return loaded_labware_dict

def object_to_object_list(protocol, stock_object_names, stock_object_slots,
                          offset=None):
    """
    Loads the labware specfied in the list arguments with the respective slots.
    This labware is tied to the loaded protocol (global).
    Parameters
    -----------
    protocol: opentrons.protocol_api.protocol_context.ProtocolContext
        Protocol object from the robot
    stock_object_names: List
        List containing string representing the labware to use for the protocol
    stock_object_slots: List
        List containing string representing the OT-2 deck slots each labware
        will be placed on during the experiment.
    Returns
    --------
    labware_objects : List
        List containing all the labware objects
            [opentrons.protocol_api.labware.Labware]
    """

    labware_objects = []  # labware objects
    if offset:
        for labware_name, labware_slot, offset_coord in zip(
                                              stock_object_names,
                                              stock_object_slots,
                                              offset):
            labware_object = protocol.load_labware(labware_name,
                                                   labware_slot)
            labware_object.set_offset(x=offset_coord[0],
                                      y=offset_coord[1],
                                      z=offset_coord[2])
            # this is where the well information is being pulled from
            # a OT2/added native library
            labware_objects.append(labware_object)

    else:
        for labware_name, labware_slot in zip(
                                              stock_object_names,
                                              stock_object_slots):
            labware_object = protocol.load_labware(labware_name,
                                                   labware_slot)
            # this is where the well information is being pulled from
            # a OT2/added native library
            labware_objects.append(labware_object)
    return labware_objects



