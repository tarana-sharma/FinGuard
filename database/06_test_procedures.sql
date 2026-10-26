
-- FinGuard: Test the RECORD_EXPENSE procedure
-- First expense test: Rs. 2000

BEGIN
    record_expense(
        p_account_id  => 1,
        p_amount      => 2000,
        p_category    => 'Shopping',
        p_description => 'Test shopping expense'
    );
END;
/

-- Verify the updated account balance
SELECT account_id, account_name, balance
FROM financial_accounts
WHERE account_id = 1;

-- Verify the transaction record
SELECT transaction_id, account_id,
       transaction_type, amount, category,
       transaction_status
FROM transactions
WHERE account_id = 1
ORDER BY transaction_id DESC;


-- Test 2: Insufficient balance handling
-- Expected result: ORA-20004

BEGIN
    record_expense(
        p_account_id  => 1,
        p_amount      => 20000,
        p_category    => 'Shopping',
        p_description => 'Insufficient balance test'
    );
END;
/


-- Test 3: Record Income
-- Expected: Balance increases from 13000 to 18000

BEGIN
    record_income(
        p_account_id  => 1,
        p_amount      => 5000,
        p_category    => 'Salary',
        p_description => 'Test salary income'
    );
END;
/


-- Test 4: Invalid Income Amount
-- Expected error: ORA-20006

BEGIN
    record_income(
        p_account_id  => 1,
        p_amount      => -1000,
        p_category    => 'Salary',
        p_description => 'Invalid negative income test'
    );
END;
/
