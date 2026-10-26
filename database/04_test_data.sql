
-- FinGuard: Test Data
-- Step 1: Create a sample user

INSERT INTO app_users (
    full_name,
    email,
    password_hash
)
VALUES (
    'FinGuard Test User',
    'finguard.test@example.com',
    'TEST_ONLY_NOT_A_REAL_PASSWORD_HASH'
);

COMMIT;


-- Step 2: Create a sample financial account

INSERT INTO financial_accounts (
    user_id,
    account_name,
    account_type,
    balance
)
VALUES (
    1,
    'My Savings Account',
    'SAVINGS',
    15000
);

COMMIT;


-- Step 3: Create a second financial account
-- This account will be used for transfer testing

INSERT INTO financial_accounts (
    user_id,
    account_name,
    account_type,
    balance
)
VALUES (
    1,
    'My Cash Wallet',
    'CASH',
    2000
);

COMMIT;
