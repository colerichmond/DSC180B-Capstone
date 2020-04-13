import pandas as pd
import os

def get_stops_url(state, columns):
    '''
    return a downloadable file of traffic
    stops for a given year before RIPA.
    
    :param: given year to fetch
    '''
    
    url = 'https://stacks.stanford.edu/file/druid:kx738rc7407/kx738rc7407_%s_statewide_2019_12_17.csv.zip' % (state)

    return pd.read_csv(url, nrows=500).loc[:, columns]

def get_stops_local(inpath):
    '''
    return a table of traffic stops for a given 
    state, from a location on local disk.
    '''

    df = pd.read_csv(inpath)

    return df

def get_stops(state, columns, inpath=None):
    '''
    return a table of season statistics for a
    given team and year.
    '''

    if not inpath:
        return get_stops_url(state, columns)
    else:
        return get_stops_local(inpath)

# ---------------------------------------------------------------------
# Driver Function(s)
# ---------------------------------------------------------------------
    
def get_data(states, columns, outpath=None, indir=None):
    '''
    downloads and saves traffic stops tables 
    at the specified output directory for the
    given year.
    
    :param: states: a list of states from which to collect data.
    :param: columns: list of columns to keep from ingested data.
    :param: outdir: the directory to which to save the data.
    '''

    print('Ingesting data...')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
        
    for state in states:

        if indir:
            inpath = os.path.join(indir, '%s_stops.csv' % (state))
        else:
            inpath = None

        table = get_stops(state, columns, inpath)

        file_name = '%s_stops.csv' % (state)
        table.to_csv(os.path.join(outpath, file_name))
    
    print('...done!')
    return