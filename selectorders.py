from re import sub
import numpy as np
import latinsquare
import seaborn as sns
from matplotlib import pyplot as plt
import pandas as pd

import git

'''
Evaluate counterbalancing stategies for videos in founcog study
Stimuli for each participant comprise three subblocks of 6-8 videos
Maybe 40-50 participants but poor control over which data will be usable, making complex counterbalancing stategies difficult.
Analysis goals:
- MVPA across 6-8 videos, requiring minimal temporal bias. MVPA will be done across subblocks but need to watch out for balance of videos that are adjacent across subblocks.
- inter-subject correlation between subjects seeing same subblock of movies. Need as many subjects as possible with given order, while satisfying other constraints. Also plan to analyse effect of context, so want to compare effect of X preceded by Y vs. Z. Requires different orders to have different adjacencies.
- may be order effects

v1: 2021-05-18 Rhodri Cusack, Trinity College Dublin
Simulate a set of nsubj=40 subjects nperm=100 times
Optimise two metrics:
(1) across subblock adjacency. As MVPA is performed across blocks, need balance of what follows what at block boundaries. So calculate matrix of what follows what (video X -> video Y), and summarise this by the largest difference - i.e., most common adjacency - least common 
(2) within subblock adjaceny. Want different orders to give movies different contexts (i.e., have different things preceding them). Quantify this by correlation of adjacency matrix of different subblocks orders.
'''

def generate_latin_subblock_order(nvid=6):
    # Generate a set of subblock orders following a latin square
    return(latinsquare.rls(nvid))        

def generate_subblock_order_set(nsubblock_orders=20, nvid=6):
    # Generate a set of random subblock orders 
    subblock_order_set=[]
    for subblock in range(nsubblock_orders):
        order = np.arange(nvid)
        np.random.shuffle(order)
        subblock_order_set.append(order)
    return subblock_order_set

def generate_order(subblock_order_set, nsubblock=3):
    # Generate an order for a given subject, by selecting orders from the possible set for each of their subblocks 
    order=[]
    # Don't repeat orders within a subject. Is this the right thing to do?
    possible_subblock_order = list(range(len(subblock_order_set)))

    for subblock in range(nsubblock):
        subblock_order_ind=np.random.choice(possible_subblock_order)
        possible_subblock_order.remove(subblock_order_ind)
        order.append(subblock_order_set[subblock_order_ind])
    return(order)

def assess_adjacency(nvid, order):
    # Calculate what follows what, within and across subblocks, giving nvid * nvid adjacency matrix
    allvids=[x for y in order for x in y]
    adjacency = np.zeros((nvid,nvid))
    for vidind in range(len(allvids)-1):
        adjacency[allvids[vidind], allvids[vidind+1]]+=1
    return adjacency

def assess_across_block_adjacency(nvid, order):
    # Calculate what follows what across subblocks, giving nvid * nvid adjacency matrix
    adjacency = np.zeros((nvid,nvid))
    for block in range(len(order)-1):
        adjacency[order[block][-1], order[block+1][0]]+=1
    return adjacency

if __name__=='__main__':

    counterbalancetype='optimised_balance_pairs'   # Choices random | latinsquare | optimised | optimised_balance_pairs
    
    nvid=6          # number of videos
    nsubj=40        # number of subjects in a study
    nperm=100       # number of studies to generate
    noptperm=5000    # when optmising latin squares, do this many  iterations 


    # Tag output with git commit
    repo = git.Repo(search_parent_directories=True)

    # To store results
    df=pd.DataFrame()

    for nsubblock_orders in range(10,50,5):
        # When random, create this many subblock orders. Otherwise, it is ignored.
        aba_std=[]
        aba_range=[]

        for perm in range(nperm):
            # For each "study"...
            # Generate possible subblock orders using one of our strategies
            if counterbalancetype=='latinsquare':
                subblock_order_set=generate_latin_subblock_order(nvid=nvid)      
                nsubblock_orders = nvid    
            elif counterbalancetype=='random':
                subblock_order_set=generate_subblock_order_set(nvid=nvid, nsubblock_orders=nsubblock_orders)
            elif counterbalancetype=='optimised':
                # Optimise order, by generating a random set and picking the one with the minimum across-order adjacency correlation
                iu1=np.triu_indices(nvid, k=1)
                cmeanmin=np.inf
                nsubblock_orders = nvid
                for optperm in range(noptperm):
                    subblock_order_set=generate_latin_subblock_order(nvid=nvid) 
                    order_adjacency=np.zeros((nsubblock_orders, nvid, nvid))     
                    for orderind in range(nsubblock_orders):
                        order_adjacency[orderind,:,:] = assess_adjacency(nvid, subblock_order_set[orderind:orderind+1])                                       
                    cmean=np.corrcoef(order_adjacency.reshape(nsubblock_orders, nvid*nvid))[iu1].mean()
                    if cmean<cmeanmin:
                        cmeanmin=cmean
                        optorder=subblock_order_set
            elif counterbalancetype=='optimised_balance_pairs':
                # Optimise order, by generating a random set and picking the one with the most order adjacency set with most balanced pairs 
                iu1=np.triu_indices(nvid, k=1)
                cmeanmin=np.inf
                nsubblock_orders = nvid
                for optperm in range(noptperm):
                    subblock_order_set=generate_latin_subblock_order(nvid=nvid) 
                    order_adjacency=np.zeros((nsubblock_orders, nvid, nvid))     
                    for orderind in range(nsubblock_orders):
                        order_adjacency[orderind,:,:] = assess_adjacency(nvid, subblock_order_set[orderind:orderind+1])                                       
                    order_adjacency_set = np.sum(order_adjacency, axis =0)
                                        
                    maxes = np.max(order_adjacency_set,axis=0)
                    order_adjacency_set_temp  = order_adjacency_set.copy()
                    order_adjacency_set_temp[order_adjacency_set_temp == 0] = 999 # want min of non-zero entries only, so put the zeros out of the range 
                    mins = np.min(order_adjacency_set_temp,axis=0) 

                    # Want max and min to be 2 and 3 or 3 and 2
                    cost = np.sum(np.power(maxes-2.5, 2)) + np.sum(np.power(mins-2.5, 2))  

                   
                    if cost<cmeanmin:
                        cmeanmin=cost
                        optorder=subblock_order_set
                        print(cost)
                        print (order_adjacency_set)

                subblock_order_set = optorder

                print(subblock_order_set)

            # Assess subblock orders
            order_adjacency=np.zeros((nsubblock_orders, nvid, nvid))
            for orderind in range(nsubblock_orders):
                order_adjacency[orderind,:,:] = assess_adjacency(nvid, subblock_order_set[orderind:orderind+1])
                    
            order_adjacency_reshaped = order_adjacency.reshape(nsubblock_orders, nvid*nvid)
            iu1=np.triu_indices(nsubblock_orders, k=1)
            c=np.corrcoef(order_adjacency_reshaped)
            c_iu1=c[iu1]

            allsubj_adjacency = np.zeros((nvid,nvid))
            allsubj_across_block_adjacency = np.zeros((nvid,nvid))
            
            # Create a single study
            for subj in range(nsubj):
                # Create each subject and calculate their metrics
                order = generate_order(subblock_order_set)
                allsubj_adjacency  = allsubj_adjacency + assess_adjacency(nvid, order)
                allsubj_across_block_adjacency  = allsubj_across_block_adjacency + assess_across_block_adjacency(nvid, order)

            # Summarise this study and store results
            df = df.append({'aba_range': np.max(allsubj_across_block_adjacency) - np.min(allsubj_across_block_adjacency), 
                    'aba_std':np.std(allsubj_across_block_adjacency),
                    'nsubblock_orders': nsubblock_orders,
                    'mean_c_iu1': np.mean(c_iu1)
                    },ignore_index=True)
    
    # Plot up

    fig,ax = plt.subplots(nrows=2, ncols=2)
    
    sns.violinplot(x=df['nsubblock_orders'].astype(int), y=df['aba_range'], ax=ax[0,0])
    ax[0,0].title.set_text(f'{counterbalancetype} N={nsubj}')
    sns.violinplot(x=df['nsubblock_orders'].astype(int), y=df['mean_c_iu1'], ax=ax[1,0])
    ax[1,0].title.set_text(f'N={nsubj}')

 
    im0 = ax[0,1].imshow(allsubj_adjacency)
    ax[0,1].title.set_text('e.g., within- and between- block adjacency ')
    fig.colorbar(im0, ax=ax[0,1])

    im1 = ax[1,1].imshow(allsubj_across_block_adjacency)
    ax[1,1].title.set_text('e.g., between-block adjacency ')
    fig.colorbar(im1, ax=ax[1,1])
    
    plt.tight_layout()

    plt.savefig(f'{counterbalancetype}_N_{nsubj}_{repo.head.object.hexsha}.jpg')
    plt.show()