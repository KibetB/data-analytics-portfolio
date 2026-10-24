"""
Replicates every test in spss/analysis.sps in open-source Python, so results can be
verified without an SPSS licence, and produces the figures used in the case study.
Run:  python src/02_replicate_analysis.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyreadstat
import scipy.stats as st
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)
df, meta = pyreadstat.read_sav(ROOT / "data" / "youth_finance_survey.sav")
lab = meta.variable_value_labels
R = {"n": len(df)}

# ---------------------------------------------------------------- 1. preparation
df["trust3_r"] = 6 - df["trust3"]
df["log_income"] = np.log(df["income_kes"])
df["log_saving"] = np.log(df["monthly_saving_kes"] + 1)
trust_items = ["trust1", "trust2", "trust3_r", "trust4", "trust5"]
fin_items = ["fin1", "fin2", "fin3", "fin4"]
df["trust_score"] = df[trust_items].mean(axis=1).where(df[trust_items].notna().sum(axis=1) >= 4)
df["fin_lit_score"] = df[fin_items].mean(axis=1).where(df[fin_items].notna().sum(axis=1) >= 3)
R["missing"] = df[["income_kes", "trust4", "fin2"]].isna().sum().to_dict()

# ---------------------------------------------------------------- 2. profile
prof = {}
for v in ["county", "gender", "educ", "employ", "chama", "formal_save"]:
    pct = df[v].map(lab[v]).value_counts(normalize=True).mul(100).round(1)
    prof[v] = pct.to_dict()
R["profile"] = prof
R["age_mean_sd"] = [round(df.age.mean(), 1), round(df.age.std(), 1)]
R["income_median"] = float(df.income_kes.median())
R["saving_median"] = float(df.monthly_saving_kes.median())

# ---------------------------------------------------------------- 3. reliability
def cronbach(items):
    d = df[items].dropna()
    k = d.shape[1]
    alpha = k / (k - 1) * (1 - d.var(ddof=1).sum() / d.sum(axis=1).var(ddof=1))
    citc = {c: round(st.pearsonr(d[c], d.drop(columns=c).sum(axis=1))[0], 2) for c in items}
    return round(alpha, 3), citc, len(d)
R["alpha_trust"], R["citc_trust"], _ = cronbach(trust_items)
R["alpha_fin"], R["citc_fin"], _ = cronbach(fin_items)
R["alpha_trust_if_trust3_not_reversed"] = cronbach(["trust1", "trust2", "trust3", "trust4", "trust5"])[0]

# ---------------------------------------------------------------- 4. hypothesis tests
def chi(a, b):
    ct = pd.crosstab(df[a], df[b])
    chi2, p, dof, _ = st.chi2_contingency(ct, correction=False)
    rowpct = pd.crosstab(df[a].map(lab[a]), df[b].map(lab[b]), normalize="index").mul(100).round(1)
    return {"chi2": round(chi2, 2), "df": dof, "p": float(p), "phi": round(np.sqrt(chi2 / ct.values.sum()), 3),
            "row_pct_yes": rowpct["Yes"].to_dict()}
R["H1_gender_chama"] = chi("gender", "chama")
R["H2_gender_formal"] = chi("gender", "formal_save")

def ttest(var):
    g1 = df.loc[df.formal_save == 1, var].dropna(); g0 = df.loc[df.formal_save == 0, var].dropna()
    lev = st.levene(g1, g0)
    t = st.ttest_ind(g1, g0, equal_var=lev.pvalue > .05)
    sp = np.sqrt(((len(g1) - 1) * g1.var() + (len(g0) - 1) * g0.var()) / (len(g1) + len(g0) - 2))
    return {"mean_savers": round(g1.mean(), 2), "sd_savers": round(g1.std(), 2),
            "mean_non": round(g0.mean(), 2), "sd_non": round(g0.std(), 2),
            "t": round(t.statistic, 2), "df": len(g1) + len(g0) - 2, "p": float(t.pvalue),
            "levene_p": round(lev.pvalue, 3), "cohens_d": round((g1.mean() - g0.mean()) / sp, 2),
            "n_savers": len(g1), "n_non": len(g0)}
R["H3_trust_by_saver"] = ttest("trust_score")
R["H3b_literacy_by_saver"] = ttest("fin_lit_score")

d4 = df.dropna(subset=["fin_lit_score"])
groups = [g.fin_lit_score for _, g in d4.groupby("educ")]
f = st.f_oneway(*groups)
ss_b = sum(len(g) * (g.mean() - d4.fin_lit_score.mean()) ** 2 for g in groups)
ss_t = ((d4.fin_lit_score - d4.fin_lit_score.mean()) ** 2).sum()
tk = pairwise_tukeyhsd(d4.fin_lit_score, d4.educ.map(lab["educ"]))
tk_df = pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0])
R["H4_literacy_by_educ"] = {
    "F": round(f.statistic, 2), "df": [len(groups) - 1, len(d4) - len(groups)], "p": float(f.pvalue),
    "eta_sq": round(ss_b / ss_t, 3), "levene_p": round(st.levene(*groups).pvalue, 3),
    "means": d4.groupby(d4.educ.map(lab["educ"])).fin_lit_score.mean().round(2).to_dict(),
    "tukey": tk_df.assign(meandiff=tk_df.meandiff.astype(float).round(2))[["group1", "group2", "meandiff", "p-adj", "reject"]]
                  .to_dict("records")}

kw = st.kruskal(*[g.momo_freq for _, g in df.groupby("county")])
R["H5_momo_by_county"] = {"H": round(kw.statistic, 2), "df": 2, "p": float(kw.pvalue),
                          "median": df.groupby(df.county.map(lab["county"])).momo_freq.median().to_dict(),
                          "mean_rank_like_mean": df.groupby(df.county.map(lab["county"])).momo_freq.mean().round(2).to_dict()}

cv = ["trust_score", "fin_lit_score", "log_income", "monthly_saving_kes", "momo_freq"]
R["H6_correlations"] = df[cv].corr().round(2).to_dict()
R["H6_spearman_trust_momo"] = round(st.spearmanr(df.trust_score, df.momo_freq, nan_policy="omit")[0], 2)

# ---------------------------------------------------------------- 5. models
m = df.dropna(subset=["trust_score", "fin_lit_score", "log_income"]).copy()
m["male"] = (m.gender == 2).astype(int)
logit = smf.logit("formal_save ~ trust_score + fin_lit_score + log_income + chama + male + age + C(educ)",
                  data=m).fit(disp=0)
ll0, ll1, n = logit.llnull, logit.llf, logit.nobs
cox = 1 - np.exp(2 * (ll0 - ll1) / n)
nag = cox / (1 - np.exp(2 * ll0 / n))
pred = (logit.predict(m) >= .5).astype(int)
# Hosmer-Lemeshow
m["p_hat"] = logit.predict(m); m["dec"] = pd.qcut(m.p_hat, 10, labels=False, duplicates="drop")
hl = m.groupby("dec").apply(lambda g: (g.formal_save.sum() - g.p_hat.sum()) ** 2
                            / (g.p_hat.sum() * (1 - g.p_hat.mean())), include_groups=False).sum()
ci = np.exp(logit.conf_int())
R["logit"] = {
    "n": int(n), "LR_chi2": round(2 * (ll1 - ll0), 2), "LR_df": int(logit.df_model),
    "LR_p": float(logit.llr_pvalue), "nagelkerke_r2": round(nag, 3), "cox_snell_r2": round(cox, 3),
    "accuracy": round((pred == m.formal_save).mean(), 3), "base_rate": round(m.formal_save.mean(), 3),
    "hosmer_lemeshow_chi2": round(hl, 2), "hosmer_lemeshow_p": round(1 - st.chi2.cdf(hl, 8), 3),
    "table": pd.DataFrame({"B": logit.params.round(3), "OR": np.exp(logit.params).round(2),
                           "CI_low": ci[0].round(2), "CI_high": ci[1].round(2),
                           "p": logit.pvalues.round(4)}).to_dict("index")}

ols = smf.ols("log_saving ~ trust_score + fin_lit_score + log_income + chama + age", data=m).fit()
X = ols.model.exog
R["ols"] = {"n": int(ols.nobs), "R2": round(ols.rsquared, 3), "adjR2": round(ols.rsquared_adj, 3),
            "F": round(ols.fvalue, 2), "F_p": float(ols.f_pvalue),
            "durbin_watson": round(float(np.sum(np.diff(ols.resid) ** 2) / np.sum(ols.resid ** 2)), 2),
            "table": pd.DataFrame({"B": ols.params.round(3), "SE": ols.bse.round(3), "p": ols.pvalues.round(4)})
                     .to_dict("index"),
            "vif": {ols.model.exog_names[i]: round(variance_inflation_factor(X, i), 2) for i in range(1, X.shape[1])}}
# standardized betas
z = m[["log_saving", "trust_score", "fin_lit_score", "log_income", "chama", "age"]].apply(st.zscore)
R["ols"]["std_beta"] = smf.ols("log_saving ~ trust_score + fin_lit_score + log_income + chama + age",
                               data=z).fit().params.drop("Intercept").round(3).to_dict()

from statsmodels.stats.diagnostic import het_breuschpagan
R["ols"]["breusch_pagan_p"] = float(het_breuschpagan(ols.resid, ols.model.exog)[1])
R["ols"]["hc3_p"] = smf.ols("log_saving ~ trust_score + fin_lit_score + log_income + chama + age",
                            data=m).fit(cov_type="HC3").pvalues.round(4).to_dict()
fa_items = trust_items + fin_items
R["efa_eigenvalues"] = np.round(np.linalg.eigvalsh(df[fa_items].dropna().corr())[::-1][:4], 2).tolist()

json.dump(R, open(OUT / "results.json", "w"), indent=2, default=str)

# ---------------------------------------------------------------- 6. figures
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "axes.titleweight": "bold"})
ink, green, gold, red, blue = "#1d2433", "#1f7a5a", "#c9922e", "#b8412f", "#2a5d8f"

# Fig 1: diverging Likert chart for the trust scale (as worded, before reversing)
fig, ax = plt.subplots(figsize=(11, 4.2))
items = ["trust1", "trust2", "trust3", "trust4", "trust5"]
pct = pd.DataFrame({c: df[c].value_counts(normalize=True).reindex(range(1, 6), fill_value=0) * 100 for c in items}).T
cols = [red, "#e3a091", "#d9d9d9", "#8fc0aa", green]
left = -(pct[1] + pct[2] + pct[3] / 2)
for k in range(1, 6):
    ax.barh(range(len(items)), pct[k], left=left, color=cols[k - 1], label=lab["trust1"][float(k)] if float(k) in lab["trust1"] else lab["trust1"][k])
    left = left + pct[k]
ax.set_yticks(range(len(items)), [meta.column_names_to_labels[c] for c in items], fontsize=9)
ax.invert_yaxis(); ax.axvline(0, color=ink, lw=.8)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{abs(v):.0f}%"))
ax.set_xlabel("% of respondents (disagree to the left of the line, agree to the right; neutral split across it)")
ax.set_title("Trust in mobile money: item responses", loc="left")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(.45, -.18), frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig(OUT / "fig1_trust_likert.png", dpi=170); plt.close(fig)

# Fig 2: formal saving rate by education & chama
fig, ax = plt.subplots(figsize=(8.5, 4.2))
rate = df.groupby([df.educ.map(lab["educ"]), "chama"]).formal_save.mean().unstack() * 100
rate = rate.reindex(list(lab["educ"].values()))
x = np.arange(len(rate))
ax.bar(x - .2, rate[0], .4, color="#a9b4c2", label="Not in a chama")
ax.bar(x + .2, rate[1], .4, color=blue, label="Chama member")
for i, (a, b) in enumerate(zip(rate[0], rate[1])):
    ax.text(i - .2, a + 1, f"{a:.0f}%", ha="center", fontsize=8.5); ax.text(i + .2, b + 1, f"{b:.0f}%", ha="center", fontsize=8.5)
ax.set_xticks(x, rate.index); ax.set_ylabel("% saving formally"); ax.set_ylim(0, 100)
ax.set_title("Formal saving rises with education; the chama gap opens from secondary level up", loc="left", fontsize=10.5)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig2_saving_by_educ_chama.png", dpi=170); plt.close(fig)

# Fig 3: odds-ratio forest plot
tab = pd.DataFrame(R["logit"]["table"]).T.drop("Intercept")
nice = {"trust_score": "Trust score (+1 pt)", "fin_lit_score": "Financial literacy (+1 pt)",
        "log_income": "Log income (+1 = 2.7x income)", "chama": "Chama member", "male": "Male (vs female)",
        "age": "Age (+1 yr)", "C(educ)[T.2.0]": "Secondary (vs primary)",
        "C(educ)[T.3.0]": "Diploma (vs primary)", "C(educ)[T.4.0]": "Degree (vs primary)"}
tab.index = [nice.get(i, i) for i in tab.index]
tab = tab.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
sig = tab.p < .05
ax.errorbar(tab.OR, range(len(tab)), xerr=[tab.OR - tab.CI_low, tab.CI_high - tab.OR], fmt="none",
            ecolor="#9aa3ae", elinewidth=1.6, capsize=3)
ax.scatter(tab.OR, range(len(tab)), color=np.where(sig, green, "#9aa3ae"), s=46, zorder=3)
ax.axvline(1, color=ink, lw=.8, ls="--"); ax.set_xscale("log")
ax.set_xticks([.5, 1, 2, 3], ["0.5", "1", "2", "3"]); ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_yticks(range(len(tab)), tab.index, fontsize=9)
ax.set_xlabel("Odds ratio (log scale, 95% CI). Green = p < .05")
ax.set_title("What predicts formal saving? Logistic regression", loc="left")
fig.tight_layout(); fig.savefig(OUT / "fig3_logit_forest.png", dpi=170); plt.close(fig)

print(json.dumps({k: R[k] for k in ["n", "alpha_trust", "alpha_fin", "alpha_trust_if_trust3_not_reversed",
                                    "H1_gender_chama", "H3_trust_by_saver", "H5_momo_by_county"]}, indent=1, default=str))
print(json.dumps({k: v for k, v in R["H4_literacy_by_educ"].items() if k != "tukey"}, indent=1))
print(pd.DataFrame(R["H4_literacy_by_educ"]["tukey"]))
print({k: v for k, v in R["logit"].items() if k != "table"})
print(pd.DataFrame(R["logit"]["table"]).T)
print({k: v for k, v in R["ols"].items() if k not in ("table",)})
print(pd.DataFrame(R["ols"]["table"]).T)
print(R["profile"], R["age_mean_sd"], R["income_median"], R["saving_median"], R["H2_gender_formal"], R["H3b_literacy_by_saver"])
