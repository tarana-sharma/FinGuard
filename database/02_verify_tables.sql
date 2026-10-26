
-- FinGuard Database Verification
-- Verify the connected user and database

SELECT
    USER AS connected_user,
    SYS_CONTEXT('USERENV', 'CON_NAME') AS database_name
FROM dual;

-- Display all FinGuard tables

SELECT
    table_name
FROM user_tables
WHERE table_name IN (
    'APP_USERS',
    'FINANCIAL_ACCOUNTS',
    'TRANSACTIONS',
    'BUDGETS',
    'SAVINGS_GOALS',
    'TRANSACTION_RISK_ALERTS',
    'AUDIT_LOGS'
)
ORDER BY table_name;

-- Count the existing FinGuard tables

SELECT COUNT(*) AS total_tables
FROM user_tables
WHERE table_name IN (
    'APP_USERS',
    'FINANCIAL_ACCOUNTS',
    'TRANSACTIONS',
    'BUDGETS',
    'SAVINGS_GOALS',
    'TRANSACTION_RISK_ALERTS',
    'AUDIT_LOGS'
);
