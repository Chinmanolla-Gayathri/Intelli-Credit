"""
Intelli-Credit ML Model (Retail/B2C Edition)
=============================================
Random Forest Credit Scoring Engine for the Intelli-Credit Hackathon.

What this script does:
  1. Loads and preprocesses the Loan.csv (Retail) dataset
  2. Trains a Random Forest classifier (Default Risk)
  3. Trains a Random Forest regressor (0-100 Risk Score)
  4. Evaluates both models with full advanced metrics (F1, Precision, Recall, etc.)
  5. Generates feature importance charts (the B2C Five Cs breakdown)
  6. Saves the models, encoders, and a scorer function for live inference
  7. Produces a sample JSON output for retail applicants
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
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, accuracy_score, mean_absolute_error, r2_score,
    f1_score, precision_score, recall_score
)
from sklearn.preprocessing import LabelEncoder

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "primary":  "#1B3A6B",   # deep navy
    "accent":   "#E8A020",   # saffron / gold
    "good":     "#2E7D52",   # green
    "warn":     "#E8A020",   # amber
    "bad":      "#C0392B",   # red
    "light":    "#F5F7FA",
    "mid":      "#8FA3BF",
}

print("=" * 65)
print("   INTELLI-CREDIT ML ENGINE (RETAIL EDITION)")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
df = pd.read_csv("Loan.csv")

# Proxy 'default' risk (1 = Reject/Default Risk, 0 = Approve/Healthy)
df['default'] = 1 - df['LoanApproved']
df['risk_score'] = df['RiskScore']

def categorize_risk(score):
    if score < 45: return "LOW"
    elif score < 50: return "MEDIUM"
    elif score < 55: return "HIGH"
    else: return "REJECT"

df["risk_category"] = df["risk_score"].apply(categorize_risk)
df["suggested_loan_limit"] = df["AnnualIncome"] * 0.4 * (1 - df["risk_score"]/100)

print(f"\n[1/7] Data loaded → {df.shape[0]} rows × {df.shape[1]} columns")
print(f"      Default/Reject rate : {df['default'].mean():.1%}")
print(f"      Risk spread         : {df['risk_category'].value_counts().to_dict()}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. FEATURE ENGINEERING & PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/7] Preprocessing features & Applying 5 C's...")

# Five Cs feature groups for Retail (B2C) Lending
FIVE_CS = {
    "Character": [
        "CreditScore", "PaymentHistory", "LengthOfCreditHistory", 
        "PreviousLoanDefaults", "BankruptcyHistory", "UtilityBillsPaymentHistory",
        "NumberOfCreditInquiries"
    ],
    "Capacity": [
        "AnnualIncome", "MonthlyIncome", "DebtToIncomeRatio", 
        "TotalDebtToIncomeRatio", "EmploymentStatus", "JobTenure",
        "MonthlyDebtPayments", "MonthlyLoanPayment"
    ],
    "Capital": [
        "NetWorth", "TotalAssets", "SavingsAccountBalance", 
        "CheckingAccountBalance"
    ],
    "Collateral": [
        "HomeOwnershipStatus", "TotalLiabilities", "NumberOfOpenCreditLines"
    ],
    "Conditions": [
        "Age", "Experience", "LoanAmount", "LoanDuration", 
        "InterestRate", "BaseInterestRate", "LoanPurpose", 
        "EducationLevel", "MaritalStatus", "NumberOfDependents"
    ],
}

FEATURE_COLS = [f for c in FIVE_CS.values() for f in c]
FEATURE_TO_C = {f: c_name for c_name, c_features in FIVE_CS.items() for f in c_features}

# Encode Categorical Variables
encoders = {}
for col in df[FEATURE_COLS].select_dtypes(include=['object']).columns:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    encoders[col] = le

X = df[FEATURE_COLS].copy()
y_clf  = df["default"]            
y_risk = df["risk_score"]         

# ─────────────────────────────────────────────────────────────────────────────
# 3. TRAIN / TEST SPLIT
# ─────────────────────────────────────────────────────────────────────────────
X_train, X_test, y_train_clf, y_test_clf, y_train_risk, y_test_risk = \
    train_test_split(X, y_clf, y_risk, test_size=0.20, random_state=42, stratify=y_clf)

print(f"\n[3/7] Train/test split → {len(X_train)} train / {len(X_test)} test")

# ─────────────────────────────────────────────────────────────────────────────
# 4. TRAIN MODELS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/7] Training models...")

clf = RandomForestClassifier(
    n_estimators=200, max_depth=12, min_samples_leaf=5,
    class_weight="balanced", random_state=42, n_jobs=-1,
)
clf.fit(X_train, y_train_clf)

reg = RandomForestRegressor(
    n_estimators=200, max_depth=12, min_samples_leaf=5,
    random_state=42, n_jobs=-1,
)
reg.fit(X_train, y_train_risk)

# ─────────────────────────────────────────────────────────────────────────────
# 5. EVALUATE
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/7] Evaluating on test set...")

y_pred_clf  = clf.predict(X_test)
y_prob_clf  = clf.predict_proba(X_test)[:, 1]
y_pred_risk = reg.predict(X_test).clip(0, 100)

acc       = accuracy_score(y_test_clf, y_pred_clf)
auc       = roc_auc_score(y_test_clf, y_prob_clf)
f1        = f1_score(y_test_clf, y_pred_clf)
precision = precision_score(y_test_clf, y_pred_clf)
recall    = recall_score(y_test_clf, y_pred_clf)
mae       = mean_absolute_error(y_test_risk, y_pred_risk)
r2        = r2_score(y_test_risk, y_pred_risk)

print(f"      Classifier  → Accuracy: {acc:.3f} | AUC: {auc:.3f} | F1: {f1:.3f} | Precision: {precision:.3f} | Recall: {recall:.3f}")
print(f"      Regressor   → MAE: {mae:.2f} pts | R²: {r2:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. GENERATE CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/7] Generating charts...")

fig = plt.figure(figsize=(22, 18))
fig.patch.set_facecolor(C["light"])
fig.suptitle("Intelli-Credit ML Engine (Retail) — Model Report", fontsize=20, fontweight="bold", color=C["primary"], y=0.98)

gs = fig.add_gridspec(3, 3, hspace=0.45, wspace=0.35)

# ── Chart 1: Feature Importance (Top 20) ──
ax1 = fig.add_subplot(gs[0, :2])
fi = pd.Series(clf.feature_importances_, index=FEATURE_COLS).sort_values()
top20 = fi.tail(20)

colors_fi = [{"Character": C["bad"], "Capacity": C["primary"], "Capital": C["accent"], "Collateral": C["good"], "Conditions": C["mid"]}.get(FEATURE_TO_C.get(f, "Conditions"), C["mid"]) for f in top20.index]

bars = ax1.barh(range(len(top20)), top20.values, color=colors_fi, edgecolor="white", linewidth=0.5)
ax1.set_yticks(range(len(top20)))
ax1.set_yticklabels([f.replace("_", " ") for f in top20.index], fontsize=9)
ax1.set_xlabel("Feature Importance Score", fontsize=10)
ax1.set_title("Top 20 Feature Importances", fontsize=12, fontweight="bold", color=C["primary"], pad=10)
ax1.set_facecolor("white")
ax1.grid(axis="x", alpha=0.3)

legend_patches = [mpatches.Patch(color=C["bad"], label="Character"), mpatches.Patch(color=C["primary"], label="Capacity"), mpatches.Patch(color=C["accent"], label="Capital"), mpatches.Patch(color=C["good"], label="Collateral"), mpatches.Patch(color=C["mid"], label="Conditions")]
ax1.legend(handles=legend_patches, loc="lower right", fontsize=8)

# ── Chart 2: Five Cs Contribution ──
ax2 = fig.add_subplot(gs[0, 2])
c_importance = {c_name: sum(clf.feature_importances_[FEATURE_COLS.index(f)] for f in c_features if f in FEATURE_COLS) for c_name, c_features in FIVE_CS.items()}
total_imp = sum(c_importance.values())
c_pct = {k: v / total_imp * 100 for k, v in c_importance.items()}

wedges, texts, autotexts = ax2.pie(c_pct.values(), labels=c_pct.keys(), autopct="%1.1f%%", colors=[C["bad"], C["primary"], C["accent"], C["good"], C["mid"]], startangle=140, pctdistance=0.75, wedgeprops={"edgecolor": "white", "linewidth": 2})
for t in texts: t.set_fontsize(9)
for t in autotexts: t.set_fontsize(8); t.set_color("white"); t.set_fontweight("bold")
ax2.set_title("Five Cs\nContribution to Model", fontsize=11, fontweight="bold", color=C["primary"])

# ── Chart 3: Confusion Matrix ──
ax3 = fig.add_subplot(gs[1, 0])
cm = confusion_matrix(y_test_clf, y_pred_clf)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax3, xticklabels=["Approve", "Reject/Default"], yticklabels=["Approve", "Reject/Default"], linewidths=1, linecolor="white", cbar=False)
ax3.set_title("Confusion Matrix", fontsize=11, fontweight="bold", color=C["primary"])
ax3.set_ylabel("Actual", fontsize=9)
ax3.set_xlabel("Predicted", fontsize=9)

# ── Chart 4: ROC Curve ──
ax4 = fig.add_subplot(gs[1, 1])
fpr, tpr, _ = roc_curve(y_test_clf, y_prob_clf)
ax4.plot(fpr, tpr, color=C["primary"], lw=2.5, label=f"ROC Curve (AUC = {auc:.3f})")
ax4.plot([0, 1], [0, 1], color=C["mid"], lw=1, linestyle="--", label="Random")
ax4.fill_between(fpr, tpr, alpha=0.08, color=C["primary"])
ax4.set_xlabel("False Positive Rate", fontsize=9)
ax4.set_ylabel("True Positive Rate", fontsize=9)
ax4.set_title("ROC Curve", fontsize=11, fontweight="bold", color=C["primary"])
ax4.legend(fontsize=9)
ax4.set_facecolor("white")
ax4.grid(alpha=0.3)

# ── Chart 5: Risk Score Distribution ──
ax5 = fig.add_subplot(gs[1, 2])
colors_risk = df["risk_category"].map({"LOW": C["good"], "MEDIUM": C["accent"], "HIGH": C["bad"], "REJECT": "#6B0000"})
ax5.scatter(df["risk_score"], df["default"], c=colors_risk, alpha=0.25, s=15, edgecolors="none")
ax5.axvline(45, color=C["good"], lw=1.5, linestyle="--", label="LOW/MED boundary")
ax5.axvline(50, color=C["accent"], lw=1.5, linestyle="--", label="MED/HIGH boundary")
ax5.axvline(55, color=C["bad"], lw=1.5, linestyle="--", label="HIGH/REJECT")
ax5.set_xlabel("Risk Score (0–100)", fontsize=9)
ax5.set_ylabel("Default Risk (1=Reject, 0=Approve)", fontsize=9)
ax5.set_title("Risk Score vs Default Risk", fontsize=11, fontweight="bold", color=C["primary"])
ax5.legend(fontsize=7)
ax5.set_facecolor("white")
ax5.grid(alpha=0.3)

# ── Chart 6: Loan Limit Distribution ──
ax6 = fig.add_subplot(gs[2, :2])
risk_order = ["LOW", "MEDIUM", "HIGH", "REJECT"]
risk_colors = [C["good"], C["accent"], C["bad"], "#6B0000"]
plot_data = [df[df["risk_category"] == r]["suggested_loan_limit"] for r in risk_order]
bp = ax6.boxplot(plot_data, patch_artist=True, notch=False, medianprops={"color": "white", "linewidth": 2})
for patch, color in zip(bp["boxes"], risk_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)
for element in ["whiskers", "caps"]:
    for item in bp[element]: item.set_color(C["mid"])
ax6.set_xticklabels(risk_order, fontsize=10)
ax6.set_xlabel("Risk Category", fontsize=10)
ax6.set_ylabel("Suggested Loan Limit ($)", fontsize=10)
ax6.set_title("Suggested Loan Limit Distribution by Risk Category", fontsize=12, fontweight="bold", color=C["primary"])
ax6.set_facecolor("white")
ax6.grid(axis="y", alpha=0.3)

# ── Chart 7: Model Metrics Summary Card ──
ax7 = fig.add_subplot(gs[2, 2])
ax7.set_facecolor(C["primary"])
ax7.set_xlim(0, 1); ax7.set_ylim(0, 1)
ax7.axis("off")

metrics = [
    ("Accuracy",   f"{acc:.1%}",  "Classifier"),
    ("F1-Score",   f"{f1:.3f}",   "Classifier"),
    ("Precision",  f"{precision:.3f}", "Class 1 (Reject)"),
    ("AUC-ROC",    f"{auc:.3f}",  "Classifier"),
    ("R² Score",   f"{r2:.3f}",   "Regressor"),
    ("MAE",        f"{mae:.2f}",  "Risk Score"),
]
ax7.text(0.5, 0.95, "Model Performance", ha="center", va="top", fontsize=12, fontweight="bold", color="white", transform=ax7.transAxes)
for i, (label, value, sub) in enumerate(metrics):
    y_pos = 0.82 - i * 0.13
    ax7.text(0.08, y_pos, label, fontsize=9, color=C["mid"], transform=ax7.transAxes)
    ax7.text(0.92, y_pos, value, fontsize=11, color=C["accent"], fontweight="bold", ha="right", transform=ax7.transAxes)
    ax7.text(0.92, y_pos - 0.045, sub, fontsize=7, color=C["mid"], ha="right", transform=ax7.transAxes)

plt.savefig("intelli_credit_retail_model_report.png", dpi=180, bbox_inches="tight", facecolor=C["light"])
plt.close()
print("      Saved → intelli_credit_retail_model_report.png")

# ─────────────────────────────────────────────────────────────────────────────
# 7. SAVE MODEL + SCORER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7/7] Saving model artifacts...")

with open("intelli_credit_clf.pkl", "wb") as f: pickle.dump(clf, f)
with open("intelli_credit_reg.pkl", "wb") as f: pickle.dump(reg, f)
with open("intelli_credit_encoders.pkl", "wb") as f: pickle.dump(encoders, f)

model_meta = {
    "feature_cols":    FEATURE_COLS,
    "feature_to_c":    FEATURE_TO_C,
    "five_cs":         FIVE_CS,
    "risk_thresholds": {"LOW": 45, "MEDIUM": 50, "HIGH": 55, "REJECT": 100},
}
with open("intelli_credit_meta.json", "w") as f: json.dump(model_meta, f, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# LIVE SCORER FUNCTION (For the API)
# ─────────────────────────────────────────────────────────────────────────────
def score_applicant(applicant_data: dict) -> dict:
    medians = df[FEATURE_COLS].median(numeric_only=True).to_dict()
    row = {}
    
    # Safely load data or fill with standard values
    for f in FEATURE_COLS:
        val = applicant_data.get(f)
        if val is None:
            val = df[f].mode()[0] if f in encoders else medians.get(f, 0)
        row[f] = val
    
    # Dynamically encode string variables like 'EmploymentStatus'
    encoded_row = row.copy()
    for col, le in encoders.items():
        if isinstance(encoded_row[col], str):
            if encoded_row[col] in le.classes_:
                encoded_row[col] = le.transform([encoded_row[col]])[0]
            else:
                encoded_row[col] = 0

    X_new = pd.DataFrame([encoded_row])[FEATURE_COLS]

    # ── Hard reject check (RETAIL CRITERIA) ──
    hard_reject_reasons = []
    if row.get("BankruptcyHistory", 0) >= 1:
        hard_reject_reasons.append("Applicant has history of bankruptcy")
    if row.get("PreviousLoanDefaults", 0) >= 1:
        hard_reject_reasons.append(f"Previous loan defaults detected ({int(row.get('PreviousLoanDefaults', 0))})")
    if row.get("CreditScore", 999) < 550:
        hard_reject_reasons.append(f"Credit Score too low ({int(row.get('CreditScore', 0))})")
    if row.get("TotalDebtToIncomeRatio", 0) > 0.65:
        hard_reject_reasons.append(f"Debt-to-Income ratio critically high ({row.get('TotalDebtToIncomeRatio', 0):.2f})")
    if row.get("EmploymentStatus", "") == "Unemployed":
        hard_reject_reasons.append("Employment status is Unemployed")

    if hard_reject_reasons:
        return {
            "decision":          "HARD REJECT",
            "risk_category":     "REJECT",
            "risk_score":        100,
            "default_probability_pct": 100.0,
            "suggested_loan_limit": 0,
            "suggested_interest_rate_pct": None,
            "top_risk_factors": hard_reject_reasons,
            "five_cs_scores": {},
            "hard_reject_reasons": hard_reject_reasons,
            "explanation": "Application rejected at pre-screening due to: " + "; ".join(hard_reject_reasons),
        }

    # ── ML scoring ──
    default_prob  = clf.predict_proba(X_new)[0][1]
    risk_score    = float(reg.predict(X_new)[0])
    risk_score    = np.clip(risk_score, 0, 100)

    if   risk_score < 45: risk_cat = "LOW"
    elif risk_score < 50: risk_cat = "MEDIUM"
    elif risk_score < 55: risk_cat = "HIGH"
    else:                 risk_cat = "REJECT"

    loan_limit    = int(row["AnnualIncome"] * 0.4 * (1 - risk_score / 100))
    loan_limit    = max(loan_limit, 0)
    interest_rate = round(row.get("BaseInterestRate", 5.0) + (risk_score / 100) * 8.0, 2)

    # ── Calculate Top Risk Factors & 5 C's Sub-scores ──
    risk_direction = {
        "DebtToIncomeRatio": 1, "TotalDebtToIncomeRatio": 1, "MonthlyDebtPayments": 1, 
        "TotalLiabilities": 1, "LoanAmount": 1, "PreviousLoanDefaults": 1, 
        "BankruptcyHistory": 1, "NumberOfCreditInquiries": 1,
        "CreditScore": -1, "AnnualIncome": -1, "NetWorth": -1, "TotalAssets": -1,
        "SavingsAccountBalance": -1, "JobTenure": -1, "LengthOfCreditHistory": -1
    }
    
    fi_series = pd.Series(clf.feature_importances_, index=FEATURE_COLS)
    factor_scores = {}
    for feat in FEATURE_COLS:
        direction = risk_direction.get(feat, 1)
        val = encoded_row[feat]
        col_min, col_max = df[feat].min(), df[feat].max()
        norm = (val - col_min) / (col_max - col_min + 1e-9)
        risk_val = norm if direction == 1 else (1 - norm)
        factor_scores[feat] = fi_series[feat] * risk_val

    top_risks = sorted(factor_scores, key=factor_scores.get, reverse=True)[:5]
    top_risk_factors = [f.replace("_", " ") for f in top_risks]

    # Calculate 5 C's Scores (0 to 100 scale based on weighted risk)
    five_cs_scores = {}
    for c_name, c_features in FIVE_CS.items():
        valid = [f for f in c_features if f in FEATURE_COLS]
        if not valid: continue
        c_risk = np.mean([factor_scores.get(f, 0) for f in valid])
        five_cs_scores[c_name] = round(float(c_risk) * 1000, 1) # scaled for visibility

    # ── Decision ──
    if   risk_cat == "LOW":    decision = "APPROVE"
    elif risk_cat == "MEDIUM": decision = "CONDITIONAL APPROVAL"
    elif risk_cat == "HIGH":   decision = "APPROVE WITH CAUTION"
    else:                      decision = "REJECT"

    explanation = (f"{decision} — Risk Score: {risk_score:.1f}/100 ({risk_cat}). "
                   f"Primary risk drivers: {', '.join(top_risk_factors[:3])}. "
                   f"Suggested loan limit: ${loan_limit:,} at {interest_rate}% p.a.")

    return {
        "decision": decision,
        "risk_category": risk_cat,
        "risk_score": round(risk_score, 1),
        "default_probability_pct": round(default_prob * 100, 1),
        "suggested_loan_limit": loan_limit,
        "suggested_interest_rate_pct": interest_rate,
        "top_risk_factors": top_risk_factors,
        "five_cs_scores": five_cs_scores,
        "hard_reject_reasons": [],
        "explanation": explanation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("   LIVE SCORER DEMO")
print("=" * 65)

# Applicant A — Healthy Employed Candidate
applicant_a = {
    "AnnualIncome": 85000, "CreditScore": 750, "DebtToIncomeRatio": 0.20,
    "TotalDebtToIncomeRatio": 0.25, "PreviousLoanDefaults": 0, "BankruptcyHistory": 0, 
    "EmploymentStatus": "Employed", "NetWorth": 150000, "LoanAmount": 15000, 
    "BaseInterestRate": 4.5
}

# Applicant B — High-Risk Unemployed Candidate
applicant_b = {
    "AnnualIncome": 32000, "CreditScore": 510, "DebtToIncomeRatio": 0.75,
    "TotalDebtToIncomeRatio": 0.85, "PreviousLoanDefaults": 1, "BankruptcyHistory": 0, 
    "EmploymentStatus": "Unemployed", "NetWorth": 2000, "LoanAmount": 25000, 
    "BaseInterestRate": 5.0
}

for name, applicant in [("Applicant A (Healthy)", applicant_a), ("Applicant B (High-Risk)", applicant_b)]:
    result = score_applicant(applicant)
    print(f"\n  ── {name} ──")
    print(f"  Decision          : {result['decision']}")
    print(f"  Risk Category     : {result['risk_category']}")
    print(f"  Risk Score        : {result['risk_score']}/100")
    print(f"  Five Cs Scores    : {result['five_cs_scores']}")
    print(f"  Explanation       : {result.get('explanation')}")
    
    # Save sample output JSON
    fname = f"sample_output_{name.split()[1].lower()}.json"
    with open(fname, "w") as f:
        json.dump(result, f, indent=2)

print("\n" + "=" * 65)
print("  ALL DONE")
print("=================================================================")