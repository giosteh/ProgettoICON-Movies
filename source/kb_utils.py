import pandas as pd
import numpy as np
from pyswip import Prolog

# funzione che salva su un file i fatti
def save_to_file(strings, filename):
    with open(filename, 'a') as f:
        f.write('\n'.join(strings))


# funzione che crea la kb
def create_kb():
    df = pd.read_csv('../dataset/movies_v3.csv')
    save_to_file([":-style_check(-discontiguous).\n"], 'facts.pl')

    # fatti per i film
    facts = []
    for row in df.itertuples():
        facts.append(
            f'movie({row.id}).\n'
            f'title({row.id}, "{row.title}").\n'
            f'rating({row.id}, "{row.rating}").\n'
            f'genre({row.id}, "{row.genre}").\n'
            f'year({row.id}, {row.year}).\n'
            f'country({row.id}, "{row.country}").\n'
            f'company({row.id}, "{row.company}").\n'
            f'runtime({row.id}, {row.runtime}).\n'
            f'budget({row.id}, {row.budget}).\n'
            f'gross({row.id}, {row.gross}).\n'
            f'score({row.id}, {row.score}).\n'
            f'directed_by({row.id}, "{row.director}").\n'
            f'star({row.id}, "{row.star}").'
        )
    save_to_file(facts, 'facts.pl')

    # fatti per i registi e gli attori
    df_directors = df['director'].unique()
    df_actors = df['star'].unique()

    facts = []
    for director in df_directors:
        facts.append(f'director("{director}").')

    for actor in df_actors:
        facts.append(f'actor("{actor}").')

    save_to_file(facts, 'facts.pl')


# funzione che esegue una query safe su una kb
def query_kb(prolog_kb, query):
    result = prolog_kb.query(query)
    if result:
        return list(result)[0]['X']
    return None


# funzione che deriva il nuovo dataframe dei movies dalla kb
def derive_movies_data(df, prolog_kb, binning=False, task='regression'):
    new_data = []

    for movie_id in df['id']:
        features = {}

        features['id'] = movie_id
        features['country'] = query_kb(prolog_kb, f'country({movie_id}, X).')
        features['company'] = query_kb(prolog_kb, f'company({movie_id}, X).')
        features['rating'] = query_kb(prolog_kb, f'rating_regrouped({movie_id}, X).')
        features['genre'] = query_kb(prolog_kb, f'genre_regrouped({movie_id}, X).')
        features['director'] = query_kb(prolog_kb, f'directed_by({movie_id}, X).')
        features['star'] = query_kb(prolog_kb, f'star({movie_id}, X).')

        features['score'] = query_kb(prolog_kb, f'score({movie_id}, X).')
        features['quality'] = query_kb(prolog_kb, f'movie_score_binned({movie_id}, X).')

        features['profit_index'] = query_kb(prolog_kb, f'movie_profit_index({movie_id}, X).')
        features['profitability'] = query_kb(prolog_kb, f'movie_profit_index_binned({movie_id}, X).')

        if not binning:
            features['cult_index'] = query_kb(prolog_kb, f'movie_cult_index({movie_id}, X).')
            features['age'] = query_kb(prolog_kb, f'movie_age({movie_id}, X).')
            features['runtime'] = query_kb(prolog_kb, f'runtime({movie_id}, X).')
            features['votes'] = query_kb(prolog_kb, f'votes({movie_id}, X).')
            features['budget'] = query_kb(prolog_kb, f'budget({movie_id}, X).')
            features['gross'] = query_kb(prolog_kb, f'gross({movie_id}, X).')
        else:
            features['cult_index'] = query_kb(prolog_kb, f'movie_cult_index_binned({movie_id}, X).')
            features['age'] = query_kb(prolog_kb, f'movie_age_binned({movie_id}, X).')
            features['runtime'] = query_kb(prolog_kb, f'movie_runtime_binned({movie_id}, X).')
            features['votes'] = query_kb(prolog_kb, f'movie_votes_binned({movie_id}, X).')
            features['budget'] = query_kb(prolog_kb, f'movie_budget_binned({movie_id}, X).')
            features['gross'] = query_kb(prolog_kb, f'movie_gross_binned({movie_id}, X).')            

        new_data.append(features)
    
    return pd.DataFrame(new_data)


# funzione che deriva il nuovo dataframe dei registi dalla kb
def derive_directors_data(df, prolog_kb, binning=False):
    new_data = []

    for director in df:
        features = {}

        features['director_name'] = director

        if not binning:
            features['director_num_movies'] = query_kb(prolog_kb, f'director_num_movies("{director}", X).')
            features['director_profit_mean'] = query_kb(prolog_kb, f'director_profit_mean("{director}", X).')
            features['director_profit_std'] = query_kb(prolog_kb, f'director_profit_std("{director}", X).')
            features['director_score_mean'] = query_kb(prolog_kb, f'director_score_mean("{director}", X).')
            features['director_score_std'] = query_kb(prolog_kb, f'director_score_std("{director}", X).')
        else:
            features['director_num_movies'] = query_kb(prolog_kb, f'director_num_movies_binned("{director}", X).')
            features['director_profit_mean'] = query_kb(prolog_kb, f'director_profit_mean_binned("{director}", X).')
            features['director_profit_std'] = query_kb(prolog_kb, f'director_profit_std_binned("{director}", X).')
            features['director_score_mean'] = query_kb(prolog_kb, f'director_score_mean_binned("{director}", X).')
            features['director_score_std'] = query_kb(prolog_kb, f'director_score_std_binned("{director}", X).')

        new_data.append(features)
    
    return pd.DataFrame(new_data)


# funzione che deriva il nuovo dataframe degli attori dalla kb
def derive_actors_data(df, prolog_kb, binning=False):
    new_data = []

    for actor in df:
        features = {}

        features['actor_name'] = actor

        if not binning:
            features['actor_num_movies'] = query_kb(prolog_kb, f'actor_num_movies("{actor}", X).')
            features['actor_profit_mean'] = query_kb(prolog_kb, f'actor_profit_mean("{actor}", X).')
            features['actor_profit_std'] = query_kb(prolog_kb, f'actor_profit_std("{actor}", X).')
            features['actor_score_mean'] = query_kb(prolog_kb, f'actor_score_mean("{actor}", X).')
            features['actor_score_std'] = query_kb(prolog_kb, f'actor_score_std("{actor}", X).')
        else:
            features['actor_num_movies'] = query_kb(prolog_kb, f'actor_num_movies_binned("{actor}", X).')
            features['actor_profit_mean'] = query_kb(prolog_kb, f'actor_profit_mean_binned("{actor}", X).')
            features['actor_profit_std'] = query_kb(prolog_kb, f'actor_profit_std_binned("{actor}", X).')
            features['actor_score_mean'] = query_kb(prolog_kb, f'actor_score_mean_binned("{actor}", X).')
            features['actor_score_std'] = query_kb(prolog_kb, f'actor_score_std_binned("{actor}", X).')

        new_data.append(features)

    return pd.DataFrame(new_data)
