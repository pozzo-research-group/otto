import pandas as pd
import numpy as np
from OT2_code import CreateSamples, OT2Commands
from opentrons import simulate, execute, protocol_api
import random
import os
import math
import time

class experiment():
    def __init__(self):
        return 
        
    def simulate(self):
        path = r"Samples_and_Protocol/Protocol/protocol.csv"
        labware_dir_path = r"OT2_code/Custom_Labware"
        self.plan = CreateSamples.get_experiment_plan(path)
        self.custom_labware_dict = OT2Commands.custom_labware_dict(labware_dir_path)
        protocol = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.protocol2 = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.loaded_dict = OT2Commands.loading_labware(protocol, self.plan)
        return protocol
    
    def execute(self):
        path = r"Samples_and_Protocol/Protocol/protocol.csv"
        labware_dir_path = r"OT2_code/Custom_Labware"
        self.plan = CreateSamples.get_experiment_plan(path)
        self.custom_labware_dict = OT2Commands.custom_labware_dict(labware_dir_path)
        protocol = execute.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.protocol2 = execute.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.loaded_dict = OT2Commands.loading_labware(protocol, self.plan)
        return protocol 
    
    def calculate_exp_duration(self, direction_array, **kwargs):
        self.action_time = kwargs['action_time']
        times = []
        for i in range(direction_array.shape[0]):
            actions = direction_array[i, -1]
            if actions > -1:
                times.append(1)
            else:
                times.append(-actions)
        total_time = np.sum(np.array(times))*self.action_time
        hours = math.floor(total_time/3600)
        minutes = int(np.round((total_time%3600)/3600*60))
        print('Experiment will take a total time of:')
        print(hours, 'hours')
        print(minutes, 'minutes')
        

    def stock_solution_ranges(self, direction_array, vial_volume):
        ind = np.argsort(direction_array[:,-1])
        sorted_array = direction_array[ind]
        stock_sum_list = []
        stock_identity = []
        for stock in range(int(sorted_array[-1,-1]+1)):
            row = np.where(sorted_array[:, -1] == stock)
            stock_sum = np.sum(sorted_array[row, :][0], axis=0)[0]
            stock_sum_list.append(stock_sum) # Create a list of the amount of volume needed for each stock 
        count = 0 
        # Display where each stock should be located depending on the volumes that
        # need to be pipetted 
        for stock in range(len(stock_sum_list)): #Assign vial positions to each stock
            n_vials = math.ceil(stock_sum_list[stock]/vial_volume)
            for vial in range(n_vials):
                print('Stock', stock, 'on ', self.loaded_dict['Stock Wells'][vial + count])
                if stock == 0 and vial == 0:
                    stock_positions = self.loaded_dict['Stock Wells'][vial + count]
                else:
                    stock_positions = np.vstack((stock_positions,self.loaded_dict['Stock Wells'][vial + count]))
                stock_identity.append(stock)
            count = vial + count + 1
        # Find the starting_stock_positions which is the location where each unique
        # stock is located 
        starting_stock_position = [0]
        for i in range(1, len(stock_identity)):
            if stock_identity[i] != stock_identity[i-1]:
                starting_stock_position.append(i)   
        # Substitute the values for the stock locations with the new starting positions
        for row in range(direction_array.shape[0]):    
            for i in range(len(starting_stock_position)):
                if direction_array[row, -1] == i:
                    direction_array[row, -1] = starting_stock_position[i]
                    break
                else:
                    pass
        volume_pipetted = [0]*(len(starting_stock_position))
        starting_stock_position = np.array(starting_stock_position)
        for row in range(direction_array.shape[0]):
            stock_location = direction_array[row, -1]
            stock_volume = direction_array[row, 0]
            if stock_location < 0:
                pass
            else:
                # add stock volume pipetted to cumulative stock volume pipetted
                for stock in range(len(volume_pipetted)):
                    if starting_stock_position[stock] == stock_location:
                        volume_pipetted[stock] = volume_pipetted[stock] + stock_volume
                        break
                # check if volume pipetted is over the vial volume 
                for vial in range(len(volume_pipetted)):
                    if volume_pipetted[vial] > vial_volume: #if the total stock pipetted volume is over the vial volume 
                        #Change the stock positions to 1+ the original value starting from when the max volume was pipetted in direction array
                        volume_pipetted[vial] = 0
                        starting_stock_position[vial] = starting_stock_position[vial] + 1
                        for sample in range(row, direction_array.shape[0]):    
                            if direction_array[sample, -1] == starting_stock_position[vial]-1:
                                direction_array[sample, -1] = starting_stock_position[vial]
                            else:
                                pass

        return direction_array


    def pipette_action(self, pipette, volume, sample_well, stock_solution):
        if stock_solution == 64444:
            if 'Resevoir Wells' in self.loaded_dict.keys():
                pipette.mix(3, 150, self.loaded_dict['Destination Wells'][sample_well])
                pipette.mix(3, 250, self.loaded_dict['Resevoir Wells'][-1])
                pipette.blow_out()
                pipette.mix(1, 15, self.loaded_dict['Resevoir Wells'][-4])
                pipette.blow_out()
        else:
            pipette.aspirate(volume, self.loaded_dict['Stock Wells'][stock_solution])
            if volume < 16:
                pipette.air_gap(4)
            elif volume <= 20:
                pass
            else:
                pipette.air_gap(20)
            pipette.dispense(volume, self.loaded_dict['Destination Wells'][sample_well])
            pipette.blow_out()
            ##Wash the tip to prevent liquid from entering the tip rack
            #pipette.mix(1, 15, self.loaded_dict['Resevoir Wells'][-2])
            #pipette.mix(1, 15, self.loaded_dict['Resevoir Wells'][-3])
            
            pipette.blow_out()
            #pipette.transfer(volume, self.loaded_dict['Stock Wells'][stock_solution], self.loaded_dict['Destination Wells'][sample_well])


    def perform_directions(self, protocol, direction_array, **kwargs):
        if 'start_location' in kwargs.keys():
            start_location = kwargs['start_location']
        action_time = self.action_time
        small_pipette = self.loaded_dict['Small Pipette']
        small_tiprack = self.loaded_dict['Small Tiprack']
        large_pipette = self.loaded_dict['Large Pipette']
        large_tiprack = self.loaded_dict['Large Tiprack'] 
        for action in range(direction_array.shape[0]):
            volume = int(direction_array[action, 0])
            sample_well = int(direction_array[action, 1] + start_location)
            stock_solution = int(direction_array[action, 2])
            start_time = time.time()
            if volume > small_pipette.max_volume: #Use large pipette
                large_pipette.pick_up_tip(self.loaded_dict['Large Tiprack'][stock_solution])
                self.pipette_action(large_pipette, volume, sample_well, stock_solution)
                large_pipette.drop_tip(self.loaded_dict['Large Tiprack'][stock_solution].bottom(12))
                end_time = time.time()
                actual_time_taken = end_time - start_time
                delay_time = action_time - actual_time_taken
                #assert delay_time > 0, 'Increase the action_time'
                if delay_time > 0:
                    protocol.delay(seconds= delay_time)
                else:
                    print('Increase the action time. OT2 takes longer than action time to perform action')
                

            elif volume > 0: #Use small pipette 
                small_pipette.pick_up_tip(self.loaded_dict['Small Tiprack'][stock_solution])
                self.pipette_action(small_pipette, volume, sample_well, stock_solution)
                small_pipette.drop_tip(self.loaded_dict['Small Tiprack'][stock_solution].bottom(10))
                end_time = time.time()
                actual_time_taken = end_time - start_time
                delay_time = action_time - actual_time_taken
                #assert delay_time > 0, 'Increase the action_time'
                if delay_time > 0:
                    protocol.delay(seconds= delay_time)
                else:
                    print('Increase the action time. OT2 takes longer than action time to perform action')
            else: #Do nothing
                protocol.delay(seconds=-action_time*direction_array[action,-1])
                end_time = time.time()
        protocol.home() 
        for line in protocol.commands(): 
            print(line)
        
        
        
        
        
    