
-- ==========================================
-- FinGuard: Financial Risk Detection
-- Trigger for large expense transactions
-- ==========================================

CREATE OR REPLACE TRIGGER trg_detect_expense_risk
AFTER INSERT ON transactions
FOR EACH ROW
WHEN (
    NEW.transaction_type = 'EXPENSE'
    AND NEW.transaction_status = 'COMPLETED'
)
DECLARE
    v_risk_level  VARCHAR2(10);
    v_risk_reason VARCHAR2(500);
BEGIN
    IF :NEW.amount >= 10000 THEN
        v_risk_level := 'HIGH';
        v_risk_reason :=
            'Large expense detected: amount is at least INR 10000';

    ELSIF :NEW.amount >= 5000 THEN
        v_risk_level := 'MEDIUM';
        v_risk_reason :=
            'Significant expense detected: amount is at least INR 5000';
    END IF;

    IF v_risk_level IS NOT NULL THEN
        INSERT INTO transaction_risk_alerts (
            transaction_id,
            risk_level,
            risk_reason,
            alert_status
        )
        VALUES (
            :NEW.transaction_id,
            v_risk_level,
            v_risk_reason,
            'OPEN'
        );
    END IF;
END trg_detect_expense_risk;
/
