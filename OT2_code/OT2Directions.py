import pandas as pd
import numpy as np
from OT2_code import CreateSamples, OT2Commands, Create_Directions
from opentrons import simulate, execute, protocol_api
import random
import os
import math
import time

class experiment():
    def __init__(self):
        self.air_gap = 20.0
        self.well_order = 'row'
        return 
        
    def simulate(self, path):
        ''' Function to simulate the experiment '''

        #path = r"Samples_and_Protocol/Protocol/protocol.csv"
        labware_dir_path = r"OT2_code/Custom_Labware"
        self.plan = CreateSamples.get_experiment_plan(path)
        self.custom_labware_dict = OT2Commands.custom_labware_dict(labware_dir_path)
        protocol = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.protocol2 = simulate.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.loaded_dict = OT2Commands.loading_labware(protocol, self.plan, well_order=self.well_order)
        return protocol
    
    def execute(self, path):
        ''' Function to execute the experiment '''
        #path = r"Samples_and_Protocol/Protocol/protocol.csv"
        labware_dir_path = r"OT2_code/Custom_Labware"
        self.plan = CreateSamples.get_experiment_plan(path)
        self.custom_labware_dict = OT2Commands.custom_labware_dict(labware_dir_path)
        protocol = execute.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.protocol2 = execute.get_protocol_api('2.8', extra_labware=self.custom_labware_dict)
        self.loaded_dict = OT2Commands.loading_labware(protocol, self.plan, well_order=self.well_order)
        return protocol 
    
    def calculate_exp_duration(self, direction_array, print_time=True, **kwargs):
        ''' Function to determine the total time the experiment will take at time = 0'''

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
        if print_time == True:
            print('Experiment will take a total time of:')
            print(hours, 'hours')
            print(minutes, 'minutes')
        return total_time
        
    def calculate_remaining_exp_duration(self, direction_array, **kwargs):
        ''' Function to determine how long the experiment will take at time = t'''

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
        print('Total time left ', hours, ' hours', minutes, ' minutes')

    def stock_solution_ranges(self, direction_array, vial_volume):
        ''' Function to determine how many stock solution vials are needed '''

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
        ''' Function that specifies what the opentrons performs at each action '''

        if self.display_action == True:
            print('Step ', self.action, ' out of ', self.total_actions)
            print('Transferring ', np.round(volume) ,'uL from Stock',stock_solution, ' into Well', sample_well)
            self.calculate_remaining_exp_duration(self.remaining_direction_array, action_time = self.action_time)
            print('')    
        
        #This controls what the pipette does at each step
        pipette.aspirate(volume, self.loaded_dict['Stock Wells'][stock_solution])
        
        if volume < 16:
            pipette.air_gap(4)
        elif volume <= self.air_gap:
            pass
        else:
            pipette.air_gap(self.air_gap)
        pipette.dispense(volume, self.loaded_dict['Destination Wells'][sample_well], rate=1.5)
        pipette.blow_out()
        self.dispense_time = time.time()
        
        pipette.mix(2, 100, self.loaded_dict['Destination Wells'][sample_well],rate=1.5)
        ##Wash the tip to prevent liquid from entering the tip rack
        pipette.mix(2, 150, self.loaded_dict['Resevoir Wells'][-1],rate=2)
        pipette.mix(2, 150, self.loaded_dict['Resevoir Wells'][-2],rate=2)
        pipette.blow_out(self.loaded_dict['Resevoir Wells'][-5])
            
    def perform_directions(self, protocol, direction_array, **kwargs):
        '''Main function to start running the protocol '''

        if 'start_location' in kwargs.keys():
            start_location = kwargs['start_location']
        action_time = self.action_time
        self.small_pipette = self.loaded_dict['Small Pipette']
        self.small_tiprack = self.loaded_dict['Small Tiprack']
        self.large_pipette = self.loaded_dict['Large Pipette']
        self.large_tiprack = self.loaded_dict['Large Tiprack']
        
        if protocol.is_simulating() == False:
            self.display_action = True
        else:
            self.display_action = False
                
        for action in range(direction_array.shape[0]):
            self.action = action
            self.total_actions = direction_array.shape[0]
            self.remaining_direction_array = direction_array[action:,:]
            volume = int(direction_array[action, 0])
            sample_well = int(direction_array[action, 1] + start_location)
            stock_solution = int(direction_array[action, 2])
            start_time = time.time()
            if volume > self.small_pipette.max_volume-self.air_gap: #Use large pipette
                self.large_pipette.pick_up_tip(self.loaded_dict['Large Tiprack'][stock_solution])
                self.pipette_action(self.large_pipette, volume, sample_well, stock_solution)
                self.large_pipette.drop_tip(self.loaded_dict['Large Tiprack'][stock_solution].bottom(12))
                end_time = time.time()
                actual_time_taken = end_time - start_time
                delay_time = action_time - actual_time_taken
                #assert delay_time > 0, 'Increase the action_time'
                if delay_time > 0:
                    protocol.delay(seconds= delay_time)
                else:
                    print('Increase the action time. OT2 takes longer than action time to perform action')
            elif volume > 0: #Use small pipette 
                self.small_pipette.pick_up_tip(self.loaded_dict['Small Tiprack'][stock_solution])
                self.pipette_action(self.small_pipette, volume, sample_well, stock_solution)
                self.small_pipette.drop_tip(self.loaded_dict['Small Tiprack'][stock_solution].bottom(10))
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
        
#         self.transfer_samples(protocol, 200, 10)

        protocol.home() 
        for line in protocol.commands(): 
            print(line)


    def transfer_samples(self, protocol, volume, transfer_offset, **kwargs):
        ''' Optional function to transfer samples from one labware to another
            inputs:
            Volume = amount in uL that will be transferred in all specified wells
            transfer_offset = The height in mm from the bottom of the source transfer well
            Transfer Wells = an array which specifies the locations fo the wells to be transferred. If this is 
            not specified, the wells will be transferred one by one'''

        self.small_pipette = self.loaded_dict['Small Pipette']
        self.small_tiprack = self.loaded_dict['Small Tiprack']
        self.large_pipette = self.loaded_dict['Large Pipette']
        self.large_tiprack = self.loaded_dict['Large Tiprack']
        
        if 'Transfer Wells' in self.loaded_dict.keys():
            if volume > self.small_pipette.max_volume: # Use Large Pipette
                self.pipette = self.loaded_dict['Large Pipette']
                self.pipette.pick_up_tip(self.loaded_dict['Large Tiprack'][-1])
            else:
                self.pipette = self.loaded_dict['Small Pipette']
                self.pipette.pick_up_tip(self.loaded_dict['Small Tiprack'][-1])
                
        else:
            print('Error: Transfer wells not specified in protocol')
        
        if 'starting_position' in kwargs.keys():
            starting_position = kwargs['starting_position']
        else:
            starting_position = 0

        if 'source_well_index' in kwargs.keys(): # If the source wells is specified by an array of the well index 
            source_well_index = kwargs['source_well_index']
            for sample in range(len(source_well_index)):
                self.pipette.aspirate(volume, self.loaded_dict['Destination Wells'][source_well_index[sample]].bottom(transfer_offset),rate=0.5)
                self.pipette.dispense(volume, self.loaded_dict['Transfer Wells'][sample + starting_position])
                self.pipette.blow_out()
                self.pipette.mix(2, 20, self.loaded_dict['Resevoir Wells'][-3])
                self.pipette.mix(2, 20, self.loaded_dict['Resevoir Wells'][-4])
                self.pipette.blow_out(self.loaded_dict['Resevoir Wells'][-5])
            self.pipette.drop_tip()
        elif 'n_samples' in kwargs.keys(): # If the source wells index and destination well index is the same
            n_samples = kwargs['n_samples'] 
            for sample in range(n_samples):
                self.pipette.aspirate(volume, self.loaded_dict['Destination Wells'][sample].bottom(transfer_offset),rate=0.5)
                self.pipette.dispense(volume, self.loaded_dict['Transfer Wells'][sample + starting_position])
                self.pipette.blow_out()
                self.pipette.mix(2, 20, self.loaded_dict['Resevoir Wells'][-3])
                self.pipette.mix(2, 20, self.loaded_dict['Resevoir Wells'][-4])
                self.pipette.blow_out(self.loaded_dict['Resevoir Wells'][-5])
            self.pipette.drop_tip()

        protocol.home() 
        for line in protocol.commands(): 
            print(line)
    
    def test(self, exp_data, v_array, t_array, o_array):
        ''' Optional function to test if the actual actions correspond to the specified '''

        # Make sure that there are no zeros in the v_array 
        n_stocks = v_array.shape[1]
        n_samples = v_array.shape[0]
        #assert int((n_stocks)*(n_samples)) == exp_data.shape[0], 'Test will not work since some volumes are 0. New test need to be created for this case'
        # Sort Values first based on Sample number and then by time that they were added 
        exp_data = exp_data[(exp_data >= 0).all(1)]
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

        # Change the relative time of the first stock of each sample to 0
        stock_0_of_sample = delay_times[::n_stocks]
        for j in range(len(stock_0_of_sample)):
            for i in range(len(delay_times)):
                if delay_times[i] == stock_0_of_sample[j]:
                    delay_times[i] = 0
                    break

        delay_times = np.abs(delay_times)
        # Create exp_data array with relative time delays as last column
        exp_data = np.hstack((exp_data, delay_times.reshape(-1,1)))
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
        if np.sum(np.abs(np.floor(volumes) - np.floor(v_array))) > 0:
            print('Volume: Error, Actual Volume is not equal to specified Volume')
        else:
            print('Volume: Check Passed, Actual Volume is equal to specified Volume')

    
    def change_order(self, order_x, v_array, t_array, o_array):
        ''' Function to shuffle the order of the input arrays based on order_x'''

        order_lst = []
        for i in range(len(order_x)):
            order_lst.append(int(order_x[i]))
        order_x = np.array(order_lst)
        v_array = v_array[order_x, :]
        t_array = t_array[order_x, :]
        o_array = o_array[order_x, :]
        direction_array = Create_Directions.create_directions(v_array, t_array, o_array)
        return direction_array, v_array, t_array, o_array


    def optimize(self, v_array, t_array, o_array):
        '''Calculates the direction_array for shuffled versions of the input arrays and returns the order that
           takes the least amount of time to complete '''

        all_times = []
        for j in range(10):
            order_x = np.linspace(0, v_array.shape[0]-1, v_array.shape[0])
            np.random.shuffle(order_x)
            direction_array, a, b, c = self.change_order(order_x, v_array, t_array, o_array)
            total_time = self.calculate_exp_duration(direction_array, print_time = False, action_time = 60)
            all_times.append(total_time)
            if j == 0:
                all_orders = order_x.reshape(1,-1)
            else:
                all_orders = np.vstack((all_orders, order_x.reshape(1,-1)))
        all_times = np.array(all_times).reshape(-1,1)
        order_times = np.hstack((all_orders, all_times))
        sorted_array = order_times[np.argsort(order_times[:, -1])]
        best_order = sorted_array[0,:-1]
        best_time = sorted_array[0,-1]
        return best_order, best_time
    
    