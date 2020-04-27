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

def pitsburg(state, columns, pit_columns, inpath):

     url = 'https://stacks.stanford.edu/file/druid:yg821jf8611/yg821jf8611_pa_pittsburgh_2020_04_01.csv.zip'

    pits = pd.read_csv(url, nrows=500).loc[:, pit_columns]
    pits = pits.dropna()
    pits = pits[(pits.subject_race.isin(['white','black','asian/pacific islander','hispanic']))&(pits.officer_race != 'unknown')].reset_index(drop=True)

    def group_time(time):
        hour = int(time.split(':')[0])
        if hour >= 6 and hour <= 11:
            return 'Morning'
        elif hour >= 12 and hour <=4:
            return 'Afternoon'
        elif hour >= 5 and hour <=8:
            return 'Evening'
        else:
            return 'Night'

    def officer_race_rename(race):
        if race == 'asian/pacific islander':
            return 'asian'
        elif race == 'other':
            return 'hispanic'
        else:
            return race


    def bool_col(bool_):
        if bool_:
            return 1 
        else:
            return 0

    def violation_filtering(violation):
        moving_violations = ['Obedience to Traffic-Control Devices','Traffic-Control Signals',
                             'Turning Movements and Required Signals','Careless Driving ','Speed Limits',
                            'Turning','Speed Limitations']
        equiptment_violations = ['Vehicle Equipment Standards','General Lighting Requirements',
                                 'Windshield','Lighted Lamps','Registration Plate']
        for mv in moving_violations:
            if mv in violation:
                return 'Moving Violation'
        for mv in equiptment_violations:
            if mv in violation:
                return 'Equiptment Violation'
        else:
            return 'Other Violation'

    filter_dict = {'time':group_time,'lat':(lambda x: round(x,2)),'lng':(lambda x: round(x,2)),'subject_race':
                   (lambda race: 'asian' if race == 'asian/pacific islander' else race),
                  'officer_race': officer_race_rename, 'subject_sex':(lambda sex: 1 if 'male' else 0),
                   'officer_sex': (lambda sex: 1 if 'male' else 0),'arrest_made':bool_col,
                   'citation_issued':bool_col,'contraband_found':bool_col,'search_conducted':bool_col,
                  'violation':violation_filtering}

    for row, func in filter_dict.items():
        pits[row] = pits[row].apply(func)
        
    return pits

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

        if state == "pa":
            table = pittsburgh(state, columns, pit_columns, inpath)
        else:
            table = get_stops(state, columns, pit_columns, inpath)

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