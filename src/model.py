import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

TRAINCOLS = [
    'county_name',
    'subject_age',
    'subject_sex',
    'violation',
    'arrest_made',
    'citation_issued',
    'search_conducted'
    ]

def data_loader(indir, traincols=TRAINCOLS):
    
    df = pd.concat([pd.read_csv(os.path.join(indir, p)[traincols].dropna(subset=traincols).reset_index(drop=True)) for p in os.listdir(indir)])

    df['subject_sex'] = df['subject_sex'].apply(lambda sex: {'female': 0, 'male': 1}.get(sex, ' '))

    bool_cols = ['arrest_made','citation_issued','search_conducted']

    for col in bool_cols:
        df[col] = df[col].apply(lambda x: 1 if x else 0)

    df = pd.get_dummies(df,prefix=['county','violation'], columns=['county_name','violation'])

     # probabiltiy searched 
    X = fl_ohe.drop(['arrest_made','citation_issued','search_conducted'],axis=1)
    y = fl_ohe['search_conducted']
    lr = train_model(X, y)
    probs_searched = [x[1] for x in lr.predict_proba(X)]

    # probabiltiy cited 
    X = fl_ohe.drop(['arrest_made','citation_issued'],axis=1)
    y = fl_ohe['citation_issued']
    lr = train_model(X, y)
    probs_cited = [x[1] for x in lr.predict_proba(X)]

    # probabiltiy arrested 
    X = fl_ohe.drop(['arrest_made','citation_issued'],axis=1)
    y = fl_ohe['arrest_made']
    lr = train_model(X, y)
    probs_arrested = [x[1] for x in lr.predict_proba(X)]

    return list(zip(probs_searched,probs_cited,probs_arrested))


def train_model(X, y, outdir=None):

    lr = LogisticRegression(n_jobs=1, solver='liblinear')
    lr.fit(X, y)

    return lr


def driver(indir, outdir=None):

    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)

    propensity_scores = data_loader(indir)

    return propensity_scores


def propensity_matching(propensity_scores):
    
    """
    Matches traffic stops based on their respective searched, cited and arrested propensity scores.
    Returns a list of dictionaries that indicate the indicies of the matches as follows:
        [searched matches, cited matches, arrested matches]
    A return dictionary entry example for searched matches is:
        {1:124} (indicates that the stop at the 1st index has a searched propensity score closest to 124)
    """
    
    searched_dict = {}
    cited_dict = {}
    arrested_dict = {}
    searched_propensity_scores = [(num,s[0]) for num,s in enumerate(propensity_scores)]
    cited_propensity_scores = [(num,s[1]) for num,s in enumerate(propensity_scores)]
    arrested_propensity_scores = [(num,s[2]) for num,s in enumerate(propensity_scores)]
    
    for num, scores in enumerate(propensity_scores):
        searched_ps, cited_ps, arrested_ps = scores
        
        closest_match_searched = -1
        closest_match_searched_diff = 1
        for ind, ps in searched_propensity_scores:
            if ind == num:
                continue
            if abs(ps-searched_ps) < closest_match_searched_diff:
                closest_match_searched_diff = abs(ps-searched_ps)
                closest_match_searched = ind
        searched_dict[num] = closest_match_searched
        
        closest_match_cited = -1
        closest_match_cited_diff = 1
        for ind, ps in cited_propensity_scores:
            if ind == num:
                continue
            if abs(ps-cited_ps) < closest_match_cited_diff:
                closest_match_cited_diff = abs(ps-cited_ps)
                closest_match_cited = ind
        cited_dict[num] = closest_match_cited
        
        closest_match_arrested = -1
        closest_match_arrested_diff = 1
        for ind, ps in arrested_propensity_scores:
            if ind == num:
                continue
            if abs(ps-arrested_ps) < closest_match_arrested_diff:
                closest_match_arrested_diff = abs(ps-arrested_ps)
                closest_match_arrested= ind
        arrested_dict[num] = closest_match_arrested
        
    return [searched_dict,cited_dict,arrested_dict]