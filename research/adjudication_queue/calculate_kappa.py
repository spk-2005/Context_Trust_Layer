"""
Chance-Adjusted Inter-Annotator Agreement Engine (Cohen's Kappa).
Computes rigorous, multiclass Cohen's Kappa with marginal chance-correction,
observed agreement, and qualitative reliability benchmarks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def compute_cohens_kappa(
    reviewer_a_dispositions: List[str],
    reviewer_b_dispositions: List[str],
    categories: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Computes Cohen's Kappa for two raters over categorical classifications.
    Returns detailed metrics dictionary with observed agreement, expected chance agreement,
    Kappa coefficient, and qualitative strength of agreement.
    """
    if len(reviewer_a_dispositions) != len(reviewer_b_dispositions):
        raise ValueError("Both reviewers must have evaluated the exact same number of items.")

    n = len(reviewer_a_dispositions)
    if n == 0:
        return {"n": 0, "observed_agreement": 0.0, "chance_agreement": 0.0, "cohens_kappa": 0.0, "interpretation": "NO_DATA"}

    if categories is None:
        categories = sorted(list(set(reviewer_a_dispositions) | set(reviewer_b_dispositions)))

    # Construct confusion matrix
    matrix: Dict[str, Dict[str, int]] = {c1: {c2: 0 for c2 in categories} for c1 in categories}
    for a, b in zip(reviewer_a_dispositions, reviewer_b_dispositions):
        if a in matrix and b in matrix[a]:
            matrix[a][b] += 1
        else:
            # Handle out of vocabulary gracefully
            matrix.setdefault(a, {})[b] = matrix.get(a, {}).get(b, 0) + 1

    # Observed agreement (Po)
    agreed_count = sum(matrix.get(c, {}).get(c, 0) for c in categories)
    p_o = agreed_count / n

    # Expected chance agreement (Pe)
    row_totals = {c: sum(matrix.get(c, {}).get(c2, 0) for c2 in categories) for c in categories}
    col_totals = {c: sum(matrix.get(c1, {}).get(c, 0) for c1 in categories) for c in categories}

    p_e = sum((row_totals[c] / n) * (col_totals[c] / n) for c in categories)

    # Cohen's Kappa
    if p_e >= 1.0 or (1.0 - p_e) < 1e-9:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    kappa = max(-1.0, min(1.0, kappa))

    # Qualitative interpretation (Landis & Koch, 1977)
    if kappa < 0.0:
        interp = "POOR (Less than chance)"
    elif kappa <= 0.20:
        interp = "SLIGHT"
    elif kappa <= 0.40:
        interp = "FAIR"
    elif kappa <= 0.60:
        interp = "MODERATE"
    elif kappa <= 0.80:
        interp = "SUBSTANTIAL"
    else:
        interp = "ALMOST_PERFECT"

    return {
        "total_items": n,
        "agreed_items": agreed_count,
        "disagreed_items": n - agreed_count,
        "observed_agreement_pct": round(p_o * 100, 2),
        "chance_expected_agreement_pct": round(p_e * 100, 2),
        "cohens_kappa": round(kappa, 4),
        "interpretation": interp,
        "confusion_matrix": matrix,
    }
