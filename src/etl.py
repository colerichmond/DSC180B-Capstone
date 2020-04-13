import pandas as pd
import os

def get_stops(state, columns):
    '''
    return a downloadable file of traffic
    stops for a given year before RIPA.
    
    :param: given year to fetch
    '''
    
    url = 'https://stacks.stanford.edu/file/druid:kx738rc7407/kx738rc7407_%s_statewide_2019_12_17.csv.zip' % (state)
    column_set = columns

    return pd.read_csv(url).loc[:, column_set]

# ---------------------------------------------------------------------
# Driver Function(s)
# ---------------------------------------------------------------------
    
def get_data(states, columns, outpath):
    '''
    downloads and saves traffic stops tables 
    at the specified output directory for the
    given year.
    
    :param: states: a list of states from which to collect data
    :param: outdir: the directory to which to save the data
    '''
    print('Ingesting data...')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
        
    for state in states:
        table = get_stops(state, columns)
        file_name = '%s_stops.csv' % (state)
        table.to_csv(os.path.join(outpath, file_name))
    
    print('...done!')
    return