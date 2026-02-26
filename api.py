from fastapi import FastAPI, HTTPException
import pickle
import bz2
import requests
import pandas as pd
import numpy as np


# Initialize the API
app = FastAPI(title="Movie Recommender API")

# =====================================================================
# LOAD ALL DATA (Runs once when the server starts)
# =====================================================================
try:
    cbf_movies = pickle.load(open('models/content-based-models/movie_list.pkl', 'rb'))
    with bz2.BZ2File('models/content-based-models/similarity.pkl.bz2', 'rb') as f:
        cbf_similarity = pickle.load(f)

    user_item_matrix = pickle.load(open('models/user-based-models/user_item_matrix.pkl', 'rb'))
    user_item_matrix_norm = pickle.load(open('models/user-based-models/user_item_matrix_norm.pkl', 'rb'))
    user_means = pickle.load(open('models/user-based-models/user_means.pkl', 'rb'))
    user_similarity_df = pickle.load(open('models/user-based-models/user_similarity.pkl', 'rb'))
    ubcf_movies_df = pickle.load(open('models/user-based-models/ubcf_movies.pkl', 'rb'))
except FileNotFoundError:
    print("Error: Model files not found. Check your 'models/' directory.")


# =====================================================================
# SHARED UTILITY
# =====================================================================
def fetch_poster(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=60daa24e491126aa234b2642f60eebd5&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except Exception:
        pass
    return "https://via.placeholder.com/500x750?text=No+Image+Found"


# =====================================================================
# API ENDPOINTS (What the Android App will "call")
# =====================================================================

@app.get("/recommend/content")
def recommend_content(movie_title: str, num_recs: int = 10):
    """Android app asks for similar movies by title."""
    if movie_title not in cbf_movies['title'].values:
        raise HTTPException(status_code=404, detail="Movie not found in database")

    movie_index = cbf_movies[cbf_movies['title'] == movie_title].index[0]
    distances = sorted(list(enumerate(cbf_similarity[movie_index])), reverse=True, key=lambda x: x[1])[1:num_recs + 1]

    results = []
    for i in distances:
        tmdb_id = int(cbf_movies.iloc[i[0]].movie_id)
        title = str(cbf_movies.iloc[i[0]].title)
        results.append({
            "title": title,
            "tmdb_id": tmdb_id,
            "poster_url": fetch_poster(tmdb_id)
        })

    return {"anchor_movie": movie_title, "recommendations": results}


@app.get("/recommend/hybrid")
def recommend_hybrid(user_id: int, num_recs: int = 10):
    """Android app asks for hybrid recommendations for a specific user."""
    if user_id not in user_similarity_df.index:
        raise HTTPException(status_code=404, detail="User ID not found")

    # 1. Find the User's highest rated movie
    user_ratings = user_item_matrix.loc[user_id].dropna().sort_values(ascending=False)
    seed_tmdb_id = None
    seed_movie_title = None

    for ml_movie_id in user_ratings.index:
        tmdb_lookup = ubcf_movies_df[ubcf_movies_df['movieId'] == ml_movie_id]['tmdbId']
        if not tmdb_lookup.empty and pd.notna(tmdb_lookup.values[0]):
            tmdb_id = int(tmdb_lookup.values[0])
            if tmdb_id in cbf_movies['movie_id'].values:
                seed_movie_title = cbf_movies[cbf_movies['movie_id'] == tmdb_id]['title'].values[0]
                break

    if not seed_movie_title:
        raise HTTPException(status_code=400, detail="Could not find a valid anchor movie for this user.")

    # 2. Get Candidates (Content)
    movie_index = cbf_movies[cbf_movies['title'] == seed_movie_title].index[0]
    distances = sorted(list(enumerate(cbf_similarity[movie_index])), reverse=True, key=lambda x: x[1])[1:100]
    candidate_tmdb_ids = [cbf_movies.iloc[i[0]].movie_id for i in distances]
    candidate_ml_ids = ubcf_movies_df[ubcf_movies_df['tmdbId'].isin(candidate_tmdb_ids)]['movieId'].tolist()

    # 3. Predict Ratings (Collaborative)
    target_mean = user_means[user_id]
    target_user_movies = user_item_matrix.loc[user_id].dropna().index
    similar_users = user_similarity_df[user_id].sort_values(ascending=False)[1:16]
    similar_users = similar_users[similar_users > 0]

    if similar_users.empty:
        raise HTTPException(status_code=400, detail="Not enough similar users.")

    neighbors_norm_ratings = user_item_matrix_norm.loc[similar_users.index].drop(columns=target_user_movies,
                                                                                 errors='ignore')
    neighbors_raw_ratings = user_item_matrix.loc[similar_users.index].drop(columns=target_user_movies, errors='ignore')
    weights = similar_users.values

    weighted_norm_ratings = neighbors_norm_ratings.fillna(0).multiply(weights, axis=0).sum(axis=0)
    sum_of_weights = neighbors_raw_ratings.notna().multiply(weights, axis=0).sum(axis=0)
    cf_predictions = (target_mean + (weighted_norm_ratings / sum_of_weights.replace(0, np.nan))).dropna()

    # 4. Filter and Format Output
    hybrid_scores = cf_predictions[cf_predictions.index.isin(candidate_ml_ids)]
    top_hybrid_ml_ids = hybrid_scores.sort_values(ascending=False).head(num_recs).index
    recs = ubcf_movies_df.set_index('movieId').loc[top_hybrid_ml_ids].reset_index()

    results = []
    for _, row in recs.iterrows():
        tmdb_id = int(row['tmdbId']) if pd.notna(row['tmdbId']) else None
        results.append({
            "title": str(row['title']),
            "tmdb_id": tmdb_id,
            "poster_url": fetch_poster(
                tmdb_id) if tmdb_id else "https://via.placeholder.com/500x750?text=No+Image+Found"
        })

    return {"anchor_movie": seed_movie_title, "recommendations": results}


# =====================================================================
# UI
# =====================================================================
@app.get("/")
def read_root():
    return {"message": "Welcome to the Movie Recommender API! Go to /docs to test it."}


# =====================================================================