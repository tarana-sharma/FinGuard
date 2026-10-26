
-- FinGuard PL/SQL Procedures
-- Procedure 1: Record an expense

CREATE OR REPLACE PROCEDURE record_expense (
    p_account_id IN NUMBER,
    p_amount IN NUMBER,
    p_category IN VARCHAR2,
    p_description IN VARCHAR2
)
IS
    v_balance financial_accounts.balance%TYPE;
BEGIN
    -- Validate the expense amount
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE_APPLICATION_ERROR(
            -20002,
            'Expense amount must be greater than zero'
        );
    END IF;

    -- Validate the category
    IF TRIM(p_category) IS NULL THEN
        RAISE_APPLICATION_ERROR(
            -20003,
            'Expense category is required'
        );
    END IF;

    -- Lock the account while processing
    SELECT balance
    INTO v_balance
    FROM financial_accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    -- Check sufficient balance
    IF v_balance < p_amount THEN
        RAISE_APPLICATION_ERROR(
            -20004,
            'Insufficient account balance'
        );
    END IF;

    -- Deduct the expense amount
    UPDATE financial_accounts
    SET balance = balance - p_amount
    WHERE account_id = p_account_id;

    -- Record the expense transaction
    INSERT INTO transactions (
        account_id,
        transaction_type,
        amount,
        category,
        description,
        transaction_status
    )
    VALUES (
        p_account_id,
        'EXPENSE',
        p_amount,
        TRIM(p_category),
        p_description,
        'COMPLETED'
    );

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(
            -20005,
            'Financial account not found'
        );
END record_expense;
/


-- Procedure 2: Record Income

CREATE OR REPLACE PROCEDURE record_income (
    p_account_id IN NUMBER,
    p_amount IN NUMBER,
    p_category IN VARCHAR2,
    p_description IN VARCHAR2
)
IS
    v_balance financial_accounts.balance%TYPE;
BEGIN
    -- Validate income amount
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE_APPLICATION_ERROR(
            -20006,
            'Income amount must be greater than zero'
        );
    END IF;

    -- Validate category
    IF TRIM(p_category) IS NULL THEN
        RAISE_APPLICATION_ERROR(
            -20007,
            'Income category is required'
        );
    END IF;

    -- Lock the account
    SELECT balance
    INTO v_balance
    FROM financial_accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    -- Update account balance
    UPDATE financial_accounts
    SET balance = balance + p_amount
    WHERE account_id = p_account_id;

    -- Record income transaction
    INSERT INTO transactions (
        account_id,
        transaction_type,
        amount,
        category,
        description,
        transaction_status
    )
    VALUES (
        p_account_id,
        'INCOME',
        p_amount,
        TRIM(p_category),
        p_description,
        'COMPLETED'
    );

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(
            -20008,
            'Financial account not found'
        );
END record_income;
/


-- Procedure 3: Transfer Funds Between Accounts

CREATE OR REPLACE PROCEDURE transfer_funds (
    p_from_account_id IN NUMBER,
    p_to_account_id   IN NUMBER,
    p_amount          IN NUMBER,
    p_description     IN VARCHAR2
)
IS
    v_from_balance financial_accounts.balance%TYPE;
    v_from_user_id financial_accounts.user_id%TYPE;
    v_to_user_id financial_accounts.user_id%TYPE;
    v_locked_id financial_accounts.account_id%TYPE;
BEGIN
    -- Step 1: Validate transfer amount
    IF p_amount IS NULL OR p_amount <= 0
       OR p_amount <> ROUND(p_amount, 2) THEN
        RAISE_APPLICATION_ERROR(
            -20009,
            'Transfer amount must be positive with at most 2 decimal places'
        );
    END IF;

    -- Step 2: Validate account IDs
    IF p_from_account_id IS NULL
       OR p_to_account_id IS NULL
       OR p_from_account_id = p_to_account_id THEN
        RAISE_APPLICATION_ERROR(
            -20010,
            'Source and destination must be different accounts'
        );
    END IF;

    -- Step 3: Lock both accounts in a consistent order
    -- This helps reduce deadlocks during concurrent transfers
    FOR acc IN (
        SELECT account_id
        FROM financial_accounts
        WHERE account_id IN (
            p_from_account_id,
            p_to_account_id
        )
        ORDER BY account_id
    )
    LOOP
        SELECT account_id
        INTO v_locked_id
        FROM financial_accounts
        WHERE account_id = acc.account_id
        FOR UPDATE;
    END LOOP;

    -- Step 4: Retrieve source account details
    BEGIN
        SELECT balance, user_id
        INTO v_from_balance, v_from_user_id
        FROM financial_accounts
        WHERE account_id = p_from_account_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(
                -20011,
                'Source account not found'
            );
    END;

    -- Step 5: Retrieve destination account owner
    BEGIN
        SELECT user_id
        INTO v_to_user_id
        FROM financial_accounts
        WHERE account_id = p_to_account_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(
                -20012,
                'Destination account not found'
            );
    END;

    -- Step 6: Ensure both accounts have the same owner
    IF v_from_user_id <> v_to_user_id THEN
        RAISE_APPLICATION_ERROR(
            -20013,
            'Transfer between different users is not allowed'
        );
    END IF;

    -- Step 7: Check available balance
    IF v_from_balance < p_amount THEN
        RAISE_APPLICATION_ERROR(
            -20014,
            'Insufficient funds for transfer'
        );
    END IF;

    -- Step 8: Deduct from source account
    UPDATE financial_accounts
    SET balance = balance - p_amount
    WHERE account_id = p_from_account_id;

    -- Step 9: Add to destination account
    UPDATE financial_accounts
    SET balance = balance + p_amount
    WHERE account_id = p_to_account_id;

    -- Step 10: Record the transfer
    INSERT INTO transactions (
        account_id,
        destination_account_id,
        transaction_type,
        amount,
        category,
        description,
        transaction_status
    )
    VALUES (
        p_from_account_id,
        p_to_account_id,
        'TRANSFER',
        p_amount,
        'Transfer',
        p_description,
        'COMPLETED'
    );

END transfer_funds;
/
