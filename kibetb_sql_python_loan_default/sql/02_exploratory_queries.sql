-- =====================================================================
-- Exploratory analysis: business questions answered in SQL
-- Each query is separated by a "-- name:" tag so Python can run it by name.
-- =====================================================================

-- name: portfolio_overview
-- Q1. How big is the loan book and what is the overall default rate?
SELECT COUNT(*)                              AS total_loans,
       COUNT(DISTINCT customer_id)           AS borrowers,
       ROUND(SUM(principal_kes) / 1e6, 1)    AS disbursed_kes_millions,
       ROUND(AVG(principal_kes), 0)          AS avg_loan_kes,
       ROUND(100.0 * AVG(defaulted), 2)      AS default_rate_pct
FROM loans;

-- name: default_by_occupation
-- Q2. Which customer segments carry the most risk? (JOIN + GROUP BY)
SELECT c.occupation,
       COUNT(*)                                   AS loans,
       ROUND(100.0 * AVG(l.defaulted), 1)         AS default_rate_pct,
       ROUND(SUM(l.principal_kes * l.defaulted)/1e6, 2) AS kes_lost_millions
FROM loans l
JOIN customers c USING (customer_id)
GROUP BY c.occupation
ORDER BY default_rate_pct DESC;

-- name: default_by_loan_to_income_band
-- Q3. Does borrowing a large share of income predict default? (CASE banding)
SELECT CASE
         WHEN l.principal_kes / c.monthly_income_kes < 0.25 THEN '1. <25% of income'
         WHEN l.principal_kes / c.monthly_income_kes < 0.50 THEN '2. 25-50%'
         WHEN l.principal_kes / c.monthly_income_kes < 1.00 THEN '3. 50-100%'
         ELSE '4. >100% of income'
       END                                        AS loan_to_income_band,
       COUNT(*)                                   AS loans,
       ROUND(100.0 * AVG(l.defaulted), 1)         AS default_rate_pct
FROM loans l
JOIN customers c USING (customer_id)
GROUP BY loan_to_income_band
ORDER BY loan_to_income_band;

-- name: county_ranking
-- Q4. Rank counties by default rate (window function RANK)
SELECT county,
       loans,
       default_rate_pct,
       RANK() OVER (ORDER BY default_rate_pct DESC) AS risk_rank
FROM (
    SELECT c.county,
           COUNT(*)                           AS loans,
           ROUND(100.0 * AVG(l.defaulted), 2) AS default_rate_pct
    FROM loans l JOIN customers c USING (customer_id)
    GROUP BY c.county
) t
ORDER BY risk_rank;

-- name: monthly_trend
-- Q5. Monthly disbursement with a 3-month moving average default rate
WITH m AS (
    SELECT strftime('%Y-%m', issue_date) AS month,
           COUNT(*)                      AS loans,
           AVG(defaulted)                AS dr
    FROM loans GROUP BY month
)
SELECT month, loans,
       ROUND(100 * dr, 2) AS default_rate_pct,
       ROUND(100 * AVG(dr) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                          AS default_rate_3m_avg
FROM m ORDER BY month;
