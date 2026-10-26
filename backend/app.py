import os
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
import oracledb
from pathlib import Path
from flask import send_from_directory
from flask import Flask, jsonify, request
from db import get_connection

load_dotenv()

app = Flask(__name__)

# ==========================================
# Flask Authentication Configuration
# ==========================================

secret_key = os.getenv("FLASK_SECRET_KEY")

if not secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing from backend/.env"
    )

app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)


# ==========================================
# Authentication Helper Functions
# ==========================================

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "status": "error",
                "message": "Please log in to continue"
            }), 401

        return route_function(*args, **kwargs)

    return wrapper


def get_current_user_id():
    return session.get("user_id")




FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.route("/dashboard")
def frontend_dashboard():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/style.css")
def frontend_css():
    return send_from_directory(FRONTEND_DIR, "style.css")

@app.route("/script.js")
def frontend_js():
    return send_from_directory(FRONTEND_DIR, "script.js")

@app.route("/")
def home():
    return jsonify({
        "application": "FinGuard",
        "message": "FinGuard Backend is Running!",
        "status": "success"
    })


@app.route("/api/db-test")
def database_test():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT USER FROM DUAL"
                )
                result = cursor.fetchone()

        return jsonify({
            "status": "success",
            "message": "Oracle Database Connected!",
            "database_user": result[0]
        })

    except Exception:
        app.logger.exception("Database connection test failed")
        return jsonify({
            "status": "error",
            "message": "Database connection failed. Check server logs."
        }), 500


# API 1: Retrieve Financial Accounts
@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT account_id, account_name,
                           account_type, balance
                    FROM financial_accounts
                    WHERE user_id = :user_id
                    ORDER BY account_id
                """, {"user_id": 1})

                accounts = [
                    {
                        "account_id": row[0],
                        "account_name": row[1],
                        "account_type": row[2],
                        "balance": float(row[3])
                    }
                    for row in cursor.fetchall()
                ]

        return jsonify({
            "status": "success",
            "accounts": accounts
        })

    except Exception:
        app.logger.exception("Failed to retrieve accounts")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve accounts"
        }), 500


# API 2: Dashboard Summary
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*), NVL(SUM(balance), 0)
                    FROM financial_accounts
                    WHERE user_id = :user_id
                """, {"user_id": 1})

                account_count, total_balance = cursor.fetchone()

        return jsonify({
            "status": "success",
            "dashboard": {
                "total_accounts": account_count,
                "total_balance": float(total_balance),
                "currency": "INR"
            }
        })

    except Exception:
        app.logger.exception("Failed to retrieve dashboard")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve dashboard"
        }), 500


# API 3: Transaction History
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        t.transaction_id,
                        t.account_id,
                        t.transaction_type,
                        t.amount,
                        t.category,
                        t.description,
                        t.transaction_date,
                        t.transaction_status
                    FROM transactions t
                    JOIN financial_accounts a
                      ON t.account_id = a.account_id
                    WHERE a.user_id = :user_id
                    ORDER BY t.transaction_date DESC,
                             t.transaction_id DESC
                """, {"user_id": 1})

                transactions = [
                    {
                        "transaction_id": row[0],
                        "account_id": row[1],
                        "transaction_type": row[2],
                        "amount": float(row[3]),
                        "category": row[4],
                        "description": row[5],
                        "transaction_date": row[6].isoformat(),
                        "transaction_status": row[7]
                    }
                    for row in cursor.fetchall()
                ]

        return jsonify({
            "status": "success",
            "transactions": transactions
        })

    except Exception:
        app.logger.exception("Failed to retrieve transactions")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve transactions"
        }), 500


# Helper: Validate Transaction Input
def validate_transaction_data(data):
    from decimal import Decimal, InvalidOperation

    if not isinstance(data, dict):
        return None, "A JSON object is required"

    try:
        account_id = int(data.get("account_id"))
        amount = Decimal(str(data.get("amount")))
    except (TypeError, ValueError, InvalidOperation):
        return None, "Invalid account ID or amount"

    category = data.get("category")
    description = data.get("description", "")

    if (
        account_id <= 0
        or not amount.is_finite()
        or amount <= 0
        or amount.as_tuple().exponent < -2
        or amount > Decimal("9999999999999.99")
    ):
        return None, "Amount must be positive with at most 2 decimal places"

    if not isinstance(category, str) or not category.strip():
        return None, "Category is required"

    if len(category.strip()) > 50:
        return None, "Category must be at most 50 characters"

    if not isinstance(description, str) or len(description) > 255:
        return None, "Description must be at most 255 characters"

    return {
        "account_id": account_id,
        "amount": amount,
        "category": category.strip(),
        "description": description
    }, None


# API 4: Add Income
@app.route("/api/income", methods=["POST"])
def add_income():
    data, error = validate_transaction_data(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({
            "status": "error",
            "message": error
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 1
                    FROM financial_accounts
                    WHERE account_id = :account_id
                      AND user_id = :user_id
                """, {
                    "account_id": data["account_id"],
                    "user_id": 1
                })

                if cursor.fetchone() is None:
                    return jsonify({
                        "status": "error",
                        "message": "Account not found"
                    }), 404

                cursor.callproc("RECORD_INCOME", [
                    data["account_id"],
                    data["amount"],
                    data["category"],
                    data["description"]
                ])

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Income recorded successfully"
        }), 201

    except Exception:
        app.logger.exception("Failed to record income")
        return jsonify({
            "status": "error",
            "message": "Unable to record income"
        }), 500


# API 5: Add Expense
@app.route("/api/expense", methods=["POST"])
def add_expense():
    data, error = validate_transaction_data(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({
            "status": "error",
            "message": error
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 1
                    FROM financial_accounts
                    WHERE account_id = :account_id
                      AND user_id = :user_id
                """, {
                    "account_id": data["account_id"],
                    "user_id": 1
                })

                if cursor.fetchone() is None:
                    return jsonify({
                        "status": "error",
                        "message": "Account not found"
                    }), 404

                cursor.callproc("RECORD_EXPENSE", [
                    data["account_id"],
                    data["amount"],
                    data["category"],
                    data["description"]
                ])

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Expense recorded successfully"
        }), 201

    except Exception:
        app.logger.exception("Failed to record expense")
        return jsonify({
            "status": "error",
            "message": "Unable to record expense"
        }), 500


# API 6: Transfer Money Between Accounts
@app.route("/api/transfer", methods=["POST"])
def transfer_money():
    from decimal import Decimal, InvalidOperation

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON object is required"
        }), 400

    try:
        from_account = int(data.get("from_account_id"))
        to_account = int(data.get("to_account_id"))
        amount = Decimal(str(data.get("amount")))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify({
            "status": "error",
            "message": "Invalid account or amount"
        }), 400

    description = data.get("description", "")

    if from_account <= 0 or to_account <= 0:
        return jsonify({
            "status": "error",
            "message": "Invalid account IDs"
        }), 400

    if from_account == to_account:
        return jsonify({
            "status": "error",
            "message": "Select two different accounts"
        }), 400

    if (
        not amount.is_finite()
        or amount <= 0
        or amount.as_tuple().exponent < -2
        or amount > Decimal("9999999999999.99")
    ):
        return jsonify({
            "status": "error",
            "message": "Invalid transfer amount"
        }), 400

    if not isinstance(description, str) or len(description) > 255:
        return jsonify({
            "status": "error",
            "message": "Description must be at most 255 characters"
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM financial_accounts
                    WHERE user_id = :user_id
                      AND account_id IN (:from_id, :to_id)
                """, {
                    "user_id": 1,
                    "from_id": from_account,
                    "to_id": to_account
                })

                if cursor.fetchone()[0] != 2:
                    return jsonify({
                        "status": "error",
                        "message": "One or both accounts are unavailable"
                    }), 404

                cursor.callproc("TRANSFER_FUNDS", [
                    from_account,
                    to_account,
                    amount,
                    description
                ])

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Transfer completed successfully"
        }), 201

    except oracledb.DatabaseError as error:
        app.logger.exception("Transfer failed")

        error_obj = error.args[0]
        error_code = getattr(error_obj, "code", None)

        if error_code == 20014:
            return jsonify({
                "status": "error",
                "message": "Insufficient funds for transfer"
            }), 400

        return jsonify({
            "status": "error",
            "message": "Transfer could not be completed"
        }), 500

    except Exception:
        app.logger.exception("Unexpected transfer failure")
        return jsonify({
            "status": "error",
            "message": "Transfer could not be completed"
        }), 500


# API 7: Get Monthly Budgets
@app.route("/api/budgets", methods=["GET"])
def get_budgets():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        b.budget_id,
                        b.category,
                        b.monthly_limit,
                        b.budget_month,
                        NVL((
                            SELECT SUM(t.amount)
                            FROM transactions t
                            JOIN financial_accounts a
                              ON t.account_id = a.account_id
                            WHERE a.user_id = b.user_id
                              AND t.transaction_type = 'EXPENSE'
                              AND t.transaction_status = 'COMPLETED'
                              AND UPPER(t.category) = UPPER(b.category)
                              AND t.transaction_date >=
                                  CAST(b.budget_month AS TIMESTAMP)
                              AND t.transaction_date <
                                  CAST(ADD_MONTHS(b.budget_month, 1)
                                  AS TIMESTAMP)
                        ), 0) AS spent
                    FROM budgets b
                    WHERE b.user_id = :user_id
                      AND b.budget_month = TRUNC(SYSDATE, 'MM')
                    ORDER BY b.category
                """, {"user_id": 1})

                budgets = []
                for row in cursor.fetchall():
                    limit = float(row[2])
                    spent = float(row[4])

                    budgets.append({
                        "budget_id": row[0],
                        "category": row[1],
                        "monthly_limit": limit,
                        "budget_month": row[3].isoformat(),
                        "spent": spent,
                        "remaining": limit - spent,
                        "percentage": round(
                            (spent / limit) * 100, 2
                        )
                    })

        return jsonify({
            "status": "success",
            "budgets": budgets
        })

    except Exception:
        app.logger.exception("Failed to retrieve budgets")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve budgets"
        }), 500


# API 8: Create or Update Monthly Budget
@app.route("/api/budgets", methods=["POST"])
def create_budget():
    from decimal import Decimal, InvalidOperation

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON object is required"
        }), 400

    category = data.get("category")

    try:
        limit = Decimal(str(data.get("monthly_limit")))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify({
            "status": "error",
            "message": "Invalid budget amount"
        }), 400

    if not isinstance(category, str) or not category.strip():
        return jsonify({
            "status": "error",
            "message": "Budget category is required"
        }), 400

    category = category.strip()

    if len(category) > 50:
        return jsonify({
            "status": "error",
            "message": "Category must be at most 50 characters"
        }), 400

    if (
        not limit.is_finite()
        or limit <= 0
        or limit.as_tuple().exponent < -2
        or limit > Decimal("9999999999999.99")
    ):
        return jsonify({
            "status": "error",
            "message": "Invalid monthly budget limit"
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    MERGE INTO budgets b
                    USING (
                        SELECT :user_id AS user_id,
                               :category AS category,
                               TRUNC(SYSDATE, 'MM') AS budget_month
                        FROM dual
                    ) src
                    ON (
                        b.user_id = src.user_id
                        AND b.category = src.category
                        AND b.budget_month = src.budget_month
                    )
                    WHEN MATCHED THEN
                        UPDATE SET b.monthly_limit = :monthly_limit
                    WHEN NOT MATCHED THEN
                        INSERT (
                            user_id, category,
                            monthly_limit, budget_month
                        )
                        VALUES (
                            src.user_id, src.category,
                            :monthly_limit, src.budget_month
                        )
                """, {
                    "user_id": 1,
                    "category": category,
                    "monthly_limit": limit
                })

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Monthly budget saved successfully"
        }), 201

    except Exception:
        app.logger.exception("Failed to save budget")
        return jsonify({
            "status": "error",
            "message": "Unable to save budget"
        }), 500


# ==========================================
# FIN GUARD - SAVINGS GOALS APIs
# ==========================================

from decimal import Decimal, InvalidOperation


def validate_goal_amount(value):
    try:
        amount = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return None

    if (
        not amount.is_finite()
        or amount <= 0
        or amount.as_tuple().exponent < -2
        or amount > Decimal("9999999999999.99")
    ):
        return None

    return amount


# API 9: Retrieve Savings Goals
@app.route("/api/goals", methods=["GET"])
def get_savings_goals():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT goal_id, goal_name, target_amount,
                           saved_amount, target_date, goal_status
                    FROM savings_goals
                    WHERE user_id = :user_id
                    ORDER BY goal_id DESC
                """, {"user_id": 1})

                goals = []

                for row in cursor.fetchall():
                    target = float(row[2])
                    saved = float(row[3])

                    goals.append({
                        "goal_id": row[0],
                        "goal_name": row[1],
                        "target_amount": target,
                        "saved_amount": saved,
                        "target_date": (
                            row[4].isoformat() if row[4] else None
                        ),
                        "goal_status": row[5],
                        "remaining": max(target - saved, 0),
                        "percentage": round(
                            min(saved / target * 100, 100), 2
                        )
                    })

        return jsonify({
            "status": "success",
            "goals": goals
        })

    except Exception:
        app.logger.exception("Failed to retrieve savings goals")
        return jsonify({
            "status": "error",
            "message": "Unable to load savings goals"
        }), 500


# API 10: Create Savings Goal
@app.route("/api/goals", methods=["POST"])
def create_savings_goal():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON object is required"
        }), 400

    name = data.get("goal_name")
    target = validate_goal_amount(data.get("target_amount"))
    target_date = data.get("target_date") or None

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Goal name is required"
        }), 400

    if len(name.strip()) > 100:
        return jsonify({
            "status": "error",
            "message": "Goal name must be at most 100 characters"
        }), 400

    if target is None:
        return jsonify({
            "status": "error",
            "message": "Enter a valid target amount"
        }), 400

    if target_date is not None:
        if not isinstance(target_date, str):
            return jsonify({
                "status": "error",
                "message": "Invalid target date"
            }), 400

        from datetime import date

        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Use YYYY-MM-DD for target date"
            }), 400

        target_date = parsed_date

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO savings_goals (
                        user_id, goal_name, target_amount,
                        saved_amount, target_date, goal_status
                    )
                    VALUES (
                        :user_id, :goal_name, :target_amount,
                        0, :target_date, 'ACTIVE'
                    )
                """, {
                    "user_id": 1,
                    "goal_name": name.strip(),
                    "target_amount": target,
                    "target_date": target_date
                })

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Savings goal created successfully"
        }), 201

    except Exception:
        app.logger.exception("Failed to create savings goal")
        return jsonify({
            "status": "error",
            "message": "Unable to create savings goal"
        }), 500


# API 11: Add Savings to Goal
@app.route("/api/goals/<int:goal_id>/save", methods=["POST"])
def add_goal_savings(goal_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON object is required"
        }), 400

    amount = validate_goal_amount(data.get("amount"))

    if amount is None:
        return jsonify({
            "status": "error",
            "message": "Enter a valid savings amount"
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE savings_goals
                    SET saved_amount = saved_amount + :amount,
                        goal_status = CASE
                            WHEN saved_amount + :amount >= target_amount
                            THEN 'COMPLETED'
                            ELSE 'ACTIVE'
                        END
                    WHERE goal_id = :goal_id
                      AND user_id = :user_id
                      AND goal_status = 'ACTIVE'
                      AND saved_amount + :amount <= target_amount
                """, {
                    "amount": amount,
                    "goal_id": goal_id,
                    "user_id": 1
                })

                if cursor.rowcount == 0:
                    return jsonify({
                        "status": "error",
                        "message": "Goal unavailable or amount exceeds target"
                    }), 400

            connection.commit()

        return jsonify({
            "status": "success",
            "message": "Savings progress updated successfully"
        })

    except Exception:
        app.logger.exception("Failed to update savings goal")
        return jsonify({
            "status": "error",
            "message": "Unable to update savings goal"
        }), 500


# ==========================================
# API 12: Retrieve Financial Risk Alerts
# ==========================================

@app.route("/api/risk-alerts", methods=["GET"])
def get_risk_alerts():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        r.alert_id,
                        r.transaction_id,
                        r.risk_level,
                        r.risk_reason,
                        r.alert_status,
                        r.detected_at,
                        t.amount,
                        t.category,
                        a.account_name
                    FROM transaction_risk_alerts r
                    JOIN transactions t
                      ON r.transaction_id = t.transaction_id
                    JOIN financial_accounts a
                      ON t.account_id = a.account_id
                    WHERE a.user_id = :user_id
                    ORDER BY r.detected_at DESC,
                             r.alert_id DESC
                """, {"user_id": 1})

                alerts = []

                for row in cursor.fetchall():
                    alerts.append({
                        "alert_id": row[0],
                        "transaction_id": row[1],
                        "risk_level": row[2],
                        "risk_reason": row[3],
                        "alert_status": row[4],
                        "detected_at": (
                            row[5].isoformat()
                            if row[5] else None
                        ),
                        "amount": float(row[6]),
                        "category": row[7],
                        "account_name": row[8]
                    })

        return jsonify({
            "status": "success",
            "total_alerts": len(alerts),
            "alerts": alerts
        })

    except Exception:
        app.logger.exception("Failed to retrieve risk alerts")

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve risk alerts"
        }), 500


# ==========================================
# API: Financial Audit Logs
# ==========================================

@app.route("/api/audit-logs", methods=["GET"])
def get_audit_logs():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        l.log_id,
                        l.table_name,
                        l.record_id,
                        l.action_type,
                        l.old_value,
                        l.new_value,
                        l.action_timestamp
                    FROM audit_logs l
                    JOIN financial_accounts a
                      ON l.table_name = 'FINANCIAL_ACCOUNTS'
                     AND l.record_id = a.account_id
                    WHERE a.user_id = :user_id
                      AND l.user_id = :user_id
                    ORDER BY l.action_timestamp DESC,
                             l.log_id DESC
                    FETCH FIRST 50 ROWS ONLY
                """, {"user_id": 1})

                logs = []

                for row in cursor.fetchall():
                    logs.append({
                        "log_id": row[0],
                        "table_name": row[1],
                        "record_id": row[2],
                        "action_type": row[3],
                        "old_value": row[4].read()
                            if hasattr(row[4], "read")
                            else row[4],
                        "new_value": row[5].read()
                            if hasattr(row[5], "read")
                            else row[5],
                        "action_timestamp": (
                            row[6].isoformat()
                            if row[6] else None
                        )
                    })

        return jsonify({
            "status": "success",
            "total_logs": len(logs),
            "logs": logs
        })

    except Exception:
        app.logger.exception("Failed to retrieve audit logs")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve audit logs"
        }), 500


# ==========================================
# API: Register User
# ==========================================

@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.get_json(silent=True) or {}

    full_name = str(data.get("full_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if (
        not full_name
        or not email
        or not isinstance(password, str)
        or len(password) < 8
        or len(full_name) > 100
        or len(email) > 255
    ):
        return jsonify({
            "status": "error",
            "message": "Enter a valid name, email and password of at least 8 characters"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                user_id_var = cursor.var(int)

                cursor.execute("""
                    INSERT INTO app_users (
                        full_name, email, password_hash
                    )
                    VALUES (
                        :full_name, :email, :password_hash
                    )
                    RETURNING user_id INTO :new_user_id
                """, {
                    "full_name": full_name,
                    "email": email,
                    "password_hash": password_hash,
                    "new_user_id": user_id_var
                })

                user_id = int(user_id_var.getvalue()[0])
                connection.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful",
            "user_id": user_id
        }), 201

    except oracledb.IntegrityError as error:
        if "ORA-00001" in str(error):
            return jsonify({
                "status": "error",
                "message": "This email is already registered"
            }), 409
        app.logger.exception("Registration integrity error")
        return jsonify({
            "status": "error",
            "message": "Registration failed"
        }), 500

    except Exception:
        app.logger.exception("Registration failed")
        return jsonify({
            "status": "error",
            "message": "Registration failed"
        }), 500


# ==========================================
# API: Login User
# ==========================================

@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str):
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, full_name,
                           password_hash, account_status
                    FROM app_users
                    WHERE LOWER(email) = :email
                """, {"email": email})

                user = cursor.fetchone()

        if (
            not user
            or user[3] != "ACTIVE"
            or not check_password_hash(user[2], password)
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials or inactive account"
            }), 401

        session.clear()
        session["user_id"] = int(user[0])
        session["full_name"] = user[1]
        session.permanent = True

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "user_id": int(user[0]),
                "full_name": user[1],
                "email": email
            }
        })

    except Exception:
        app.logger.exception("Login failed")
        return jsonify({
            "status": "error",
            "message": "Login failed"
        }), 500


# ==========================================
# API: Logout User
# ==========================================

@app.route("/api/logout", methods=["POST"])
@login_required
def logout_user():
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    })


# ==========================================
# API: Current User
# ==========================================

@app.route("/api/me", methods=["GET"])
@login_required
def current_user():
    return jsonify({
        "status": "success",
        "user": {
            "user_id": get_current_user_id(),
            "full_name": session.get("full_name")
        }
    })


# ==========================================
# Authentication Frontend Routes
# ==========================================

@app.route("/login")
def login_page():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    return send_from_directory(frontend_dir, "login.html")


@app.route("/auth.css")
def auth_styles():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    return send_from_directory(frontend_dir, "auth.css")


@app.route("/auth.js")
def auth_scripts():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    return send_from_directory(frontend_dir, "auth.js")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
