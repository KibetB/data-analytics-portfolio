"""
Step 1 - Build the SQLite database.

Generates a realistic, reproducible mobile-lending dataset (simulated - no real
customer data) and loads it into three normalised tables:
    customers, loans, transactions
Run:  python src/01_build_database.py
"""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "mobile_lending.db"
SCHEMA = ROOT / "sql" / "schema.sql"
rng = np.random.default_rng(42)

N_CUST = 5000
COUNTIES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Embu", "Eldoret",
            "Machakos", "Nyeri", "Kakamega", "Meru"]
OCCUPATIONS = ["Salaried", "Small business", "Casual labour", "Farmer", "Student"]

# ---------------- customers ----------------
cust = pd.DataFrame({
    "customer_id": np.arange(1, N_CUST + 1),
    "age": rng.integers(18, 65, N_CUST),
    "gender": rng.choice(["F", "M"], N_CUST),
    "county": rng.choice(COUNTIES, N_CUST,
                         p=[.28, .1, .08, .09, .05, .08, .08, .07, .08, .09]),
    "occupation": rng.choice(OCCUPATIONS, N_CUST, p=[.25, .3, .2, .15, .1]),
    "months_on_network": rng.integers(3, 120, N_CUST),
    "signup_date": pd.to_datetime("2023-01-01")
                   + pd.to_timedelta(rng.integers(0, 365, N_CUST), unit="D"),
})
income_base = {"Salaried": 45000, "Small business": 35000, "Casual labour": 15000,
               "Farmer": 18000, "Student": 8000}
cust["monthly_income_kes"] = (cust["occupation"].map(income_base)
                              * rng.lognormal(0, .45, N_CUST)).round(-2)

# ---------------- transactions (6 months of wallet activity) ----------------
tx_rows = []
for cid, inc in zip(cust.customer_id, cust.monthly_income_kes):
    n = rng.poisson(max(5, inc / 1500))
    amounts = rng.gamma(2, inc / 25, n).round(0)
    types = rng.choice(["deposit", "withdrawal", "p2p_send", "bill_pay", "airtime"],
                       n, p=[.25, .25, .25, .15, .1])
    days = rng.integers(0, 180, n)
    for a, t, d in zip(amounts, types, days):
        tx_rows.append((cid, str((pd.Timestamp("2023-07-01") + pd.Timedelta(days=int(d))).date()), t, float(a)))
tx = pd.DataFrame(tx_rows, columns=["customer_id", "tx_date", "tx_type", "amount_kes"])
tx.insert(0, "tx_id", np.arange(1, len(tx) + 1))

# ---------------- loans (1-4 per customer, default driven by real signals) -----
loan_rows, lid = [], 1
deposits = tx[tx.tx_type == "deposit"].groupby("customer_id").amount_kes.sum()
for r in cust.itertuples():
    n_loans = rng.integers(1, 5)
    issue_days = np.sort(rng.integers(0, 300, n_loans))   # loans in date order
    prev_defaults = 0
    for k in range(n_loans):
        amount = float(np.clip(rng.gamma(2, r.monthly_income_kes / 6), 500, 100000).round(-2))
        term = int(rng.choice([7, 14, 30, 60]))
        dep = deposits.get(r.customer_id, 0)
        # latent risk: loan-to-income, thin deposits, tenure, age, occupation, prior loans
        z = (-2.2
             + 1.8 * amount / r.monthly_income_kes
             - 0.9 * np.log1p(dep / r.monthly_income_kes)
             - 0.012 * r.months_on_network
             - 0.015 * (r.age - 18)
             + 0.6 * (r.occupation in ("Casual labour", "Student"))
             + 0.25 * (term >= 30)
             - 0.35 * k
             + 1.3 * prev_defaults
             + rng.normal(0, .5))
        defaulted = int(rng.random() < 1 / (1 + np.exp(-z)))
        prev_defaults += defaulted
        issue = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(issue_days[k]))
        loan_rows.append((lid, r.customer_id, str(issue.date()), amount, term,
                          round(float(rng.uniform(0.06, 0.12)), 3), defaulted))
        lid += 1
loans = pd.DataFrame(loan_rows, columns=["loan_id", "customer_id", "issue_date", "principal_kes",
                                         "term_days", "interest_rate", "defaulted"])

# ---------------- write to SQLite ----------------
DB.parent.mkdir(exist_ok=True)
DB.unlink(missing_ok=True)
con = sqlite3.connect(DB)
con.executescript(SCHEMA.read_text())
cust.assign(signup_date=cust.signup_date.dt.date.astype(str)).to_sql("customers", con, if_exists="append", index=False)
loans.to_sql("loans", con, if_exists="append", index=False)
tx.to_sql("transactions", con, if_exists="append", index=False)
con.commit()
for t in ("customers", "loans", "transactions"):
    print(f"{t:<13}{con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8,} rows")
con.close()
