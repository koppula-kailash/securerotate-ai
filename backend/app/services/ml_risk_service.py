"""
SecureRotate AI - AI/ML Risk Prediction Service

Final risk engine for SecureRotate.

Design:
    - RandomForest ML model is used as an intelligence signal.
    - Deterministic security scoring controls the final business risk.
    - Expiry proximity is the strongest risk factor.
    - Production and privileged credentials increase risk.
    - Dependencies and historical failures add operational risk.
    - CRITICAL is reserved for genuinely urgent credentials.
    - Credentials with long expiry periods cannot become CRITICAL
      merely because they are Production + ADMIN.
    - Human-readable explanations and recommendations are generated.

Risk levels:
    LOW      : 0.00 - 0.39
    MEDIUM   : 0.40 - 0.59
    HIGH     : 0.60 - 0.79
    CRITICAL : 0.80 - 1.00
"""

import os
from typing import Dict, Any, List

import joblib
import pandas as pd


_MODEL = None


# ============================================================================
# MODEL LOADING
# ============================================================================

def load_risk_model():
    """
    Lazy-load the trained RandomForest model.
    """

    global _MODEL

    if _MODEL is None:

        model_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "ml",
            "models",
            "risk_model.pkl",
        )

        model_path = os.path.abspath(model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Trained risk model binary not found at {model_path}"
            )

        _MODEL = joblib.load(model_path)

    return _MODEL


# ============================================================================
# EXPIRY RISK
# ============================================================================

def calculate_expiry_risk(days_until_expiry: int) -> float:
    """
    Calculate expiry-related risk.

    Expiry is the strongest factor in the final risk calculation.

    <= 0 days  -> 1.00
    1-3 days   -> 0.95
    4-7 days   -> 0.80
    8-14 days  -> 0.65
    15-30 days -> 0.45
    31-60 days -> 0.25
    61-90 days -> 0.10
    > 90 days  -> 0.05
    """

    days = int(days_until_expiry)

    if days <= 0:
        return 1.00

    if days <= 3:
        return 0.95

    if days <= 7:
        return 0.80

    if days <= 14:
        return 0.65

    if days <= 30:
        return 0.45

    if days <= 60:
        return 0.25

    if days <= 90:
        return 0.10

    return 0.05


# ============================================================================
# PRIVILEGE RISK
# ============================================================================

def calculate_privilege_risk(privilege_level: str) -> float:
    """
    Calculate privilege-related risk.
    """

    privilege = (privilege_level or "").strip().upper()

    if privilege in {"ROOT", "SUPERUSER"}:
        return 1.00

    if privilege == "ADMIN":
        return 0.85

    if privilege == "HIGH":
        return 0.65

    if privilege == "MEDIUM":
        return 0.40

    if privilege == "LOW":
        return 0.15

    return 0.30


# ============================================================================
# ENVIRONMENT RISK
# ============================================================================

def calculate_environment_risk(environment: str) -> float:
    """
    Calculate environment-related risk.
    """

    env = (environment or "").strip().upper()

    if "PROD" in env:
        return 0.85

    if env in {"STAGING", "STAGE", "QA"}:
        return 0.45

    if env in {"TEST", "DEVELOPMENT", "DEV", "LOCAL"}:
        return 0.15

    return 0.30


# ============================================================================
# DEPENDENCY RISK
# ============================================================================

def calculate_dependency_risk(dependency_count: int) -> float:
    """
    Calculate operational dependency risk.
    """

    count = max(0, int(dependency_count))

    if count >= 10:
        return 0.90

    if count >= 5:
        return 0.70

    if count >= 3:
        return 0.50

    if count >= 1:
        return 0.30

    return 0.05


# ============================================================================
# HISTORICAL FAILURE RISK
# ============================================================================

def calculate_failure_risk(historical_failures: int) -> float:
    """
    Calculate risk caused by previous failed rotations.
    """

    failures = max(0, int(historical_failures))

    if failures >= 5:
        return 1.00

    if failures >= 3:
        return 0.80

    if failures == 2:
        return 0.60

    if failures == 1:
        return 0.40

    return 0.05


# ============================================================================
# ML RISK SIGNAL
# ============================================================================

def calculate_ml_risk_signal(probabilities: Dict[str, float]) -> float:
    """
    Convert RandomForest probabilities into a continuous ML risk signal.

    LOW      -> 0.15
    MEDIUM   -> 0.45
    HIGH     -> 0.75
    CRITICAL -> 1.00
    """

    low = probabilities.get("LOW", 0.0)
    medium = probabilities.get("MEDIUM", 0.0)
    high = probabilities.get("HIGH", 0.0)
    critical = probabilities.get("CRITICAL", 0.0)

    score = (
        low * 0.15
        + medium * 0.45
        + high * 0.75
        + critical * 1.00
    )

    return max(0.0, min(1.0, score))


# ============================================================================
# FINAL BUSINESS RISK SCORE
# ============================================================================

def calculate_final_risk_score(
    days_until_expiry: int,
    privilege_level: str,
    environment: str,
    dependency_count: int,
    historical_failures: int,
    ml_risk_signal: float,
) -> float:
    """
    Calculate the final risk score.

    Weight distribution:

        Expiry             45%
        Privilege          20%
        Environment        15%
        Dependencies       10%
        Historical failure  5%
        ML signal            5%

    Expiry intentionally has the strongest influence.

    This prevents situations such as:

        Production + ADMIN + 89 days remaining
        ->
        CRITICAL

    simply because the ML model predicts HIGH.
    """

    expiry_risk = calculate_expiry_risk(days_until_expiry)
    privilege_risk = calculate_privilege_risk(privilege_level)
    environment_risk = calculate_environment_risk(environment)
    dependency_risk = calculate_dependency_risk(dependency_count)
    failure_risk = calculate_failure_risk(historical_failures)

    # Main deterministic score.
    deterministic_score = (
        expiry_risk * 0.45
        + privilege_risk * 0.20
        + environment_risk * 0.15
        + dependency_risk * 0.10
        + failure_risk * 0.05
    )

    # ML contributes only 5%.
    final_score = (
        deterministic_score * 0.95
        + ml_risk_signal * 0.05
    )

    return round(
        max(0.0, min(1.0, final_score)),
        2
    )


# ============================================================================
# RISK LEVEL
# ============================================================================

def classify_risk_level(
    risk_score: float,
    days_until_expiry: int,
    environment: str,
    privilege_level: str,
) -> str:
    """
    Convert final risk score into LOW/MEDIUM/HIGH/CRITICAL.

    Additional business rules ensure that CRITICAL is reserved for
    genuinely urgent situations.
    """

    score = float(risk_score)
    days = int(days_until_expiry)

    env = (environment or "").strip().upper()
    privilege = (privilege_level or "").strip().upper()

    is_prod = "PROD" in env
    is_privileged = privilege in {
        "ADMIN",
        "SUPERUSER",
        "ROOT",
        "HIGH",
    }

    # ------------------------------------------------------------------
    # CRITICAL (Strictly <= 3 days or expired)
    # ------------------------------------------------------------------
    #
    # Critical should exclusively mean:
    # - expired (<= 0 days)
    # - expires within 3 days AND has meaningful security/operational exposure
    #
    if days <= 0:
        return "CRITICAL"

    if days <= 3 and is_prod and is_privileged and score >= 0.70:
        return "CRITICAL"

    if days <= 3 and score >= 0.85:
        return "CRITICAL"

    # Credentials with > 3 days CANNOT be CRITICAL.

    # ------------------------------------------------------------------
    # HIGH (4 to 7 days, or <= 30 days with strong risk factors)
    # ------------------------------------------------------------------
    if days <= 7 and score >= 0.55:
        return "HIGH"

    if days <= 30 and score >= 0.65 and is_prod:
        return "HIGH"

    # ------------------------------------------------------------------
    # MEDIUM & LOW (For credentials with > 30 days / > 50 days)
    # ------------------------------------------------------------------
    if days > 30:
        if days > 60:
            if score >= 0.45 and is_prod and is_privileged:
                return "MEDIUM"
            return "LOW"
        else:
            # 31 to 60 days
            if score >= 0.40:
                return "MEDIUM"
            return "LOW"

    if score >= 0.40:
        return "MEDIUM"

    return "LOW"


# ============================================================================
# HUMAN-READABLE REASONS
# ============================================================================

def generate_risk_reasons(
    days_until_expiry: int,
    environment: str,
    privilege_level: str,
    dependency_count: int,
    historical_failures: int = 0,
) -> List[str]:

    reasons: List[str] = []

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    if days_until_expiry <= 0:

        reasons.append(
            "Credential has expired or is already past its expiry date."
        )

    elif days_until_expiry <= 3:

        reasons.append(
            f"Credential expires within {days_until_expiry} day(s)."
        )

    elif days_until_expiry <= 7:

        reasons.append(
            "Credential expires within 7 days."
        )

    elif days_until_expiry <= 14:

        reasons.append(
            "Credential expires within 14 days."
        )

    elif days_until_expiry <= 30:

        reasons.append(
            "Credential expires within 30 days."
        )

    elif days_until_expiry <= 60:

        reasons.append(
            "Credential expires within 60 days."
        )

    elif days_until_expiry <= 90:

        reasons.append(
            f"Credential has {days_until_expiry} days remaining; "
            "expiry is not imminent."
        )

    else:

        reasons.append(
            f"Credential has {days_until_expiry} days remaining before expiry."
        )

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    env_upper = (environment or "").strip().upper()

    if "PROD" in env_upper:

        reasons.append(
            "Credential belongs to a production database."
        )

    # ------------------------------------------------------------------
    # Privilege
    # ------------------------------------------------------------------

    priv_upper = (privilege_level or "").strip().upper()

    if priv_upper in {
        "HIGH",
        "ADMIN",
        "SUPERUSER",
        "ROOT",
    }:

        reasons.append(
            "Credential has elevated privileges."
        )

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    if dependency_count >= 3:

        reasons.append(
            f"Credential is used by multiple downstream services "
            f"({dependency_count} services)."
        )

    elif dependency_count > 0:

        reasons.append(
            f"Credential is used by "
            f"{dependency_count} downstream service(s)."
        )

    # ------------------------------------------------------------------
    # Historical failures
    # ------------------------------------------------------------------

    if historical_failures > 0:

        reasons.append(
            f"Previous rotation failures detected "
            f"({historical_failures} failure(s))."
        )

    if not reasons:

        reasons.append(
            "Credential parameters are within normal security thresholds."
        )

    return reasons


# ============================================================================
# RECOMMENDATION
# ============================================================================

def derive_recommendation(risk_level: str) -> str:

    level = (risk_level or "").strip().upper()

    if level == "CRITICAL":
        return "ROTATE_WITHIN_24_HOURS"

    if level == "HIGH":
        return "SCHEDULE_ROTATION"

    if level == "MEDIUM":
        return "NOTIFY_OWNER"

    return "MONITOR"


# ============================================================================
# RECOMMENDATION TEXT
# ============================================================================

def generate_recommendation_text(
    credential_name: str,
    risk_level: str,
    risk_score: float,
    days_until_expiry: int,
    environment: str,
    dependency_count: int,
    privilege_level: str,
    historical_failures: int = 0,
) -> str:

    level = (risk_level or "").strip().upper()

    env_display = (environment or "Unknown").strip()

    is_prod = "PROD" in env_display.upper()

    score_pct = int(round(risk_score * 100))

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    if level == "CRITICAL":

        action = (
            f"Rotate the {credential_name} credential immediately."
        )

    elif level == "HIGH":

        action = (
            f"Schedule rotation for {credential_name} "
            f"within the next 48 hours."
        )

    elif level == "MEDIUM":

        action = (
            f"Plan credential rotation for {credential_name} "
            f"within the next 2 weeks."
        )

    else:

        action = (
            f"Continue monitoring {credential_name}. "
            f"No immediate action required."
        )

    reasons: List[str] = []

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    if days_until_expiry <= 0:

        reasons.append(
            "the credential has expired"
        )

    elif days_until_expiry <= 3:

        reasons.append(
            f"the credential expires in {days_until_expiry} days"
        )

    elif days_until_expiry <= 30:

        reasons.append(
            f"the credential expires in {days_until_expiry} days"
        )

    else:

        reasons.append(
            f"the credential has {days_until_expiry} days before expiry"
        )

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    if is_prod:

        reasons.append(
            "the database is production-critical"
        )

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    if dependency_count > 1:

        reasons.append(
            f"{dependency_count} applications depend on it"
        )

    elif dependency_count == 1:

        reasons.append(
            "1 application depends on it"
        )

    # ------------------------------------------------------------------
    # Privilege
    # ------------------------------------------------------------------

    priv_upper = (privilege_level or "").strip().upper()

    if priv_upper in {
        "HIGH",
        "ADMIN",
        "SUPERUSER",
        "ROOT",
    }:

        reasons.append(
            "the credential has elevated privileges"
        )

    # ------------------------------------------------------------------
    # Historical failures
    # ------------------------------------------------------------------

    if historical_failures > 0:

        reasons.append(
            f"{historical_failures} previous rotation failure(s) "
            f"increase operational risk"
        )

    reason_text = ", ".join(reasons)

    recommendation_text = (
        f"Recommended Action: {action}\n\n"
        f"Reason: With a risk score of {score_pct}%, "
        f"{reason_text}."
    )

    if is_prod and level in {"CRITICAL", "HIGH"}:

        recommendation_text += (
            " Rotate during the next approved low-traffic "
            "maintenance window to minimize service disruption."
        )

    return recommendation_text


# ============================================================================
# MAIN PREDICTION FUNCTION
# ============================================================================

def predict_credential_risk(
    days_until_expiry: int,
    credential_age_days: int,
    dependency_count: int,
    privilege_level: str,
    environment: str,
    historical_rotation_failures: int = 0,
    access_frequency_per_day: int = 10,
) -> Dict[str, Any]:
    """
    Main SecureRotate AI risk prediction function.

    The RandomForest model provides an ML signal, but the final
    risk decision is governed by deterministic security rules.

    This makes the system explainable and prevents unreasonable
    classifications from the trained model.
    """

    model = load_risk_model()

    # ------------------------------------------------------------------
    # 1. Prepare ML input
    # ------------------------------------------------------------------

    input_df = pd.DataFrame(
        [
            {
                "days_until_expiry": days_until_expiry,
                "credential_age_days": credential_age_days,
                "dependency_count": dependency_count,
                "privilege_level": privilege_level,
                "environment": environment,
                "historical_rotation_failures": historical_rotation_failures,
                "access_frequency_per_day": access_frequency_per_day,
            }
        ]
    )

    # ------------------------------------------------------------------
    # 2. Run RandomForest
    # ------------------------------------------------------------------

    pred_class = model.predict(input_df)[0]

    probabilities = model.predict_proba(input_df)[0]

    classes = list(model.classes_)

    prob_dict = {
        str(cls).upper(): float(prob)
        for cls, prob in zip(classes, probabilities)
    }

    # ------------------------------------------------------------------
    # 3. ML signal
    # ------------------------------------------------------------------

    ml_risk_signal = calculate_ml_risk_signal(
        probabilities=prob_dict
    )

    confidence = round(
        float(max(probabilities)),
        2
    )

    # ------------------------------------------------------------------
    # 4. Final deterministic + ML risk score
    # ------------------------------------------------------------------

    risk_score = calculate_final_risk_score(
        days_until_expiry=days_until_expiry,
        privilege_level=privilege_level,
        environment=environment,
        dependency_count=dependency_count,
        historical_failures=historical_rotation_failures,
        ml_risk_signal=ml_risk_signal,
    )

    # ------------------------------------------------------------------
    # 5. Final risk classification
    # ------------------------------------------------------------------

    risk_level = classify_risk_level(
        risk_score=risk_score,
        days_until_expiry=days_until_expiry,
        environment=environment,
        privilege_level=privilege_level,
    )

    # ------------------------------------------------------------------
    # 6. Final risk probability
    #
    # IMPORTANT:
    # This is now aligned with the FINAL risk assessment rather
    # than simply returning the ML HIGH probability.
    # ------------------------------------------------------------------

    risk_probability = risk_score

    # ------------------------------------------------------------------
    # 7. Generate explanations
    # ------------------------------------------------------------------

    reasons = generate_risk_reasons(
        days_until_expiry=days_until_expiry,
        environment=environment,
        privilege_level=privilege_level,
        dependency_count=dependency_count,
        historical_failures=historical_rotation_failures,
    )

    # ------------------------------------------------------------------
    # 8. Recommendation
    # ------------------------------------------------------------------

    recommendation = derive_recommendation(
        risk_level=risk_level
    )

    # ------------------------------------------------------------------
    # 9. Return final result
    # ------------------------------------------------------------------

    return {
        "risk_score": float(risk_score),

        "risk_level": risk_level,

        "risk_probability": float(
            round(risk_probability, 2)
        ),

        "confidence": float(confidence),

        "reasons": reasons,

        "recommendation": recommendation,
    }