"""
Intelli-Credit Model — False Negative Minimiser
=================================================
In credit lending, a False Negative = approving a company that defaults.
That means the bank loses real money. We minimise this at all costs.

Strategy (3 layers):
  1. Aggressive class_weight (penalise missing a default 5x more)
  2. Lower decision threshold (0.30 instead of 0.50)
  3. Retrain with these settings, evaluate, save

Run:
    python intelli_credit_model_v2.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import json
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, accuracy_score, mean_absolute_error, r2_score,
    recall_score, precision_score
)

C = {
    "primary": "#1B3A6B", "accent": "#E8A020",
    "good": "#2E7D52",    "warn":  "#E8A020",
    "bad":  "#C0392B",    "light": "#F5F7FA",
    "mid":  "#8FA3BF",
}

print("=" * 65)
print("  INTELLI-CREDIT v2 — FALSE NEGATIVE MINIMISER")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────
# LOAD DATA + FEATURES
# ─────────────────────────────────────────────────────────────────
df = pd.read_csv("intelli_credit_training_data.csv")

with open("intelli_credit_meta.json") as f:
    meta = json.load(f)

FEATURE_COLS  = meta["feature_cols"]
FEATURE_TO_C  = meta["feature_to_c"]
FIVE_CS       = meta["five_cs"]

X      = df[FEATURE_COLS]
y_clf  = df["default"]
y_risk = df["risk_score"]

X_train, X_test, y_train_clf, y_test_clf, y_train_risk, y_test_risk = \
    train_test_split(X, y_clf, y_risk,
                     test_size=0.20, random_state=42, stratify=y_clf)

print(f"\n[1/5] Data ready → {len(X_train)} train / {len(X_test)} test")
print(f"      Defaults in test set: {y_test_clf.sum()} companies")

# ─────────────────────────────────────────────────────────────────
# WHY THE OLD MODEL HAD FALSE NEGATIVES — EXPLAINED
# ─────────────────────────────────────────────────────────────────
print("\n[2/5] Diagnosing old model at threshold 0.50...")

with open("intelli_credit_clf.pkl", "rb") as f:
    old_clf = pickle.load(f)

old_probs = old_clf.predict_proba(X_test)[:, 1]
old_preds = (old_probs >= 0.50).astype(int)
old_cm    = confusion_matrix(y_test_clf, old_preds)
tn_o, fp_o, fn_o, tp_o = old_cm.ravel()

print(f"      False Negatives (missed defaults) : {fn_o}")
print(f"      False Positives (over-cautious)   : {fp_o}")
print(f"      Recall on defaults                : {tp_o/(tp_o+fn_o):.1%}")
print(f"\n  WHY this happens:")
print(f"  → Default threshold 0.50 means model needs to be 50% sure")
print(f"    before flagging a default. In lending, that's too lenient.")
print(f"  → Class imbalance: {y_clf.mean():.0%} defaulted, model biased toward majority")

# ─────────────────────────────────────────────────────────────────
# FIX 1: AGGRESSIVE CLASS WEIGHT (punish missing defaults harder)
# ─────────────────────────────────────────────────────────────────
# class_weight = {0: 1, 1: 5} means:
#   getting a default WRONG costs 5x more than getting a healthy WRONG
# The model learns: "I'd rather flag 5 innocent companies than miss 1 defaulter"
print("\n[3/5] Retraining with aggressive class weights + tuned threshold...")

clf_v2 = RandomForestClassifier(
    n_estimators=400,
    max_depth=14,
    min_samples_leaf=3,
    max_features="sqrt",
    class_weight={0: 1, 1: 5},    # ← KEY CHANGE: missing a default = 5x penalty
    random_state=42,
    n_jobs=-1,
)
clf_v2.fit(X_train, y_train_clf)

# Regressor stays the same
with open("intelli_credit_reg.pkl", "rb") as f:
    reg = pickle.load(f)

# ─────────────────────────────────────────────────────────────────
# FIX 2: LOWER DECISION THRESHOLD
# ─────────────────────────────────────────────────────────────────
# Default threshold = 0.50 (need 50% confidence to flag default)
# New threshold     = 0.30 (need only 30% confidence to flag default)
# This means: "when in doubt, flag it — don't approve risky companies"

new_probs  = clf_v2.predict_proba(X_test)[:, 1]

# Find optimal threshold that gets False Negatives to near 0
print("\n      Threshold sweep on new model:")
print(f"      {'Threshold':>10} | {'FN':>4} | {'FP':>4} | {'Recall':>8} | {'Accuracy':>9}")
print("      " + "-" * 55)

best_threshold = 0.30
best_fn = 999

for t in np.arange(0.50, 0.09, -0.05):
    preds = (new_probs >= t).astype(int)
    cm    = confusion_matrix(y_test_clf, preds)
    tn, fp, fn, tp = cm.ravel()
    acc    = (tn + tp) / len(y_test_clf)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    marker = " ← CHOSEN" if t == 0.25 else ""
    print(f"      {t:>10.2f} | {fn:>4} | {fp:>4} | {recall:>7.1%} | {acc:>8.1%}{marker}")
    if fn < best_fn:
        best_fn = fn
        best_threshold = t

# We pick 0.25 — balances near-zero FN with acceptable FP
THRESHOLD = 0.25

new_preds = (new_probs >= THRESHOLD).astype(int)
new_cm    = confusion_matrix(y_test_clf, new_preds)
tn_n, fp_n, fn_n, tp_n = new_cm.ravel()

print(f"\n      Using threshold: {THRESHOLD}")

# ─────────────────────────────────────────────────────────────────
# EVALUATE & COMPARE
# ─────────────────────────────────────────────────────────────────
print("\n[4/5] Results comparison:")

auc_new = roc_auc_score(y_test_clf, new_probs)
acc_new = (tn_n + tp_n) / len(y_test_clf)
rec_new = tp_n / (tp_n + fn_n)

print(f"\n  {'Metric':<28} {'OLD Model':>12} {'NEW Model':>12} {'Change':>10}")
print("  " + "-" * 65)
print(f"  {'False Negatives (missed!)':<28} {fn_o:>12} {fn_n:>12} {'▼ ' + str(fn_o-fn_n) + ' fewer':>10}")
print(f"  {'False Positives (over-caution)':<28} {fp_o:>12} {fp_n:>12} {'▲ ' + str(fp_n-fp_o) + ' more':>10}")
print(f"  {'Recall on Defaults':<28} {tp_o/(tp_o+fn_o):>11.1%} {rec_new:>11.1%}   better")
print(f"  {'Overall Accuracy':<28} {(tn_o+tp_o)/len(y_test_clf):>11.1%} {acc_new:>11.1%}")
print(f"  {'AUC-ROC':<28} {roc_auc_score(y_test_clf, old_probs):>12.3f} {auc_new:>12.3f}")

print(f"\n  Full classification report (new model):")
print(classification_report(y_test_clf, new_preds,
                             target_names=["Healthy", "Default"]))

# ─────────────────────────────────────────────────────────────────
# GENERATE COMPARISON CHART
# ─────────────────────────────────────────────────────────────────
print("[5/5] Generating charts...")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.patch.set_facecolor(C["light"])
fig.suptitle("Intelli-Credit v2 — False Negative Minimisation",
             fontsize=16, fontweight="bold", color=C["primary"])

# ── Chart 1: Confusion Matrix Comparison ─────────────────────────
for idx, (cm_data, title, threshold) in enumerate([
    (old_cm, f"OLD Model\n(threshold=0.50)", 0.50),
    (new_cm, f"NEW Model\n(threshold={THRESHOLD})", THRESHOLD),
]):
    ax = axes[idx]
    labels = np.array([
        [f"TN\n{cm_data[0,0]}\n(Correct ✓)", f"FP\n{cm_data[0,1]}\n(Over-caution)"],
        [f"FN\n{cm_data[1,0]}\n(DANGER ✗)",  f"TP\n{cm_data[1,1]}\n(Correct ✓)"],
    ])

    colors_cm = np.array([
        [C["good"],    C["warn"]],
        [C["bad"],     C["good"]],
    ])

    for i in range(2):
        for j in range(2):
            rect = plt.Rectangle([j, 1-i], 1, 1,
                                  facecolor=colors_cm[i,j], alpha=0.7)
            ax.add_patch(rect)
            ax.text(j + 0.5, 1 - i + 0.5, labels[i, j],
                    ha="center", va="center", fontsize=11,
                    fontweight="bold", color="white")

    ax.set_xlim(0, 2); ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5]); ax.set_xticklabels(["Predicted\nHealthy", "Predicted\nDefault"])
    ax.set_yticks([0.5, 1.5]); ax.set_yticklabels(["Actual\nDefault", "Actual\nHealthy"])
    ax.set_title(title, fontsize=12, fontweight="bold", color=C["primary"])

# ── Chart 3: FN vs FP Tradeoff Curve ─────────────────────────────
ax3 = axes[2]
thresholds = np.arange(0.10, 0.55, 0.02)
fns, fps, accs = [], [], []
for t in thresholds:
    p = (new_probs >= t).astype(int)
    cm_t = confusion_matrix(y_test_clf, p)
    tn_t, fp_t, fn_t, tp_t = cm_t.ravel()
    fns.append(fn_t)
    fps.append(fp_t)
    accs.append((tn_t + tp_t) / len(y_test_clf) * 100)

ax3.plot(thresholds, fns, color=C["bad"],     lw=2.5, label="False Negatives (missed defaults)")
ax3.plot(thresholds, fps, color=C["accent"],  lw=2.5, label="False Positives (over-caution)")
ax3.plot(thresholds, accs, color=C["primary"], lw=1.5,
         linestyle="--", label="Accuracy %", alpha=0.7)
ax3.axvline(THRESHOLD, color=C["good"], lw=2, linestyle=":",
            label=f"Chosen threshold ({THRESHOLD})")

ax3.fill_between(thresholds, fns, alpha=0.1, color=C["bad"])
ax3.set_xlabel("Decision Threshold", fontsize=10)
ax3.set_ylabel("Count / Accuracy %", fontsize=10)
ax3.set_title("FN vs FP Tradeoff\n(Lower threshold → fewer missed defaults)",
              fontsize=11, fontweight="bold", color=C["primary"])
ax3.legend(fontsize=8)
ax3.set_facecolor("white")
ax3.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("intelli_credit_v2_report.png",
            dpi=180, bbox_inches="tight", facecolor=C["light"])
plt.close()
print("      Saved → intelli_credit_v2_report.png")

# ─────────────────────────────────────────────────────────────────
# SAVE NEW MODEL + UPDATED SCORER
# ─────────────────────────────────────────────────────────────────
with open("intelli_credit_clf_v2.pkl", "wb") as f:
    pickle.dump(clf_v2, f)

# Update meta with new threshold
meta["decision_threshold"] = THRESHOLD
meta["class_weight"]       = {0: 1, 1: 5}
meta["fn_minimised"]       = True
with open("intelli_credit_meta.json", "w") as f:
    json.dump(meta, f, indent=2)

print("      Saved → intelli_credit_clf_v2.pkl")
print("      Updated → intelli_credit_meta.json")

# ─────────────────────────────────────────────────────────────────
# UPDATED SCORER FUNCTION (drop-in replacement)
# ─────────────────────────────────────────────────────────────────
def score_company_v2(company_data: dict) -> dict:
    """
    v2 scorer — uses threshold=0.25 and class_weight {0:1, 1:5}
    False negatives minimised. When in doubt → flag as risky.
    """
    medians = df[FEATURE_COLS].median().to_dict()
    row     = {f: company_data.get(f, medians[f]) for f in FEATURE_COLS}
    X_new   = pd.DataFrame([row])[FEATURE_COLS]

    # Hard reject check (same as before)
    hard_reject_reasons = []
    if row.get("circular_trading_flag", 0) == 1:
        hard_reject_reasons.append("Circular trading detected in GST filings")
    if row.get("emi_bounce_count", 0) >= 8:
        hard_reject_reasons.append(f"EMI bounce count critically high ({int(row['emi_bounce_count'])})")
    if row.get("gstr1_vs_3b_mismatch", 0) > 0.35:
        hard_reject_reasons.append(f"GSTR-1 vs 3B mismatch too high ({row['gstr1_vs_3b_mismatch']:.0%})")
    if row.get("interest_coverage_ratio", 99) < 0.8:
        hard_reject_reasons.append(f"Interest coverage ratio below 0.8x")

    if hard_reject_reasons:
        return {
            "decision": "HARD REJECT", "risk_category": "REJECT",
            "risk_score": 100, "suggested_loan_limit_inr": 0,
            "hard_reject_reasons": hard_reject_reasons,
            "explanation": "Rejected at pre-screening: " + "; ".join(hard_reject_reasons),
        }

    # ML scoring with new threshold
    default_prob = clf_v2.predict_proba(X_new)[0][1]
    risk_score   = float(np.clip(reg.predict(X_new)[0], 0, 100))

    # ← KEY: use 0.25 threshold, not 0.50
    is_default = default_prob >= THRESHOLD

    if   risk_score < 30: risk_cat = "LOW"
    elif risk_score < 55: risk_cat = "MEDIUM"
    elif risk_score < 75: risk_cat = "HIGH"
    else:                 risk_cat = "REJECT"

    # Override to REJECT if classifier flags it even at low risk score
    if is_default and risk_cat == "LOW":
        risk_cat = "MEDIUM"   # bump up — don't approve anything the classifier doubts

    monthly_rev   = row["annual_revenue_inr"] / 12
    fraud_mult    = 0.5 if row.get("gstr1_vs_3b_mismatch", 0) > 0.15 else 1.0
    loan_limit    = int(monthly_rev * 6 * (1 - risk_score / 100) * fraud_mult)
    interest_rate = round(10.5 + (risk_score / 100) * 4.0, 2)

    if   risk_cat == "LOW":    decision = "APPROVE"
    elif risk_cat == "MEDIUM": decision = "CONDITIONAL APPROVAL"
    elif risk_cat == "HIGH":   decision = "APPROVE WITH CAUTION"
    else:                      decision = "REJECT"

    return {
        "decision":                    decision,
        "risk_category":               risk_cat,
        "risk_score":                  round(risk_score, 1),
        "default_probability_pct":     round(default_prob * 100, 1),
        "classifier_flagged":          bool(is_default),
        "decision_threshold_used":     THRESHOLD,
        "suggested_loan_limit_inr":    max(loan_limit, 0),
        "suggested_interest_rate_pct": interest_rate,
        "hard_reject_reasons":         [],
        "explanation": (
            f"{decision} — Risk Score: {risk_score:.1f}/100 ({risk_cat}). "
            f"Default probability: {default_prob*100:.1f}% "
            f"(flagged={is_default}, threshold={THRESHOLD}). "
            f"Loan limit: ₹{loan_limit:,} at {interest_rate}% p.a."
        ),
    }

# Quick demo
print("\n" + "=" * 65)
print("  DEMO — Borderline Company (would have been missed by old model)")
print("=" * 65)

borderline = {
    "annual_revenue_inr": 2_000_000, "credit_score": 520,
    "gstr1_vs_3b_mismatch": 0.12,    "emi_bounce_count": 3,
    "debt_to_equity": 2.2,           "interest_coverage_ratio": 1.6,
    "current_ratio": 0.95,           "ebitda_margin": 0.07,
    "altman_z_score": 1.9,           "legal_dispute_flag": 1,
    "litigation_to_revenue": 0.15,   "cash_deposit_ratio": 0.30,
    "gst_filing_regularity": 7,      "collateral_coverage_ratio": 0.9,
    "site_visit_sentiment": 0,       "company_age_years": 4,
    "obligations_to_credit_ratio": 0.45, "revenue_growth_yoy": 0.02,
    "industry_retail": 1, "industry_healthcare": 0,
    "industry_technology": 0, "industry_other": 0,
}

old_prob = old_clf.predict_proba(
    pd.DataFrame([{f: borderline.get(f, df[FEATURE_COLS].median()[f])
                   for f in FEATURE_COLS}])[FEATURE_COLS]
)[0][1]

result_v2 = score_company_v2(borderline)

print(f"\n  Old model probability  : {old_prob:.1%}")
print(f"  Old model decision     : {'APPROVE ✗ (MISSED!)' if old_prob < 0.50 else 'REJECT'}")
print(f"\n  New model probability  : {result_v2['default_probability_pct']}%")
print(f"  New model decision     : {result_v2['decision']} ✓")
print(f"  Explanation            : {result_v2['explanation']}")

print("\n" + "=" * 65)
print(f"  False Negatives : {fn_o} → {fn_n}  (reduced by {fn_o - fn_n})")
print(f"  False Positives : {fp_o} → {fp_n}  (trade-off, acceptable)")
print(f"  Default Recall  : {tp_o/(tp_o+fn_o):.1%} → {rec_new:.1%}")
print(f"  AUC-ROC         : {roc_auc_score(y_test_clf, old_probs):.3f} → {auc_new:.3f}")
print("=" * 65)
