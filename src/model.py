import os
import pandas as pd
import numpy as np
import warnings
import json
from scipy.stats import ttest_rel
from sklearn.neighbors import NearestNeighbors
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

# TRAINCOLS = [
#     'county_name',
#     'subject_age',
#     'subject_sex',
#     'violation',
#     'arrest_made',
#     'citation_issued',
#     'search_conducted'
#     ]

# def data_loader(indir, traincols=TRAINCOLS):
    
#     df = pd.concat([pd.read_csv(os.path.join(indir, p)[traincols].dropna(subset=traincols).reset_index(drop=True)) for p in os.listdir(indir)])

#     df['subject_sex'] = df['subject_sex'].apply(lambda sex: {'female': 0, 'male': 1}.get(sex, ' '))

#     bool_cols = ['arrest_made','citation_issued','search_conducted']

#     for col in bool_cols:
#         df[col] = df[col].apply(lambda x: 1 if x else 0)

#     df = pd.get_dummies(df,prefix=['county','violation'], columns=['county_name','violation'])

#      # probabiltiy searched 
#     X = fl_ohe.drop(['arrest_made','citation_issued','search_conducted'],axis=1)
#     y = fl_ohe['search_conducted']
#     lr = train_model(X, y)
#     probs_searched = [x[1] for x in lr.predict_proba(X)]

#     # probabiltiy cited 
#     X = fl_ohe.drop(['arrest_made','citation_issued'],axis=1)
#     y = fl_ohe['citation_issued']
#     lr = train_model(X, y)
#     probs_cited = [x[1] for x in lr.predict_proba(X)]

#     # probabiltiy arrested 
#     X = fl_ohe.drop(['arrest_made','citation_issued'],axis=1)
#     y = fl_ohe['arrest_made']
#     lr = train_model(X, y)
#     probs_arrested = [x[1] for x in lr.predict_proba(X)]

#     return list(zip(probs_searched,probs_cited,probs_arrested))


# def train_model(X, y, outdir=None):

#     lr = LogisticRegression(n_jobs=1, solver='liblinear')
#     lr.fit(X, y)

#     return lr

def propensity_score_func(df_, **cfg):
    
    df = df_.copy()
    if 'time' in df.columns:
        
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

        df['time'] = df['time'].apply(group_time)
        
    df.drop("date",axis=1,inplace=True)
    
    driver_r1, officer_r1 = cfg['strata_1'].split('/')
    driver_r2, officer_r2 = cfg['strata_2'].split('/')
    df_ps = df[(df['subject_race'].isin([driver_r1,driver_r2])) & (df['officer_race'].isin([officer_r1,officer_r2]))]
    
    ohe_cols = list(set(df_ps.columns).intersection(cfg['ohe_cols']))
    ohe_df = pd.get_dummies(df_ps,columns=ohe_cols)
    ohe_df.drop(['subject_race','officer_race'],axis=1,inplace=True)
    lr = LogisticRegression(n_jobs=1,solver='liblinear')
    
    # Only compute arrest probability for Pittsburg
    if 'lat' in df.columns:
        
        # Probability arresteted
        X = ohe_df.drop(['search_conducted','arrest_made','citation_issued'],axis=1)
        Y = ohe_df['arrest_made']
        try:
            lr.fit(X,Y)
            probs_arrested = [x[1] for x in lr.predict_proba(X)]
        except:
            probs_arrested = len(X)*[np.nan]
        
        df_ps = df_ps[['subject_race','officer_race','arrest_made']].assign(arrest_ps = probs_arrested)
        
        return df_ps
    
    else:
        
         # Probability searched 
        X = ohe_df.drop(['arrest_made','citation_issued','search_conducted'],axis=1)
        Y = ohe_df['search_conducted']
        display(X)
        display(Y)
        lr.fit(X,Y)
        probs_searched = [x[1] for x in lr.predict_proba(X)]

        # Probability cited 
        X = ohe_df.drop(['arrest_made','citation_issued'],axis=1)
        Y = ohe_df['citation_issued']
        lr.fit(X,Y)
        probs_cited = [x[1] for x in lr.predict_proba(X)]

        # Probability arrested 
        Y = ohe_df['arrest_made']
        try:
            lr.fit(X,Y)
            probs_arrested = [x[1] for x in lr.predict_proba(X)]
        except:
            probs_arrested = len(X)*[np.nan]
        probs_arrested = [x[1] for x in lr.predict_proba(X)]
    
        df_ps = df_ps[['subject_race','officer_race','search_conducted','citation_issued','arrest_made']]
        df_ps = df_ps.assign(search_ps = probs_searched, citation_ps = probs_cited, arrest_ps = probs_arrested)
        
        return df_ps.reset_index(drop=True)

def propensity_score_matching(df,**cfg):
    
    driver_r1, officer_r1 = cfg['strata_1'].split('/')
    driver_r2, officer_r2 = cfg['strata_2'].split('/')
    
    s1 = df[(df['subject_race'] == driver_r1) & (df['officer_race'] == officer_r1)]
    s2 = df[(df['subject_race'] == driver_r2) & (df['officer_race'] == officer_r2)]
    
    outcome_cols = [['search_conducted','search_ps','matched_search_conducted'],['citation_issued','citation_ps','matched_citation_issued'],
                    ['arrest_made','arrest_ps','matched_arrest_made']]
    
    for val, propensity_score, match_col in outcome_cols:
        
        s1_outcome = s1[[val,propensity_score]].dropna(subset=[propensity_score]).reset_index(drop=True)
        s2_outcome = s2[[val,propensity_score]].sort_values(val).dropna(subset=[propensity_score]).reset_index(drop=True)
        
        treated_x = s2_outcome[[propensity_score]].values
        non_treated_x = s1_outcome[[propensity_score]].values

        nbrs = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(non_treated_x)
        distances, indices = nbrs.kneighbors(treated_x)
        match_vals = [s1_outcome.loc[ind[0],val] if d < cfg['ps_threshold'] else 'No Match' for d,ind in zip(distances,indices)]
        extra_nans = [np.nan]*(len(s2) - len(match_vals))
        match_vals += extra_nans
        
        s2[match_col] = match_vals
    
    return s2

def t_test_results(matches,**cfg):
    
    output_df = pd.DataFrame(columns = ['Strata_1','Strata_2','T_Statistic','P_Value','Conclusion'],\
                             index=['search_conducted','citation_issued','arrest_made'])
    analyses = ['search_conducted','citation_issued','arrest_made']
    strata_1, strata_2 = cfg['strata_1'], cfg['strata_2']
    string_map = {'search_conducted':'searches conducted',
                 'citation_issued':'citations issued',
                 'arrest_made':'arrests made'}
    driver_r1, officer_r1 = cfg['strata_1'].split('/')
    driver_r2, officer_r2 = cfg['strata_2'].split('/')
    
    for a in analyses:
        
        matched_col = 'matched_' + a
        a_matches = matches[[a,matched_col]]
        a_matches = a_matches[(a_matches[matched_col]!='No Match') & (a_matches[a].notnull()) & (a_matches[matched_col].notnull())]
        t_stat, p_val = ttest_rel(a_matches[matched_col],a_matches[a],nan_policy="omit")
        
        if (p_val/2) < cfg['alpha']:
            if t_stat > 0:
                output_df.loc[a] = [strata_1,strata_2,t_stat,p_val,("Traffic stops involving drivers "
                "of race {} and officers of race {} had a greater proportion of {} than"
                'traffic stops with drivers of race {} and officers of race {}').format(driver_r1,officer_r1,string_map[a],driver_r2,officer_r2)]
            else:
                output_df.loc[a] = [strata_1,strata_2,t_stat,p_val,('Traffic stops involving drivers '
                'of race {} and officers of race {} had a greater proportion of {} than '
                'traffic stops with drivers of race {} and officers of race {}').format(driver_r2,officer_r2,string_map[a],driver_r1,officer_r1)]
        else:
            output_df.loc[a] = [strata_1,strata_2,t_stat,p_val,('There is no difference in the proportion of {} involving traffic stops '
            'with drivers of race {} and officers of race {} when compared with traffic stops with drivers of race {} and '
            'officers of race {}').format(string_map[a],driver_r1,officer_r1,driver_r2,officer_r2)]      
    return output_df

def propensity_analysis(dfs, **cfg):
    
    ps_dfs = False
    for df in dfs:
        ps_df = propensity_score_func(df,**cfg)
        if isinstance(ps_dfs, pd.DataFrame):
            ps_dfs = pd.concat([ps_dfs,ps_df])
        else:
            ps_dfs = ps_df
    ps_dfs = ps_dfs.sample(frac=1,random_state = 1).reset_index(drop=True)
    matches = propensity_score_matching(ps_dfs,**cfg)
    results = t_test_results(matches,**cfg)
    return results

def driver(**cfg):

    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)

    df_iter = [pd.read_csv(os.path.join(indir, p)) for p in os.listdir(indir)]

    return propensity_analysis(df_iter, **cfg)

# def propensity_matching(propensity_scores):
    
#     """
#     Matches traffic stops based on their respective searched, cited and arrested propensity scores.
#     Returns a list of dictionaries that indicate the indicies of the matches as follows:
#         [searched matches, cited matches, arrested matches]
#     A return dictionary entry example for searched matches is:
#         {1:124} (indicates that the stop at the 1st index has a searched propensity score closest to 124)
#     """
    
#     searched_dict = {}
#     cited_dict = {}
#     arrested_dict = {}
#     searched_propensity_scores = [(num,s[0]) for num,s in enumerate(propensity_scores)]
#     cited_propensity_scores = [(num,s[1]) for num,s in enumerate(propensity_scores)]
#     arrested_propensity_scores = [(num,s[2]) for num,s in enumerate(propensity_scores)]
    
#     for num, scores in enumerate(propensity_scores):
#         searched_ps, cited_ps, arrested_ps = scores
        
#         closest_match_searched = -1
#         closest_match_searched_diff = 1
#         for ind, ps in searched_propensity_scores:
#             if ind == num:
#                 continue
#             if abs(ps-searched_ps) < closest_match_searched_diff:
#                 closest_match_searched_diff = abs(ps-searched_ps)
#                 closest_match_searched = ind
#         searched_dict[num] = closest_match_searched
        
#         closest_match_cited = -1
#         closest_match_cited_diff = 1
#         for ind, ps in cited_propensity_scores:
#             if ind == num:
#                 continue
#             if abs(ps-cited_ps) < closest_match_cited_diff:
#                 closest_match_cited_diff = abs(ps-cited_ps)
#                 closest_match_cited = ind
#         cited_dict[num] = closest_match_cited
        
#         closest_match_arrested = -1
#         closest_match_arrested_diff = 1
#         for ind, ps in arrested_propensity_scores:
#             if ind == num:
#                 continue
#             if abs(ps-arrested_ps) < closest_match_arrested_diff:
#                 closest_match_arrested_diff = abs(ps-arrested_ps)
#                 closest_match_arrested= ind
#         arrested_dict[num] = closest_match_arrested
        
#     return [searched_dict,cited_dict,arrested_dict]
