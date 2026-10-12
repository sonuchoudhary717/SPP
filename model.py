import pandas as pd
import pickle
import warnings

from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ==========================================
# 1. PROJECT SETTINGS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "student_data.csv"
MODEL_PATH = BASE_DIR / "model.pkl"

FEATURES = [
    "study_hours",
    "attendance",
    "previous_marks",
    "assignments"
]

TARGET = "final_score"


# ==========================================
# 2. LOAD DATASET
# ==========================================

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

data = pd.read_csv(DATA_PATH)

print("\n========== STUDENT PERFORMANCE MODEL ==========")
print("Original dataset shape:", data.shape)

required_columns = FEATURES + [TARGET]

missing_columns = [
    column for column in required_columns
    if column not in data.columns
]

if missing_columns:
    raise ValueError(
        f"Missing CSV columns: {missing_columns}"
    )

data = data[required_columns].copy()


# ==========================================
# 3. DATA CLEANING
# ==========================================

# Convert all model columns to numeric values.
for column in required_columns:
    data[column] = pd.to_numeric(
        data[column], errors="coerce"
    )

# Remove missing and duplicate rows.
before_cleaning = len(data)

data = data.dropna()
data = data.drop_duplicates().reset_index(drop=True)

print("Rows removed during cleaning:",
      before_cleaning - len(data))

# Validate ranges.
invalid_rows = (
    (data["study_hours"] < 0)
    | (data["attendance"] < 0)
    | (data["attendance"] > 100)
    | (data["previous_marks"] < 0)
    | (data["previous_marks"] > 100)
    | (data["assignments"] < 0)
    | (data["final_score"] < 0)
    | (data["final_score"] > 100)
)

if invalid_rows.any():
    raise ValueError(
        "Dataset contains invalid values. "
        "Check study_hours, attendance, marks, "
        "assignments and final_score ranges."
    )

if len(data) < 5:
    raise ValueError(
        "At least 5 valid rows are required "
        "for this train/test split."
    )

print("Clean dataset shape:", data.shape)


# ==========================================
# 4. FEATURES AND TARGET
# ==========================================

X = data[FEATURES]
y = data[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# ==========================================
# 5. DEFINE CANDIDATE MODELS
# ==========================================

models = {
    "Linear Regression": LinearRegression(),

    "Random Forest": RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        random_state=42
    )
}


# ==========================================
# 6. COMPARE MODELS USING CROSS-VALIDATION
# ==========================================

cv_folds = min(5, len(X_train))

if cv_folds < 2:
    raise ValueError(
        "Not enough training records for "
        "cross-validation. Add more valid data."
    )

best_name = None
best_model = None
best_cv_mae = float("inf")

print("\n========== MODEL COMPARISON ==========")

for name, candidate in models.items():

    scores = cross_val_score(
        candidate,
        X_train,
        y_train,
        cv=cv_folds,
        scoring="neg_mean_absolute_error"
    )

    cv_mae = -scores.mean()

    print(f"{name} CV MAE: {cv_mae:.2f}")

    if cv_mae < best_cv_mae:
        best_cv_mae = cv_mae
        best_name = name
        best_model = candidate


# ==========================================
# 7. TRAIN SELECTED MODEL
# ==========================================

best_model.fit(X_train, y_train)

predictions = best_model.predict(X_test)

# Predictions outside the valid score range
# are reported, not silently hidden.
if (
    (predictions < 0).any()
    or (predictions > 100).any()
):
    warnings.warn(
        "Some predicted scores are outside 0-100. "
        "Review model quality and input data."
    )


# ==========================================
# 8. MODEL EVALUATION
# ==========================================

mae = mean_absolute_error(y_test, predictions)
mse = mean_squared_error(y_test, predictions)
rmse = mse ** 0.5
r2 = r2_score(y_test, predictions)

print("\n========== FINAL EVALUATION ==========")
print("Selected model:", best_name)
print(f"Test MAE:  {mae:.2f}")
print(f"Test RMSE: {rmse:.2f}")
print(f"Test R2:   {r2:.3f}")

print(
    "\nNote: R2 is not prediction accuracy "
    "as a percentage."
)


# ==========================================
# 9. SAVE MODEL
# ==========================================

# Save the model object directly so the existing
# app.py can continue using model.predict(X).
with open(MODEL_PATH, "wb") as file:
    pickle.dump(best_model, file)

print("\nModel saved successfully!")
print("Model file:", MODEL_PATH)
print("Input features:", FEATURES)
print("================================================")