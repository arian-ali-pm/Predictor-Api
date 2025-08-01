# File: api/index.py

from flask import Flask, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# --- Configuration ---
# Get the directory of the current script to build a reliable file path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(BASE_DIR, 'sport_survey_data.csv')

# Load the data into memory when the app starts
try:
    SURVEY_DF = pd.read_csv(CSV_FILE_PATH)
    print("Survey data loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load survey data. {e}")
    SURVEY_DF = None

# Column names from your CSV
COL_SPORT = 'In your opinion, which sport is Australia’s national sport?'
COL_AGE = 'Age'
COL_GENDER = 'Gender'
COL_STATE = 'State'
COL_EDUCATION = 'Education'

# --- API Endpoint ---
@app.route('/api/predict', methods=['POST'])
def predict_sport():
    if SURVEY_DF is None:
        return jsonify({"error": "Server error: Data not loaded"}), 500

    # Get user data from the request
    data = request.json
    try:
        age = int(data['age'])
        gender = data['gender']
        state = data['state']
        education = data['education']
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid input data"}), 400

    # --- The same powerful filtering logic as before ---
    df = SURVEY_DF.copy()
    df['Age Group'] = pd.cut(df[COL_AGE], bins=[17, 24, 34, 44, 54, 64, 120],
                             labels=['18-24', '25-34', '35-44', '45-54', '55-64', '65+'])
    user_age_group = next((label for i, label in enumerate(df['Age Group'].cat.categories)
                           if df['Age Group'].cat.categories.left[i] < age <= df['Age Group'].cat.categories.right[i]), None)

    filters = [
        (df[COL_GENDER] == gender) & (df[COL_STATE] == state) & (df['Age Group'] == user_age_group) & (df[COL_EDUCATION] == education),
        (df[COL_GENDER] == gender) & (df[COL_STATE] == state) & (df['Age Group'] == user_age_group),
        (df[COL_GENDER] == gender) & (df[COL_STATE] == state),
        (df[COL_STATE] == state),
        (df[COL_GENDER] == gender) & (df['Age Group'] == user_age_group),
        pd.Series(True, index=df.index)
    ]

    filtered_df = pd.DataFrame()
    for f in filters:
        cohort = df[f]
        if len(cohort) >= 10:
            filtered_df = cohort
            break
    if filtered_df.empty:
      for f in filters:
        cohort = df[f]
        if len(cohort) > 0:
            filtered_df = cohort
            break

    if filtered_df.empty:
        return jsonify({"sport": "Not enough data", "probability": 0})

    sport_counts = filtered_df[COL_SPORT].value_counts()
    probabilities = (sport_counts / sport_counts.sum()) * 100

    # Find the top sport and its probability
    top_sport = probabilities.idxmax()
    top_prob = round(probabilities.max())

    # Return the result as JSON
    return jsonify({
        "sport": top_sport,
        "probability": top_prob
    })
