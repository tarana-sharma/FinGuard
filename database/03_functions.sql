
-- FinGuard PL/SQL Functions
-- Function 1: Get financial account balance

CREATE OR REPLACE FUNCTION get_account_balance (
    p_account_id IN NUMBER
)
RETURN NUMBER
IS
    v_balance NUMBER(15,2);
BEGIN
    SELECT balance
    INTO v_balance
    FROM financial_accounts
    WHERE account_id = p_account_id;

    RETURN v_balance;

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(
            -20001,
            'Financial account not found'
        );
END get_account_balance;
/
