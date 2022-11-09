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
        
    def simulate(self, path):
        labware_dir_path = r"OT2_code/Custom_Labware"
        self.plan = CreateSamples.get_experiment_plan(path)
        self.custom_labware_dict = OT2Commands.custom_labware_dict(labware_dir_path)
        protocol = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.protocol2 = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.loaded_dict = OT2Commands.loading_labware(protocol, self.plan)
        return protocol
    
    def execute(self, path):
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
            self.dispense_time = time.time()
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
            
            data = np.array([volume, sample_well, stock_solution, self.dispense_time]).reshape(1,-1)
            if action == 0:
                self.exp_data = data
            else:
                self.exp_data = np.vstack((self.exp_data, data))
        protocol.home() 
        for line in protocol.commands(): 
            print(line)
        
        
    def test(self, exp_data, v_array, t_array, o_array):
        # Remove Negative Values
        exp_data = exp_data[(exp_data >= 0).all(1)]
        # Sort Values first based on Sample number and then by time that they were added 
        exp_data_new = exp_data[0,:].reshape(1,-1)
        for sample in range(int(np.max(exp_data[:,1])+1)): #Iterate over the number of samples
            for row in range(1,exp_data.shape[0]): #Iterate over the whole array
                if exp_data[row, 1] == sample:
                    exp_data_new = np.vstack((exp_data_new, exp_data[row,:].reshape(1,-1)))
        exp_data = exp_data_new.copy()
        # Calculate Relative time (delay times)
        delay_times = [0]
        for row in range(1, exp_data.shape[0]):
            delay_times.append(exp_data[row-1, -1] - exp_data[row, -1])
        delay_times = np.array(delay_times)/60
        for i in range(len(delay_times)):
            if delay_times[i] > 0:
                delay_times[i] = 0
        delay_times = np.abs(delay_times)
        # Create exp_data array with relative time delays as last column
        exp_data = np.hstack((exp_data, delay_times.reshape(-1,1)))
        n_stocks = np.max(exp_data[:,2])
        n_samples = np.max(exp_data[:,1])
        assert int((n_stocks + 1)*(n_samples + 1)) == exp_data.shape[0], 'Test will not work since some volumes are 0. New test need to be created for this case'

        # Calculate the average delay time error of the actual delay time and the specified time
        zeros_loc = np.where(delay_times == 0)
        delay_times = np.delete(delay_times, zeros_loc)
        error = delay_times - (t_array*self.action_time/60).flatten() - 1 #t_array times delay time divided by 60
        average_error = np.mean(np.abs(error))*60 #seconds
        print('Time: The average time delay error is (+/-) %.3g seconds' %average_error)

        # Extract the order that the stocks were added to the sample
        n_stocks = np.max(exp_data[:,2]+1)
        n_samples = np.max(exp_data[:,1]+1)
        for sample in range(int(n_samples)):
            order_of_sample = exp_data[np.where(exp_data[:,1] == sample), 2]
            if sample == 0:
                orders = order_of_sample.reshape(1,-1)
            else:
                orders = np.vstack((orders, order_of_sample.reshape(1,-1)))
        # Check if order is equal to specified order
        if np.sum(np.abs(orders+1 - o_array)) > 0:
            print('Order: Error, Actual Order is not equal to specified Order')
        else:
            print('Order: Check Passed, Actual Order is equal to specified Order')

        # Extract the volumes that the stocks were added to the sample
        n_stocks = np.max(exp_data[:,2]+1)
        n_samples = np.max(exp_data[:,1]+1)
        for sample in range(int(n_samples)):
            volume_of_sample = exp_data[np.where(exp_data[:,1] == sample), 0]
            if sample == 0:
                volumes = volume_of_sample.reshape(1,-1)
            else:
                volumes = np.vstack((volumes, volume_of_sample.reshape(1,-1)))
        # Check if all volumes are equal to specified volums
        if np.sum(np.abs(volumes - v_array)) > 0:
            print('Volume: Error, Actual Volume is not equal to specified Volume')
        else:
            print('Volume: Check Passed, Actual Volume is equal to specified Volume')
        
    