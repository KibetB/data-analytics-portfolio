# Survey Analysis Case Study (SPSS)

**Why do young Kenyans save formally or not?** A full survey-analysis workflow on 600 respondents aged 18–35: data preparation, scale reliability, hypothesis testing and regression modelling, ending in recommendations for a SACCO.

📄 **Read the case study:** [`CASE_STUDY.md`](CASE_STUDY.md) (also as [`CASE_STUDY.pdf`](CASE_STUDY.pdf))

## Headline findings

- **Financial literacy is the strongest lever:** each extra point raises the odds of formal saving 2.4x and the amount saved by about 37%.
- **Trust affects *whether* people save formally (OR 1.8), but not *how much*.**
- **Chama members are 1.75x more likely to save formally**, so informal groups feed formal saving rather than competing with it.
- **Education's effect vanishes once literacy is controlled**, suggesting it works through practical money skills.

## Files

| File | Contents |
|---|---|
| `data/youth_finance_survey.sav` | SPSS dataset with variable labels, value labels and measurement levels |
| `spss/analysis.sps` | Complete SPSS syntax: cleaning, reliability, factor analysis, χ², t-tests, ANOVA + Tukey, Kruskal-Wallis, logistic and linear regression |
| `src/02_replicate_analysis.py` | Python replication of every test, so results can be checked without an SPSS licence |
| `outputs/results.json` | Every statistic quoted in the case study |
| `outputs/fig*.png` | Figures used in the report |

## Methods

Reverse coding · Cronbach's α · exploratory factor analysis · chi-square with φ · independent t-tests with Cohen's d · one-way ANOVA with η² and Tukey HSD · Kruskal-Wallis · binary logistic regression (Nagelkerke R², Hosmer-Lemeshow) · multiple linear regression (VIF, Durbin-Watson, Breusch-Pagan, HC3 robust SEs).

> The data is simulated to resemble a cleaned KoboToolbox export. It demonstrates the workflow, not facts about Kenya.

## Run it

**SPSS:** open `data/youth_finance_survey.sav`, then open and run `spss/analysis.sps`.
**Python:** `pip install pandas numpy scipy statsmodels pyreadstat matplotlib` then `python src/02_replicate_analysis.py`.
