# --- IMPORTS ---
import pickle
import bz2
import streamlit as st
import requests
import pandas as pd
import numpy as np

# Must be the very first Streamlit command
st.set_page_config(page_title="Movie Recommender", layout="wide", page_icon="🍿")


# =====================================================================
# SHARED UTILITY FUNCTIONS
# =====================================================================
def fetch_poster(tmdb_id):
    """Fetches the movie poster from the TMDB API using the TMDB ID."""
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=60daa24e491126aa234b2642f60eebd5&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except Exception:
        pass
    return "https://via.placeholder.com/500x750?text=No+Image+Found"


def display_movie_grid(recommendations_df, items_per_row=5):
    """Displays movie posters and titles in a neat, cinematic grid."""
    st.write("")  # Small padding at the top

    for i in range(0, len(recommendations_df), items_per_row):
        cols = st.columns(items_per_row, gap="large")
        row_recs = recommendations_df.iloc[i:i + items_per_row]

        for j in range(len(row_recs)):
            with cols[j]:
                title = row_recs.iloc[j]['title']
                tmdb_id = row_recs.iloc[j]['tmdbId']

                if pd.notna(tmdb_id):
                    st.image(fetch_poster(int(tmdb_id)), use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/500x750?text=No+Image+Found", use_container_width=True)

                st.markdown(f"<h6 style='text-align: center; color: #E0E0E0; margin-top: 5px;'>{title}</h6>",
                            unsafe_allow_html=True)

        st.write("")  # Extra padding between rows


# =====================================================================
# LOAD ALL DATA
# =====================================================================
@st.cache_resource
def load_all_data():
    """Loads all models into memory at startup."""
    # Content-Based Data
    cbf_movies = pickle.load(open('models/content-based-models/movie_list.pkl', 'rb'))
    with bz2.BZ2File('models/content-based-models/similarity.pkl.bz2', 'rb') as f:
        cbf_similarity = pickle.load(f)

    # User-Based Data
    user_item_matrix = pickle.load(open('models/user-based-models/user_item_matrix.pkl', 'rb'))
    user_item_matrix_norm = pickle.load(open('models/user-based-models/user_item_matrix_norm.pkl', 'rb'))
    user_means = pickle.load(open('models/user-based-models/user_means.pkl', 'rb'))
    user_similarity_df = pickle.load(open('models/user-based-models/user_similarity.pkl', 'rb'))
    ubcf_movies_df = pickle.load(open('models/user-based-models/ubcf_movies.pkl', 'rb'))

    return cbf_movies, cbf_similarity, user_item_matrix, user_item_matrix_norm, user_means, user_similarity_df, ubcf_movies_df


# =====================================================================
# RECOMMENDATION ENGINE FUNCTIONS
# =====================================================================
def get_cbf_recommendations(movie_name, movies_df, similarity_matrix, num_recs=10):
    movie_index = movies_df[movies_df['title'] == movie_name].index[0]
    distances = sorted(list(enumerate(similarity_matrix[movie_index])), reverse=True, key=lambda x: x[1])[
        1:num_recs + 1]
    return [movies_df.iloc[i[0]].movie_id for i in distances]


def get_ubcf_predicted_ratings(target_user_id, user_movie_matrix, user_movie_matrix_norm, user_means,
                               user_similarity_df):
    target_mean = user_means[target_user_id]
    target_user_movies = user_movie_matrix.loc[target_user_id].dropna().index

    similar_users = user_similarity_df[target_user_id].sort_values(ascending=False)[1:16]
    similar_users = similar_users[similar_users > 0]

    if similar_users.empty:
        return pd.Series()

    neighbors_norm_ratings = user_movie_matrix_norm.loc[similar_users.index].drop(columns=target_user_movies,
                                                                                  errors='ignore')
    neighbors_raw_ratings = user_movie_matrix.loc[similar_users.index].drop(columns=target_user_movies, errors='ignore')
    weights = similar_users.values

    weighted_norm_ratings = neighbors_norm_ratings.fillna(0).multiply(weights, axis=0).sum(axis=0)
    sum_of_weights = neighbors_raw_ratings.notna().multiply(weights, axis=0).sum(axis=0)

    predicted_ratings = target_mean + (weighted_norm_ratings / sum_of_weights.replace(0, np.nan))
    return predicted_ratings.dropna()


def get_hybrid_recommendations(target_user_id, num_recs=10):
    user_ratings = user_item_matrix.loc[target_user_id].dropna().sort_values(ascending=False)

    seed_tmdb_id = None
    seed_movie_title = None

    for ml_movie_id in user_ratings.index:
        tmdb_lookup = ubcf_movies_df[ubcf_movies_df['movieId'] == ml_movie_id]['tmdbId']
        if not tmdb_lookup.empty and pd.notna(tmdb_lookup.values[0]):
            tmdb_id = int(tmdb_lookup.values[0])
            if tmdb_id in cbf_movies['movie_id'].values:
                seed_tmdb_id = tmdb_id
                seed_movie_title = cbf_movies[cbf_movies['movie_id'] == tmdb_id]['title'].values[0]
                break

    if not seed_movie_title:
        return None, "Could not find a valid anchor movie for this user."

    candidate_tmdb_ids = get_cbf_recommendations(seed_movie_title, cbf_movies, cbf_similarity, num_recs=100)
    candidate_ml_ids = ubcf_movies_df[ubcf_movies_df['tmdbId'].isin(candidate_tmdb_ids)]['movieId'].tolist()

    cf_predictions = get_ubcf_predicted_ratings(target_user_id, user_item_matrix, user_item_matrix_norm, user_means,
                                                user_similarity_df)

    if cf_predictions.empty:
        return None, "Not enough similar users to confidently re-rank the hybrid list."

    hybrid_scores = cf_predictions[cf_predictions.index.isin(candidate_ml_ids)]
    top_hybrid_ml_ids = hybrid_scores.sort_values(ascending=False).head(num_recs).index

    recommendations = ubcf_movies_df.set_index('movieId').loc[top_hybrid_ml_ids].reset_index()
    return recommendations, seed_movie_title


# =====================================================================
# STREAMLIT USER INTERFACE WITH SIDEBAR NAVIGATION
# =====================================================================
try:
    cbf_movies, cbf_similarity, user_item_matrix, user_item_matrix_norm, user_means, user_similarity_df, ubcf_movies_df = load_all_data()
    data_loaded = True
except FileNotFoundError:
    data_loaded = False

st.sidebar.title("🍿 Navigation")
st.sidebar.write("Choose your recommendation engine:")
app_mode = st.sidebar.radio(
    "Select System:",
    ["Content-Based (Similar Movies)", "User-Based (Similar Tastes)", "Hybrid (Best of Both Worlds)"],
    label_visibility="collapsed"
)

st.sidebar.divider()
if not data_loaded:
    st.sidebar.error("Error loading models. Check your folders.")
else:
    st.sidebar.success("All models loaded successfully!")

# --- Common options for the dropdown ---
rec_options = [5, 10, 15, 20]
rec_default_index = 1  # Defaults to 10

# --- Main Page Routing ---
if not data_loaded:
    st.error("⚠️ Missing model files. Please run your Jupyter Notebooks to generate all .pkl files.")

elif app_mode == "Content-Based (Similar Movies)":
    st.title("🎥 Content-Based Recommender")
    st.markdown("Select a movie you love, and we'll recommend similar movies based on plot, cast, and tags.")

    # UI UPGRADE: 3 Columns [4, 1, 1]
    col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="bottom")
    with col1:
        selected_movie = st.selectbox("Select a movie:", cbf_movies['title'].values)
    with col2:
        num_recs = st.selectbox("Results:", rec_options, index=rec_default_index)
    with col3:
        submit = st.button('Search', type="primary", use_container_width=True)

    if submit:
        st.divider()
        with st.spinner('Finding matches...'):
            tmdb_ids = get_cbf_recommendations(selected_movie, cbf_movies, cbf_similarity, num_recs=num_recs)

            recs_df = pd.DataFrame({'tmdbId': tmdb_ids})
            recs_df['title'] = recs_df['tmdbId'].apply(
                lambda x: cbf_movies[cbf_movies['movie_id'] == x]['title'].values[0])

            display_movie_grid(recs_df, items_per_row=5)

elif app_mode == "User-Based (Similar Tastes)":
    st.title("👥 User-Based Recommender")
    st.markdown("Select a User ID. We will find people with the exact same tastes and recommend their favorites.")

    valid_users = user_similarity_df.index.tolist()

    # UI UPGRADE: 3 Columns [4, 1, 1]
    col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="bottom")
    with col1:
        selected_user = st.selectbox("Select a User ID:", valid_users)
    with col2:
        num_recs = st.selectbox("Results:", rec_options, index=rec_default_index)
    with col3:
        submit = st.button("Generate", type="primary", use_container_width=True)

    if submit:
        st.divider()
        with st.spinner('Calculating user tastes...'):
            predictions = get_ubcf_predicted_ratings(selected_user, user_item_matrix, user_item_matrix_norm, user_means,
                                                     user_similarity_df)

            if not predictions.empty:
                st.success(f"Top {num_recs} Picks for User {selected_user}:")
                # Dynamically limit to num_recs
                top_ml_ids = predictions.sort_values(ascending=False).head(num_recs).index
                recs = ubcf_movies_df.set_index('movieId').loc[top_ml_ids].reset_index()

                display_movie_grid(recs, items_per_row=5)
            else:
                st.warning("Could not generate confident recommendations for this user.")

elif app_mode == "Hybrid (Best of Both Worlds)":
    st.title("🧬 Hybrid Recommender")
    st.markdown("We find the user's favorite genre, then filter those movies by what their 'taste twins' highly rate.")

    valid_users = user_similarity_df.index.tolist()

    # UI UPGRADE: 3 Columns [4, 1, 1]
    col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="bottom")
    with col1:
        selected_user = st.selectbox("Select a User ID:", valid_users)
    with col2:
        num_recs = st.selectbox("Results:", rec_options, index=rec_default_index)
    with col3:
        submit = st.button("Generate", type="primary", use_container_width=True)

    if submit:
        st.divider()
        with st.spinner('Fusing Content and Collaborative models...'):
            recs, anchor_movie = get_hybrid_recommendations(selected_user, num_recs=num_recs)

            if recs is not None and not recs.empty:
                st.success(f"Because User {selected_user} loved **{anchor_movie}**, their taste twins recommend:")
                display_movie_grid(recs, items_per_row=5)
            else:
                st.warning(anchor_movie)