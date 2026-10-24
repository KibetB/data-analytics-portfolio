"""
Generates the survey dataset (simulated, n = 600) and saves it as an SPSS .sav file
with full variable labels, value labels and measurement levels - exactly what an analyst
would receive from a KoboToolbox / ODK export after cleaning.

Study: "Mobile Money, Trust and Saving Behaviour among Young Adults (18-35)
        in Embu, Nairobi and Kisumu Counties"
Run:  python src/01_generate_survey.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(2026)
N = 600

county = rng.choice([1, 2, 3], N, p=[.35, .40, .25])          # 1 Embu 2 Nairobi 3 Kisumu
gender = rng.choice([1, 2], N, p=[.52, .48])                  # 1 Female 2 Male
age = rng.integers(18, 36, N)
educ = rng.choice([1, 2, 3, 4], N, p=[.15, .40, .25, .20])    # Primary, Secondary, Diploma, Degree
employ = rng.choice([1, 2, 3, 4], N, p=[.25, .30, .30, .15])  # Unemployed, Casual, Self-employed, Salaried
inc_base = np.array([0, 4000, 9000, 14000, 26000])[employ] + 2500 * educ
income = np.round(np.clip(inc_base * rng.lognormal(0, .45, N), 1500, 150000), -2)

# Latent constructs driving 5-point Likert items (1 Strongly disagree ... 5 Strongly agree)
trust_lat = 0.25 * (educ - 2.5) + 0.15 * (county == 2) + rng.normal(0, 1, N)
literacy_lat = 0.45 * (educ - 2.5) + rng.normal(0, 1, N)

def likert(latent, n_items, loading=.85):
    out = []
    for _ in range(n_items):
        x = loading * latent + rng.normal(0, .55, len(latent))
        out.append(np.digitize(x, [-1.3, -.45, .45, 1.3]) + 1)
    return out

t1, t2, t3, t4, t5 = likert(trust_lat, 5)
f1, f2, f3, f4 = likert(literacy_lat, 4)
t3 = 6 - t3                                                    # reverse-worded item

momo_freq = np.clip(np.round(4 + 0.6 * trust_lat + 0.4 * (county == 2) + rng.normal(0, 1.1, N)), 1, 6)
chama = (rng.random(N) < np.where(gender == 1, .58, .38)).astype(int)
trust_score = (t1 + t2 + (6 - t3) + t4 + t5) / 5
lit_score = (f1 + f2 + f3 + f4) / 4
z = (-6.2 + 0.55 * trust_score + 0.65 * lit_score + 0.42 * np.log(income / 1000)
     + 0.5 * chama + 0.25 * (employ == 4))
formal_save = (rng.random(N) < 1 / (1 + np.exp(-z))).astype(int)
monthly_saving = np.round(np.clip(income * (0.04 + 0.02 * lit_score + 0.02 * chama)
                                  * rng.lognormal(0, .5, N) - 300, 0, None), -1)

df = pd.DataFrame({
    "resp_id": np.arange(1, N + 1), "county": county, "gender": gender, "age": age,
    "educ": educ, "employ": employ, "income_kes": income,
    "trust1": t1, "trust2": t2, "trust3": t3, "trust4": t4, "trust5": t5,
    "fin1": f1, "fin2": f2, "fin3": f3, "fin4": f4,
    "momo_freq": momo_freq.astype(int), "chama": chama,
    "formal_save": formal_save, "monthly_saving_kes": monthly_saving,
})
# realistic item non-response (~2%) on income and two Likert items
for col in ["income_kes", "trust4", "fin2"]:
    df.loc[rng.random(N) < .02, col] = np.nan

likert_lab = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"}
yn = {0: "No", 1: "Yes"}
value_labels = {
    "county": {1: "Embu", 2: "Nairobi", 3: "Kisumu"},
    "gender": {1: "Female", 2: "Male"},
    "educ": {1: "Primary", 2: "Secondary", 3: "Diploma/Certificate", 4: "University degree"},
    "employ": {1: "Unemployed", 2: "Casual work", 3: "Self-employed", 4: "Salaried"},
    "momo_freq": {1: "Never", 2: "Less than monthly", 3: "Monthly", 4: "Weekly",
                  5: "Several times a week", 6: "Daily"},
    "chama": yn, "formal_save": yn,
    **{c: likert_lab for c in ["trust1", "trust2", "trust3", "trust4", "trust5",
                                "fin1", "fin2", "fin3", "fin4"]},
}
column_labels = {
    "resp_id": "Respondent ID", "county": "County of residence", "gender": "Gender",
    "age": "Age in years", "educ": "Highest education completed", "employ": "Employment status",
    "income_kes": "Monthly income (KES)",
    "trust1": "Mobile money keeps my money safe",
    "trust2": "I trust mobile-money agents to give correct cash",
    "trust3": "I worry I could lose money through mobile money (reverse)",
    "trust4": "Mobile-money providers treat customers fairly",
    "trust5": "I would keep savings in a mobile wallet or mobile savings product",
    "fin1": "I can calculate interest on a loan", "fin2": "I keep a monthly budget",
    "fin3": "I compare costs before choosing a financial product",
    "fin4": "I understand the risks of digital loans",
    "momo_freq": "How often do you use mobile money?", "chama": "Member of a chama (savings group)",
    "formal_save": "Saves with a bank, SACCO or mobile savings product",
    "monthly_saving_kes": "Amount saved last month (KES)",
}
measure = {c: "scale" for c in ["age", "income_kes", "monthly_saving_kes"]}
measure.update({c: "nominal" for c in ["county", "gender", "employ", "chama", "formal_save", "resp_id"]})
measure.update({c: "ordinal" for c in ["educ", "momo_freq", "trust1", "trust2", "trust3", "trust4",
                                       "trust5", "fin1", "fin2", "fin3", "fin4"]})

(ROOT / "data").mkdir(exist_ok=True)
pyreadstat.write_sav(df, ROOT / "data" / "youth_finance_survey.sav", column_labels=column_labels,
                     variable_value_labels=value_labels, variable_measure=measure)
df.to_csv(ROOT / "data" / "youth_finance_survey.csv", index=False)
print(f"Saved {len(df)} respondents x {df.shape[1]} variables -> data/youth_finance_survey.sav")
