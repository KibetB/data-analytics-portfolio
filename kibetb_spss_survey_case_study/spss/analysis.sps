* Encoding: UTF-8.
* =============================================================================
* Mobile Money, Trust and Saving Behaviour among Young Adults in Kenya
* SPSS syntax - full analysis pipeline. Run section by section or all at once.
* Open data/youth_finance_survey.sav first, or edit the path below.
* =============================================================================.

GET FILE='youth_finance_survey.sav'.
DATASET NAME survey WINDOW=FRONT.

* -----------------------------------------------------------------------------
* 1. DATA CLEANING AND PREPARATION
* -----------------------------------------------------------------------------.
* 1a. Check ranges and missing values.
DESCRIPTIVES VARIABLES=age income_kes monthly_saving_kes trust1 TO trust5 fin1 TO fin4
  /STATISTICS=MEAN STDDEV MIN MAX.
MISSING VALUES income_kes trust1 TO fin4 (-99).

* 1b. Reverse-code the negatively worded trust item.
RECODE trust3 (1=5) (2=4) (3=3) (4=2) (5=1) INTO trust3_r.
VARIABLE LABELS trust3_r 'Worry about losing money (reverse-coded)'.
VALUE LABELS trust3_r 1 'Strongly disagree' 2 'Disagree' 3 'Neutral' 4 'Agree' 5 'Strongly agree'.
EXECUTE.

* 1c. Derived variables.
COMPUTE log_income = LN(income_kes).
COMPUTE age_group = 1.
IF (age >= 24) age_group = 2.
IF (age >= 30) age_group = 3.
VALUE LABELS age_group 1 '18-23' 2 '24-29' 3 '30-35'.
VARIABLE LABELS log_income 'Natural log of monthly income' age_group 'Age group'.
EXECUTE.

* -----------------------------------------------------------------------------
* 2. SAMPLE PROFILE (Table 1)
* -----------------------------------------------------------------------------.
FREQUENCIES VARIABLES=county gender age_group educ employ chama formal_save momo_freq
  /ORDER=ANALYSIS.
DESCRIPTIVES VARIABLES=age income_kes monthly_saving_kes /STATISTICS=MEAN STDDEV MIN MAX.
EXAMINE VARIABLES=income_kes monthly_saving_kes /PLOT BOXPLOT HISTOGRAM NPPLOT
  /STATISTICS DESCRIPTIVES.

* -----------------------------------------------------------------------------
* 3. SCALE RELIABILITY (Cronbach's alpha) AND SCALE SCORES
* -----------------------------------------------------------------------------.
RELIABILITY /VARIABLES=trust1 trust2 trust3_r trust4 trust5
  /SCALE('Trust in mobile money') ALL /MODEL=ALPHA
  /STATISTICS=DESCRIPTIVE SCALE CORR /SUMMARY=TOTAL.

RELIABILITY /VARIABLES=fin1 fin2 fin3 fin4
  /SCALE('Financial literacy') ALL /MODEL=ALPHA
  /STATISTICS=DESCRIPTIVE SCALE CORR /SUMMARY=TOTAL.

* Mean scores, requiring at least 4 of 5 (trust) and 3 of 4 (literacy) items answered.
COMPUTE trust_score = MEAN.4(trust1, trust2, trust3_r, trust4, trust5).
COMPUTE fin_lit_score = MEAN.3(fin1, fin2, fin3, fin4).
VARIABLE LABELS trust_score 'Trust in mobile money (1-5)' fin_lit_score 'Financial literacy (1-5)'.
EXECUTE.

* Construct validity check: one factor per scale.
FACTOR /VARIABLES trust1 trust2 trust3_r trust4 trust5 fin1 fin2 fin3 fin4
  /PRINT INITIAL KMO EXTRACTION ROTATION
  /CRITERIA FACTORS(2) ITERATE(25) /EXTRACTION PAF /ROTATION PROMAX(4)
  /FORMAT SORT BLANK(.30).

* -----------------------------------------------------------------------------
* 4. HYPOTHESIS TESTS
* -----------------------------------------------------------------------------.
* H1: Chama membership differs by gender (chi-square test of independence).
CROSSTABS /TABLES=gender BY chama
  /STATISTICS=CHISQ PHI /CELLS=COUNT ROW EXPECTED ASRESID.

* H2: Formal saving differs by gender (chi-square).
CROSSTABS /TABLES=gender BY formal_save
  /STATISTICS=CHISQ PHI /CELLS=COUNT ROW.

* H3: Trust differs between savers and non-savers (independent-samples t-test).
T-TEST GROUPS=formal_save(0 1) /VARIABLES=trust_score fin_lit_score
  /ES DISPLAY(TRUE) /CRITERIA=CI(.95).

* H4: Financial literacy differs by education (one-way ANOVA + Tukey post-hoc).
ONEWAY fin_lit_score BY educ
  /STATISTICS DESCRIPTIVES HOMOGENEITY WELCH
  /POSTHOC=TUKEY GH ALPHA(0.05).

* H5: Mobile-money use frequency differs by county (Kruskal-Wallis; ordinal outcome).
NPAR TESTS /K-W=momo_freq BY county(1 3).

* H6: Relationships among key continuous variables (Pearson + Spearman).
CORRELATIONS /VARIABLES=trust_score fin_lit_score log_income monthly_saving_kes momo_freq
  /PRINT=TWOTAIL NOSIG.
NONPAR CORR /VARIABLES=trust_score fin_lit_score momo_freq /PRINT=SPEARMAN TWOTAIL.

* -----------------------------------------------------------------------------
* 5. MULTIVARIATE MODELS
* -----------------------------------------------------------------------------.
* 5a. Binary logistic regression: who saves formally?
LOGISTIC REGRESSION VARIABLES formal_save
  /METHOD=ENTER trust_score fin_lit_score log_income chama gender age educ
  /CONTRAST (educ)=Indicator(1)
  /CONTRAST (gender)=Indicator(1)
  /PRINT=GOODFIT CI(95)
  /CRITERIA=PIN(0.05) POUT(0.10) ITERATE(20) CUT(0.5).

* 5b. Multiple linear regression: how much do people save? (log-transformed outcome).
COMPUTE log_saving = LN(monthly_saving_kes + 1).
EXECUTE.
REGRESSION /DESCRIPTIVES MEAN STDDEV CORR
  /STATISTICS COEFF OUTS CI(95) R ANOVA COLLIN TOL
  /DEPENDENT log_saving
  /METHOD=ENTER trust_score fin_lit_score log_income chama age
  /SCATTERPLOT=(*ZRESID ,*ZPRED)
  /RESIDUALS DURBIN HISTOGRAM(ZRESID) NORMPROB(ZRESID).

* 5c. Heteroscedasticity check and robust (HC3) standard errors.
UNIANOVA log_saving WITH trust_score fin_lit_score log_income chama age
  /PRINT=PARAMETER HETERO(BP) ROBUST(HC3)
  /DESIGN=trust_score fin_lit_score log_income chama age.

* -----------------------------------------------------------------------------
* 6. CHARTS FOR THE REPORT
* -----------------------------------------------------------------------------.
GRAPH /BAR(GROUPED)=PCT BY educ BY formal_save.
GRAPH /ERRORBAR(CI 95)=fin_lit_score BY educ.
SAVE OUTFILE='youth_finance_survey_analysed.sav' /COMPRESSED.
