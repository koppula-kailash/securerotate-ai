"""
SecureRotate AI - Enterprise Synthetic ML Dataset Generator
Generates clean, deduplicated, diverse enterprise database credential telemetry records
for AI risk classification (LOW, MEDIUM, HIGH).
"""

import csv
import os
import random
import numpy as np
import pandas as pd


def generate_dataset(num_samples=2500, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    environments = ["Development", "Staging", "Production", "Testing"]
    privilege_levels = ["LOW", "MEDIUM", "HIGH", "ADMIN"]

    rows = []
    seen = set()

    for _ in range(num_samples * 2):
        env = random.choices(environments, weights=[0.20, 0.20, 0.45, 0.15])[0]
        priv = random.choices(privilege_levels, weights=[0.25, 0.35, 0.25, 0.15])[0]
        
        # Proximity to expiry
        days_until_expiry = random.choices(
            [
                random.randint(1, 3),      # Critical proximity
                random.randint(4, 7),      # Warning proximity
                random.randint(8, 30),     # Elevated proximity
                random.randint(31, 90),    # Normal lifecycle
                random.randint(91, 180),   # Fresh credential
            ],
            weights=[0.12, 0.15, 0.23, 0.35, 0.15]
        )[0]
        
        credential_age_days = random.randint(1, 365)
        dependency_count = random.choices(
            [0, 1, 2, 3, 4, 5, 6, 7, 8],
            weights=[0.15, 0.25, 0.20, 0.15, 0.10, 0.07, 0.04, 0.02, 0.02]
        )[0]
        failures = random.choices([0, 1, 2, 3], weights=[0.80, 0.12, 0.06, 0.02])[0]
        access_freq = random.randint(5, 950)

        # Unique feature signature to ensure absolute zero duplicate records
        key = (days_until_expiry, credential_age_days, dependency_count, priv, env, failures, access_freq)
        if key in seen:
            continue
        seen.add(key)

        # Continuous risk score calculation
        score = 0.08
        if "Prod" in env:
            score += 0.30
        elif "Stag" in env:
            score += 0.14
        elif "Test" in env:
            score += 0.06

        if priv in ["HIGH", "ADMIN"]:
            score += 0.26
        elif priv == "MEDIUM":
            score += 0.12

        if days_until_expiry <= 3:
            score += 0.35
        elif days_until_expiry <= 7:
            score += 0.25
        elif days_until_expiry <= 30:
            score += 0.15

        if dependency_count >= 4:
            score += 0.15
        elif dependency_count >= 2:
            score += 0.08

        if failures > 0:
            score += 0.12 * failures

        score += float(np.random.normal(0, 0.02))

        # Risk Classification
        if score < 0.40:
            risk_level = "LOW"
        elif score < 0.68:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        rows.append({
            "days_until_expiry": days_until_expiry,
            "credential_age_days": credential_age_days,
            "dependency_count": dependency_count,
            "privilege_level": priv,
            "environment": env,
            "historical_rotation_failures": failures,
            "access_frequency_per_day": access_freq,
            "risk_level": risk_level
        })

        if len(rows) >= num_samples:
            break

    df = pd.DataFrame(rows)
    # Deduplicate strictly
    df = df.drop_duplicates().reset_index(drop=True)

    output_path = os.path.join(os.path.dirname(__file__), "dataset.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Generated {len(df)} clean deduplicated training records in {output_path}")
    print("Class breakdown:\n", df["risk_level"].value_counts())
    return df


if __name__ == "__main__":
    generate_dataset()
