"""
Step 2 - Query the database with SQL, then train and evaluate default-prediction models.

Pipeline
  1. Run the named exploratory SQL queries  -> outputs/sql_results/*.csv
  2. Run the feature-engineering SQL        -> modelling table (one row per loan)
  3. Time-based train/test split (train on Jan-Aug 2024, test on Sep-Oct 2024)
  4. Fit Logistic Regression (baseline) and Gradient Boosting
  5. Evaluate: ROC-AUC, PR-AUC, confusion matrix, feature importance, calibration
Run:  python src/02_train_model.py
"""
from pathlib import Path
import re, sqlite3, json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.calibration import calibration_curve
from sklearn.metrics import (roc_auc_score, average_precision_score, roc_curve,
                             confusion_matrix, classification_report)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"; (OUT / "sql_results").mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(ROOT / "data" / "mobile_lending.db")

# ---------------------------------------------------------------- 1. SQL EDA
sql = (ROOT / "sql" / "02_exploratory_queries.sql").read_text()
for name, body in re.findall(r"-- name: (\w+)\n(.*?)(?=-- name:|\Z)", sql, re.S):
    df = pd.read_sql(body, con)
    df.to_csv(OUT / "sql_results" / f"{name}.csv", index=False)
    print(f"\n### {name}\n{df.head(10).to_string(index=False)}")

# ---------------------------------------------------------------- 2. features
data = pd.read_sql((ROOT / "sql" / "03_feature_engineering.sql").read_text(), con)
con.close()
print(f"\nModelling table: {data.shape[0]:,} loans x {data.shape[1]} columns")

# ---------------------------------------------------------------- 3. split
train = data[data.issue_date < "2024-09-01"]
test = data[data.issue_date >= "2024-09-01"]
target = "defaulted"
cat = ["gender", "occupation", "county"]
num = ["principal_kes", "term_days", "interest_rate", "prior_loans", "prior_defaults",
       "age", "months_on_network", "monthly_income_kes", "loan_to_income", "tx_count",
       "deposits_to_income", "withdraw_deposit_ratio", "bill_payments", "active_months"]
X_tr, y_tr, X_te, y_te = train[cat + num], train[target], test[cat + num], test[target]
print(f"Train {len(train):,} (default {y_tr.mean():.1%}) | Test {len(test):,} (default {y_te.mean():.1%})")

# ---------------------------------------------------------------- 4. models
prep = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                      ("sc", StandardScaler())]), num),
])
models = {
    "Logistic Regression": Pipeline([("prep", prep),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))]),
    "Gradient Boosting": Pipeline([("prep", prep),
        ("clf", HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300,
                max_leaf_nodes=15, l2_regularization=1.0, random_state=42))]),
}
results, probs = {}, {}
for name, m in models.items():
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]
    probs[name] = p
    results[name] = {"roc_auc": round(roc_auc_score(y_te, p), 4),
                      "pr_auc": round(average_precision_score(y_te, p), 4)}
print("\nTest-set performance:\n", pd.DataFrame(results).T)

best_name = max(results, key=lambda k: results[k]["roc_auc"])
best = models[best_name]; p_best = probs[best_name]

# business threshold: flag the riskiest 20% of applications for manual review
thr = np.quantile(p_best, 0.80)
pred = (p_best >= thr).astype(int)
cm = confusion_matrix(y_te, pred)
report = classification_report(y_te, pred, target_names=["Repaid", "Defaulted"], output_dict=True)
caught = cm[1, 1] / cm[1].sum()
print(f"\nBest model: {best_name}. Reviewing top 20% riskiest loans catches {caught:.0%} of defaults.")

# ---------------------------------------------------------------- 5. plots
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
colors = {"Logistic Regression": "#2a6f97", "Gradient Boosting": "#c8553d"}
fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))

for name, p in probs.items():                                      # ROC
    fpr, tpr, _ = roc_curve(y_te, p)
    ax[0].plot(fpr, tpr, lw=2.2, color=colors[name], label=f"{name} (AUC {results[name]['roc_auc']:.3f})")
ax[0].plot([0, 1], [0, 1], "--", color="grey", lw=1)
ax[0].set(title="ROC curve (out-of-time test set)", xlabel="False positive rate", ylabel="True positive rate")
ax[0].legend(loc="lower right", frameon=False)

pi = permutation_importance(best, X_te, y_te, scoring="roc_auc", n_repeats=10, random_state=0)
imp = pd.Series(pi.importances_mean, index=cat + num).sort_values().tail(10)   # importance
ax[1].barh(imp.index, imp.values, color="#c8553d")
ax[1].set(title=f"Top drivers of default ({best_name})", xlabel="Drop in ROC-AUC when shuffled")

for name, p in probs.items():                                      # calibration
    fp, mp = calibration_curve(y_te, p, n_bins=10, strategy="quantile")
    ax[2].plot(mp, fp, "o-", color=colors[name], label=name)
ax[2].plot([0, 1], [0, 1], "--", color="grey", lw=1)
ax[2].set(title="Calibration: predicted vs actual default rate", xlabel="Predicted probability",
          ylabel="Observed default rate")
ax[2].legend(frameon=False)
fig.suptitle("Mobile-loan default model: evaluation", fontsize=15, fontweight="bold", x=.01, ha="left")
fig.tight_layout(); fig.savefig(OUT / "model_evaluation.png", dpi=160); plt.close(fig)

fig, ax = plt.subplots(figsize=(5, 4.3))                           # confusion matrix
ax.imshow(cm, cmap="Blues"); ax.grid(False)
for (i, j), v in np.ndenumerate(cm):
    ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=14,
            color="white" if v > cm.max() / 2 else "black")
ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Approve", "Review"],
       yticklabels=["Repaid", "Defaulted"], xlabel="Model decision", ylabel="Actual outcome",
       title="Confusion matrix (top-20% risk flagged)")
fig.tight_layout(); fig.savefig(OUT / "confusion_matrix.png", dpi=160); plt.close(fig)

# ---------------------------------------------------------------- save
joblib.dump(best, OUT / "best_model.joblib")
json.dump({"models": results, "best_model": best_name, "review_threshold_prob": round(float(thr), 4),
           "share_of_defaults_caught_top20pct": round(float(caught), 4),
           "precision_at_threshold": round(report["Defaulted"]["precision"], 4),
           "train_rows": len(train), "test_rows": len(test),
           "test_default_rate": round(float(y_te.mean()), 4),
           "top_features": imp.sort_values(ascending=False).round(4).to_dict()},
          open(OUT / "metrics.json", "w"), indent=2)
print("\nSaved: outputs/model_evaluation.png, confusion_matrix.png, metrics.json, best_model.joblib")
