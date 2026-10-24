-- Normalised schema for the mobile-lending database
CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    age                 INTEGER NOT NULL,
    gender              TEXT CHECK (gender IN ('F','M')),
    county              TEXT,
    occupation          TEXT,
    months_on_network   INTEGER,
    signup_date         DATE,
    monthly_income_kes  REAL
);

CREATE TABLE loans (
    loan_id        INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
    issue_date     DATE,
    principal_kes  REAL,
    term_days      INTEGER,
    interest_rate  REAL,
    defaulted      INTEGER CHECK (defaulted IN (0,1))
);

CREATE TABLE transactions (
    tx_id        INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    tx_date      DATE,
    tx_type      TEXT,
    amount_kes   REAL
);

CREATE INDEX idx_loans_customer ON loans(customer_id);
CREATE INDEX idx_tx_customer    ON transactions(customer_id);
