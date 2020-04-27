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