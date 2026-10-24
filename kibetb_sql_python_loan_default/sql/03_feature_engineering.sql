-- =====================================================================
-- Feature engineering: one row per loan, ready for modelling.
-- Shows CTEs, conditional aggregation, and leakage-safe window functions
-- (a loan only "sees" the customer's PREVIOUS loans, never its own outcome).
-- =====================================================================
WITH wallet AS (                       -- 6-month wallet behaviour per customer
    SELECT customer_id,
           COUNT(*)                                                    AS tx_count,
           SUM(CASE WHEN tx_type = 'deposit'    THEN amount_kes ELSE 0 END) AS total_deposits,
           SUM(CASE WHEN tx_type = 'withdrawal' THEN amount_kes ELSE 0 END) AS total_withdrawals,
           SUM(CASE WHEN tx_type = 'bill_pay'   THEN 1 ELSE 0 END)          AS bill_payments,
           COUNT(DISTINCT strftime('%Y-%m', tx_date))                  AS active_months
    FROM transactions
    GROUP BY customer_id
),
loan_history AS (                      -- prior behaviour, computed per loan
    SELECT l.*,
           ROW_NUMBER() OVER w - 1                                     AS prior_loans,
           COALESCE(SUM(defaulted) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING
                                             AND 1 PRECEDING), 0)      AS prior_defaults
    FROM loans l
    WINDOW w AS (PARTITION BY customer_id ORDER BY issue_date, loan_id)
)
SELECT h.loan_id,
       h.issue_date,                                       -- used for time-based split
       h.defaulted,                                        -- target
       h.principal_kes,
       h.term_days,
       h.interest_rate,
       h.prior_loans,
       h.prior_defaults,
       c.age,
       c.gender,
       c.occupation,
       c.county,
       c.months_on_network,
       c.monthly_income_kes,
       ROUND(h.principal_kes / c.monthly_income_kes, 3)    AS loan_to_income,
       COALESCE(w.tx_count, 0)                             AS tx_count,
       ROUND(COALESCE(w.total_deposits, 0) / c.monthly_income_kes, 3)  AS deposits_to_income,
       ROUND(COALESCE(w.total_withdrawals, 0) / NULLIF(w.total_deposits, 0), 3) AS withdraw_deposit_ratio,
       COALESCE(w.bill_payments, 0)                        AS bill_payments,
       COALESCE(w.active_months, 0)                        AS active_months
FROM loan_history h
JOIN customers  c USING (customer_id)
LEFT JOIN wallet w USING (customer_id);
