
-- ==========================================
-- FinGuard - Account Balance Audit Logging
-- ==========================================

CREATE OR REPLACE TRIGGER trg_audit_account_balance
AFTER UPDATE OF balance ON financial_accounts
FOR EACH ROW
WHEN (OLD.balance <> NEW.balance)
BEGIN
    INSERT INTO audit_logs (
        user_id,
        table_name,
        record_id,
        action_type,
        old_value,
        new_value
    )
    VALUES (
        :NEW.user_id,
        'FINANCIAL_ACCOUNTS',
        :NEW.account_id,
        'UPDATE',
        'Balance: ' || TO_CHAR(:OLD.balance),
        'Balance: ' || TO_CHAR(:NEW.balance)
    );
END trg_audit_account_balance;
/
