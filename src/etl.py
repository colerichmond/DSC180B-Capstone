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

def get_clean_stops(pth, df):
        
    state = pth.split('_')[0].upper()

    df = clean_races(df)
    df = convert_date(df)
    df["county_name"] = df["county_name"].apply(clean_county, args=[state])

    return df

def clean_races(df):

    race_map = {"white" : "White",
                "black" : "Black",
                "hispanic" : "Hispanic",
                "asian/pacific islander" : "Asian"}

    df["subject_race"] = df["subject_race"].map(race_map)
    df["officer_race"] = df["officer_race"].map(race_map)
    
    return df

def clean_county(county, state):

    county = str(county) + ", " + state
    
    return county

def convert_date(df):
    
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d", errors='coerce')
    
    return df

def create_county_state(row):
    county_state = row['COUNTY'] + ', '
    if row['STATE'] == 'Florida':
        county_state += 'FL'
    elif row['STATE'] == 'South Carolina':
        county_state += 'SC'
    else:
        county_state += 'WA'
    return county_state


def create_population_dataset(fname):

    final_cols = ['County_State','White','Black','Asian','Hispanic']

    national_pop = pd.read_csv(fname,encoding="ISO-8859-1")
    states_pop = national_pop[national_pop['STATE'].isin(['Washington','Florida','South Carolina'])]
    states_pop['County_State'] = states_pop.apply(create_county_state,axis=1)
    col_rename_mapper = {'H7Z003':'White','H7Z004':'Black','H7Z006':'Asian'}
    states_pop.rename(col_rename_mapper,axis=1,inplace=True)
    states_pop['Hispanic'] = states_pop['H7Z010'] - states_pop['H7Z017']

    pop_df = states_pop[final_cols]
    return pop_df

# ---------------------------------------------------------------------
# Driver Function(s)
# ---------------------------------------------------------------------
    
def get_data(states, columns, outpath=None, inpath=None):
    '''
    downloads and saves traffic stops tables 
    at the specified output directory for the
    given year.
    
    :param: states: a list of states from which to collect data.
    :param: columns: list of columns to keep from ingested data.
    :param: outpath: the directory to which to save the data.
    '''

    print('Ingesting data...')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
        
    for state in states:

        if inpath:
            inpath = os.path.join(inpath, '%s_stops.csv' % (state))
        else:
            inpath = None

        table = get_stops(state, columns, inpath)

        file_name = '%s_stops.csv' % (state)
        table.to_csv(os.path.join(outpath, file_name))
            
    print('...done!')

    return

def clean_stops(df_iter=(), outpath=None, inpath=None):
    
    print('Cleaning data...')
    
    if outpath and not os.path.exists(outpath):
        os.makedirs(outpath)

    if not df_iter:
        df_iter = ((p, pd.read_csv(os.path.join(inpath, p))) for p in os.listdir(inpath))

    for pth, df in df_iter:
        cleaned = get_clean_stops(pth, df)
        if outpath:
            cleaned.to_csv(os.path.join(outpath, pth))
            
    print('...done!')
            
    return 