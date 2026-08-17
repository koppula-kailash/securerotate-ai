"""
SecureRotate AI - Feature Preprocessing Pipeline
Defines scikit-learn ColumnTransformer for categorical and numerical features.
"""

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL_FEATURES = ["privilege_level", "environment"]
NUMERICAL_FEATURES = [
    "days_until_expiry",
    "credential_age_days",
    "dependency_count",
    "historical_rotation_failures",
    "access_frequency_per_day",
]


def build_preprocessor() -> ColumnTransformer:
    """Builds a scikit-learn ColumnTransformer for preprocessing input features."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            (
                "num",
                StandardScaler(),
                NUMERICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )
    return preprocessor
