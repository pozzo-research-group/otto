import pandas as pd
import numpy as np
import random

def create_order(c_array, t_array, order):
    '''This function will create a sparse matrix that includes information on the volumes, time delays, and the order of 
       addition of stock solution'''

    end = False
    SIZE = 100
    c_array[c_array < 1] = 982121 #If the volume is 0 in c_array, replace it with 9821 to cut it out later in the c_array
    check_array = np.zeros((c_array.shape[0],c_array.shape[0]*SIZE))
    for sample in range(len(order)): #Iterate over rows 
        for n_conc in range(c_array.shape[1]): #Iterate over columns
            if n_conc == 0: #position of the first concentration 
                check_array[order[sample], n_conc] = c_array[sample, n_conc]
                position_array = np.array([order[sample], n_conc]).reshape(1,-1)
            else: #Position of the nth concentration relative to the first one
                position_ = position_array[n_conc-1,1] + 1 + t_array[sample,n_conc-1]
                assert position_ < check_array.shape[1], 'If this error occurs, increase the variable "SIZE" in line 7 of Create_Directions.py. If the code takes too long to run, decrease the variable "SIZE"'
                check_array[order[sample], position_] = c_array[sample, n_conc]  
                pos = np.array([order[sample], position_]).reshape(1,-1)
                position_array = np.vstack((position_array, pos)) 
    return check_array 

def optimize_order(check_array):
    '''This function will optimize the order of adding the stock solutions based on their positions in the sparse matrix'''

    for row_of_check_array in range(check_array.shape[0]):
            break_while_loop = False
            while break_while_loop == False:
                T_F_list = []
                for columns in range(check_array.shape[1]):
                    non_zeros = []
                    column = check_array[0:row_of_check_array+1,columns]
                    #print('col:', column)
                    for rows in range(len(column)):
                        if column[rows] > 0:
                            non_zeros.append(1)
                        else:
                            pass
                    #print('non zeros: ', non_zeros)
                    #print('length:', len(non_zeros))
                    if len(non_zeros) == 1:
                        end = True 
                    elif len(non_zeros) == 0:
                        end = True 
                    elif len(non_zeros) > 1:
                        end = False
                    T_F_list.append(end)
                    #elif len(non_zeros) == 3:
                    #    end = True
                    #print('end: ', end)
                    #print('check_array: ', check_array)
                    if end == False:
                        check_array[row_of_check_array,:] = np.roll(check_array[row_of_check_array,:], 1)
                        break_while_loop = False
                T_F_array = np.array(T_F_list)
                if T_F_array.all() == True:
                    break_while_loop = True
    return check_array

def determine_total_time(check_array):
    '''This function determines the total time that the protocol will take'''
    
    row, column = np.where(check_array > 0)
    total_time = np.max(column)
    return total_time 

def run_gchart_optimization(c_array, t_array, **kwargs):
    '''This seems like a dead function'''
    results = {}
    results['order'] = []
    results['time'] = []
    results['check_array'] = []
    Iterations = kwargs['Iterations']
    Batch_Size = kwargs['Batch_Size']
    for i in range(Iterations):
        order = np.linspace(0,Batch_Size,Batch_Size+1)
        #order = random.sample(range(c_array.shape[0]), Batch_Size)
        print(type(order))
        check_array = create_order(c_array, t_array, order)
        check_array = optimize_order(check_array)
        total_time = determine_total_time(check_array)
        results['order'].append(order)
        results['time'].append(total_time)
        results['check_array'].append(check_array)
    min_time_loc = np.argmin(np.array(results['time']))
    min_time = np.min(np.array(results['time']))
    best_chart = results['check_array'][min_time_loc]
    results['min_time'] = min_time
    return best_chart, results

def gchart(c_array, t_array, **kwargs):
    n_samples = kwargs['n_samples']
    #order = np.linspace(0,Batch_Size,Batch_Size+1)
    #order = random.sample(range(c_array.shape[0]), Batch_Size)
    order = []
    for i in range(n_samples):
        order.append(i)
    check_array = create_order(c_array, t_array, order)
    check_array = optimize_order(check_array)
    return check_array

def post_processing(best_chart, stock_sol_pos):
    volume_array = best_chart.copy()
    volume_list = []
    sample_list = []
    for column in range(volume_array.shape[1]):
        volume = np.max(volume_array[:,column])
        sample = np.argmax(volume_array[:,column])
        volume_list.append(volume)
        sample_list.append(sample)
    volume_and_position = np.hstack((np.array(volume_list).reshape(-1,1),np.array(sample_list).reshape(-1,1)))
    
    #Cuts all the rows with volume = 982121
    del_col = np.where(volume_and_position[:,0] == 982121)[0]
    volume_and_position = np.delete(volume_and_position, del_col, axis=0)
    
    for row in range(volume_and_position.shape[0]):
        row_array = volume_and_position[row, :]
        if row_array[0] == 0 and row_array[1] == 0:
            volume_and_position[row, :] = np.array([-1,-1])

   
    position_list = []
    for row in range(volume_and_position.shape[0]):
        position = volume_and_position[row,1]
        position_list.append(position)
        position_array = np.array(position_list)

    #Determines how many times each stock has been added to the sample   
    for samples in range(-1, int(np.max(position_array)+1)):
        locations = np.where(position_array == samples)
        for i in range(len(locations[0])):
            if position_array[locations[0][i]] == -1:
                pass 
            else:
                position_array[locations[0][i]] = i + 100
    stock_solutions = position_array - 99

    # Changes -100 to -1 
    for i in range(len(stock_solutions)):
        if stock_solutions[i] == -100:
            stock_solutions[i] = -1
        else:
            stock_solutions[i] = stock_solutions[i] - 1
    
    memory_array = np.zeros(stock_sol_pos.shape)
    for i in range(len(stock_solutions)):
        sample_num = int(volume_and_position[i, 1])
        if stock_solutions[i] < 0:
            pass
        else:
            for stock_num in range(stock_sol_pos.shape[1]):
                if memory_array[sample_num, stock_num] == 0:
                    stock_solutions[i] = stock_sol_pos[sample_num, stock_num]
                    memory_array[sample_num, stock_num] = 1
                    break

   
    direction_array = np.hstack((volume_and_position, stock_solutions.reshape(-1,1))) #first column is the volume, then sample position, then stock solution
    
    #Cuts the extra rows at the bottom 
    upside_down_array = np.flipud(direction_array)
    for row in range(upside_down_array.shape[0]):
        if np.all(upside_down_array[row,:] == -1):
            pass
        else:
            break 
    direction_array = direction_array[0:-row, :]


    # This code merges all the rows where no action should take place
    # If there are two consecutive rows of [-1,-1,-1] they will be combined to
    # [-2,-2,-2,]
    for row in range(1, direction_array.shape[0]):
        if np.all(direction_array[row,:] == -1): #The row is [-1,-1,-1]
            for n_row in range(row + 1, direction_array.shape[0]):
                if np.all(direction_array[n_row,:] != -1): #The next row is not [-1,-1,-1] 
                    row = n_row
                    break
                elif np.all(direction_array[n_row,:] == -1): #The next row is [-1,-1,-1]
                    direction_array[row, :] = direction_array[row, :] + direction_array[n_row, :]

    row, col = np.where(direction_array < 0)
    row = np.unique(row)
    rows_to_del = []  
    for num in range(len(row)-1):
        if row[num] + 0.5 == (row[num] + row[num+1])/2: #If the next number is consecutive 
            rows_to_del.append(row[num+1])
    direction_array = np.delete(direction_array, rows_to_del, axis = 0)
    return direction_array
    
def create_directions(c_array, t_array, o_array):
    copy_c_array = c_array.copy()
    stock_sol_array = c_array.copy()
    for sample in range(o_array.shape[0]): #Iterate over the number of samples
        for stock in range(o_array.shape[1]): #Iterate over the number of stock solutions in one sample
            c_array[sample,  o_array[sample, stock]-1] = copy_c_array[sample, stock]
            stock_sol_array[sample,  o_array[sample, stock]-1] = stock
    best_chart = gchart(c_array, t_array, n_samples = c_array.shape[0])
    direction_array = post_processing(best_chart, stock_sol_array)
    return direction_array