
const formatMoney = (amount) => {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2
    }).format(Number(amount) || 0);
};

async function fetchJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
    }

    const data = await response.json();

    if (data.status !== "success") {
        throw new Error(data.message || "Unable to load data");
    }

    return data;
}

function renderAccounts(accounts) {
    const container = document.getElementById("accountsList");
    container.replaceChildren();

    if (!accounts.length) {
        container.textContent = "No accounts available.";
        return;
    }

    accounts.forEach(account => {
        const item = document.createElement("div");
        item.className = "account-item";

        const left = document.createElement("div");
        left.className = "account-left";

        const icon = document.createElement("div");
        icon.className = "account-icon";
        icon.textContent = account.account_type === "CASH" ? "◈" : "▣";

        const details = document.createElement("div");

        const name = document.createElement("div");
        name.className = "account-name";
        name.textContent = account.account_name;

        const type = document.createElement("div");
        type.className = "account-type";
        type.textContent = account.account_type;

        details.append(name, type);
        left.append(icon, details);

        const balance = document.createElement("div");
        balance.className = "account-balance";
        balance.textContent = formatMoney(account.balance);

        item.append(left, balance);
        container.appendChild(item);
    });
}

function renderTransactions(transactions) {
    const body = document.getElementById("transactionsBody");
    body.replaceChildren();

    if (!transactions.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = "No transactions recorded yet.";
        row.appendChild(cell);
        body.appendChild(row);
        return;
    }

    transactions.slice(0, 10).forEach(tx => {
        const row = document.createElement("tr");

        const nameCell = document.createElement("td");
        const name = document.createElement("div");
        name.className = "transaction-name";
        name.textContent = tx.transaction_type;

        const description = document.createElement("div");
        description.className = "transaction-description";
        description.textContent = tx.description || "No description";

        nameCell.append(name, description);

        const categoryCell = document.createElement("td");
        categoryCell.textContent = tx.category;

        const dateCell = document.createElement("td");
        dateCell.textContent = new Date(
            tx.transaction_date
        ).toLocaleDateString("en-IN");

        const statusCell = document.createElement("td");
        const status = document.createElement("span");
        status.className = "status-pill";
        status.textContent = tx.transaction_status;
        statusCell.appendChild(status);

        const amountCell = document.createElement("td");
        const isIncome = tx.transaction_type === "INCOME";
        const isExpense = tx.transaction_type === "EXPENSE";

        amountCell.className = isIncome
            ? "amount-income"
            : isExpense
                ? "amount-expense"
                : "";

        amountCell.textContent =
            (isIncome ? "+" : isExpense ? "−" : "") +
            formatMoney(tx.amount);

        row.append(
            nameCell,
            categoryCell,
            dateCell,
            statusCell,
            amountCell
        );

        body.appendChild(row);
    });
}

function renderCashflow(transactions) {
    let income = 0;
    let expense = 0;

    transactions.forEach(tx => {
        if (tx.transaction_status !== "COMPLETED") return;

        if (tx.transaction_type === "INCOME") {
            income += Number(tx.amount);
        } else if (tx.transaction_type === "EXPENSE") {
            expense += Number(tx.amount);
        }
    });

    document.getElementById("totalIncome").textContent =
        formatMoney(income);

    document.getElementById("totalExpense").textContent =
        formatMoney(expense);

    document.getElementById("incomeLabel").textContent =
        formatMoney(income);

    document.getElementById("expenseLabel").textContent =
        formatMoney(expense);

    const maximum = Math.max(income, expense, 1);

    document.getElementById("incomeBar").style.width =
        `${(income / maximum) * 100}%`;

    document.getElementById("expenseBar").style.width =
        `${(expense / maximum) * 100}%`;
}

async function loadDashboard() {
    const errorBox = document.getElementById("errorMessage");
    errorBox.hidden = true;

    try {
        const [dashboardData, accountsData, transactionsData] =
            await Promise.all([
                fetchJSON("/api/dashboard"),
                fetchJSON("/api/accounts"),
                fetchJSON("/api/transactions")
            ]);

        const summary = dashboardData.dashboard;

        document.getElementById("totalBalance").textContent =
            formatMoney(summary.total_balance);

        document.getElementById("totalAccounts").textContent =
            summary.total_accounts;

        renderAccounts(accountsData.accounts);
        renderTransactions(transactionsData.transactions);
        renderCashflow(transactionsData.transactions);

    } catch (error) {
        console.error(error);
        errorBox.textContent =
            "Unable to load FinGuard data. Check that Flask and Oracle are running.";
        errorBox.hidden = false;
    }
}

document.getElementById("refreshBtn")
    .addEventListener("click", loadDashboard);

loadDashboard();


// Income and Expense Forms

let transactionMode = "income";
let availableAccounts = [];

const incomeCategories = [
    "Salary", "Freelance", "Business",
    "Interest", "Gift", "Other"
];

const expenseCategories = [
    "Food", "Shopping", "Transport",
    "Bills", "Education", "Health",
    "Entertainment", "Other"
];

const modal = document.getElementById("transactionModal");
const transactionForm = document.getElementById("transactionForm");
const accountSelect = document.getElementById("transactionAccount");
const categorySelect = document.getElementById("transactionCategory");
const formError = document.getElementById("formError");

function fillSelect(select, options) {
    select.replaceChildren();

    options.forEach(option => {
        const element = document.createElement("option");
        element.value = option.value;
        element.textContent = option.label;
        select.appendChild(element);
    });
}

async function openTransactionModal(mode) {
    transactionMode = mode;
    transactionForm.reset();
    formError.hidden = true;

    document.getElementById("modalTitle").textContent =
        mode === "income" ? "Add Income" : "Add Expense";

    const categories = mode === "income"
        ? incomeCategories
        : expenseCategories;

    fillSelect(categorySelect, categories.map(category => ({
        value: category,
        label: category
    })));

    try {
        const result = await fetchJSON("/api/accounts");
        availableAccounts = result.accounts;

        if (!availableAccounts.length) {
            throw new Error("No financial accounts available");
        }

        fillSelect(accountSelect, availableAccounts.map(account => ({
            value: String(account.account_id),
            label: `${account.account_name} (${formatMoney(account.balance)})`
        })));

        modal.hidden = false;
        accountSelect.focus();

    } catch (error) {
        console.error(error);
        alert("Unable to load accounts. Please try again.");
    }
}

function closeTransactionModal() {
    modal.hidden = true;
}

document.getElementById("addIncomeBtn").addEventListener(
    "click", () => openTransactionModal("income")
);

document.getElementById("addExpenseBtn").addEventListener(
    "click", () => openTransactionModal("expense")
);

document.getElementById("closeModalBtn").addEventListener(
    "click", closeTransactionModal
);

modal.addEventListener("click", event => {
    if (event.target === modal) closeTransactionModal();
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !modal.hidden) {
        closeTransactionModal();
    }
});

transactionForm.addEventListener("submit", async event => {
    event.preventDefault();

    const saveButton = document.getElementById("saveTransactionBtn");

    const amount = document.getElementById("transactionAmount").value;

    const payload = {
        account_id: Number(accountSelect.value),
        amount: amount,
        category: categorySelect.value,
        description: document.getElementById(
            "transactionDescription"
        ).value.trim()
    };

    formError.hidden = true;
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";

    try {
        const response = await fetch(
            transactionMode === "income"
                ? "/api/income"
                : "/api/expense",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Transaction failed");
        }

        closeTransactionModal();
        await loadDashboard();

    } catch (error) {
        formError.textContent = error.message;
        formError.hidden = false;

    } finally {
        saveButton.disabled = false;
        saveButton.textContent = "Save Transaction";
    }
});


// Transfer Money Functionality

const transferModal = document.getElementById("transferModal");
const transferForm = document.getElementById("transferForm");
const transferFrom = document.getElementById("transferFrom");
const transferTo = document.getElementById("transferTo");
const transferError = document.getElementById("transferError");

async function openTransferModal() {
    transferForm.reset();
    transferError.hidden = true;

    try {
        const result = await fetchJSON("/api/accounts");
        const accounts = result.accounts;

        if (accounts.length < 2) {
            alert("At least two accounts are required for transfers.");
            return;
        }

        const options = accounts.map(account => ({
            value: String(account.account_id),
            label: `${account.account_name} (${formatMoney(account.balance)})`
        }));

        fillSelect(transferFrom, options);
        fillSelect(transferTo, options);

        transferTo.selectedIndex = 1;

        transferModal.hidden = false;
        transferFrom.focus();

    } catch (error) {
        console.error(error);
        alert("Unable to load accounts for transfer.");
    }
}

function closeTransferModal() {
    transferModal.hidden = true;
}

document.getElementById("transferBtn").addEventListener(
    "click", openTransferModal
);

document.getElementById("closeTransferBtn").addEventListener(
    "click", closeTransferModal
);

transferModal.addEventListener("click", event => {
    if (event.target === transferModal) {
        closeTransferModal();
    }
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !transferModal.hidden) {
        closeTransferModal();
    }
});

transferForm.addEventListener("submit", async event => {
    event.preventDefault();

    transferError.hidden = true;

    if (transferFrom.value === transferTo.value) {
        transferError.textContent =
            "Source and destination accounts must be different.";
        transferError.hidden = false;
        return;
    }

    const saveButton = document.getElementById("saveTransferBtn");

    saveButton.disabled = true;
    saveButton.textContent = "Transferring...";

    const payload = {
        from_account_id: Number(transferFrom.value),
        to_account_id: Number(transferTo.value),
        amount: document.getElementById("transferAmount").value,
        description: document.getElementById(
            "transferDescription"
        ).value.trim()
    };

    try {
        const response = await fetch("/api/transfer", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Transfer failed");
        }

        closeTransferModal();
        await loadDashboard();

    } catch (error) {
        transferError.textContent = error.message;
        transferError.hidden = false;

    } finally {
        saveButton.disabled = false;
        saveButton.textContent = "Transfer Money";
    }
});


// Budget Management

const budgetModal = document.getElementById("budgetModal");
const budgetForm = document.getElementById("budgetForm");
const budgetError = document.getElementById("budgetError");

function renderBudgets(budgets) {
    const container = document.getElementById("budgetsList");
    container.replaceChildren();

    if (!budgets.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent =
            "No budgets yet. Click Set Budget to create one.";
        container.appendChild(empty);
        return;
    }

    budgets.forEach(budget => {
        const card = document.createElement("div");
        card.className = "budget-item";

        const top = document.createElement("div");
        top.className = "budget-top";

        const category = document.createElement("strong");
        category.textContent = budget.category;

        const amount = document.createElement("span");
        amount.textContent =
            `${formatMoney(budget.spent)} / ${formatMoney(budget.monthly_limit)}`;

        top.append(category, amount);

        const track = document.createElement("div");
        track.className = "budget-progress";

        const fill = document.createElement("div");
        fill.className = "budget-progress-fill";

        const percentage = Number(budget.percentage);
        fill.style.width = `${Math.min(percentage, 100)}%`;

        if (percentage >= 100) {
            fill.classList.add("danger");
        } else if (percentage >= 80) {
            fill.classList.add("warning");
        }

        track.appendChild(fill);

        const bottom = document.createElement("div");
        bottom.className = "budget-bottom";

        const usage = document.createElement("span");
        usage.textContent = `${percentage.toFixed(1)}% used`;

        const remaining = document.createElement("span");
        remaining.textContent = budget.remaining >= 0
            ? `${formatMoney(budget.remaining)} remaining`
            : `${formatMoney(Math.abs(budget.remaining))} over budget`;

        bottom.append(usage, remaining);
        card.append(top, track, bottom);
        container.appendChild(card);
    });
}

async function loadBudgets() {
    try {
        const result = await fetchJSON("/api/budgets");
        renderBudgets(result.budgets);
    } catch (error) {
        console.error("Budget loading failed:", error);
        document.getElementById("budgetsList").textContent =
            "Unable to load budgets.";
    }
}

document.getElementById("addBudgetBtn").addEventListener(
    "click", () => {
        budgetForm.reset();
        budgetError.hidden = true;
        budgetModal.hidden = false;
    }
);

function closeBudgetModal() {
    budgetModal.hidden = true;
}

document.getElementById("closeBudgetBtn").addEventListener(
    "click", closeBudgetModal
);

budgetModal.addEventListener("click", event => {
    if (event.target === budgetModal) closeBudgetModal();
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !budgetModal.hidden) {
        closeBudgetModal();
    }
});

budgetForm.addEventListener("submit", async event => {
    event.preventDefault();

    const button = document.getElementById("saveBudgetBtn");
    button.disabled = true;
    budgetError.hidden = true;

    try {
        const response = await fetch("/api/budgets", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                category: document.getElementById(
                    "budgetCategory"
                ).value,
                monthly_limit: document.getElementById(
                    "budgetLimit"
                ).value
            })
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Unable to save budget");
        }

        closeBudgetModal();
        await loadBudgets();

    } catch (error) {
        budgetError.textContent = error.message;
        budgetError.hidden = false;

    } finally {
        button.disabled = false;
    }
});

// Load budgets on initial page load
loadBudgets();

// Refresh budgets when the Refresh button is clicked
document.getElementById("refreshBtn").addEventListener(
    "click", loadBudgets
);


// ==========================================
// Savings Goals Management
// ==========================================

const goalModal = document.getElementById("goalModal");
const goalForm = document.getElementById("goalForm");
const goalError = document.getElementById("goalError");

const goalSavingsModal =
    document.getElementById("goalSavingsModal");

const goalSavingsForm =
    document.getElementById("goalSavingsForm");

const savingsError =
    document.getElementById("savingsError");

let selectedGoalId = null;

function renderGoals(goals) {
    const container = document.getElementById("goalsList");
    container.replaceChildren();

    if (!goals.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent =
            "No savings goals yet. Create your first goal!";
        container.appendChild(empty);
        return;
    }

    goals.forEach(goal => {
        const card = document.createElement("div");
        card.className = "goal-card";

        const heading = document.createElement("div");
        heading.className = "goal-heading";

        const name = document.createElement("strong");
        name.textContent = goal.goal_name;

        const status = document.createElement("span");
        status.className = "goal-status";
        status.textContent = goal.goal_status;

        if (goal.goal_status === "COMPLETED") {
            status.classList.add("completed");
        }

        heading.append(name, status);

        const amount = document.createElement("div");
        amount.className = "goal-amount";
        amount.textContent = formatMoney(goal.saved_amount);

        const target = document.createElement("small");
        target.textContent =
            ` / ${formatMoney(goal.target_amount)}`;
        amount.appendChild(target);

        const progress = document.createElement("div");
        progress.className = "goal-progress";

        const fill = document.createElement("div");
        fill.className = "goal-progress-fill";
        fill.style.width = `${Math.min(goal.percentage, 100)}%`;

        if (goal.goal_status === "COMPLETED") {
            fill.classList.add("completed");
        }

        progress.appendChild(fill);

        const details = document.createElement("div");
        details.className = "goal-details";

        const percentage = document.createElement("span");
        percentage.textContent =
            `${Number(goal.percentage).toFixed(1)}% saved`;

        const remaining = document.createElement("span");
        remaining.textContent =
            `${formatMoney(goal.remaining)} remaining`;

        details.append(percentage, remaining);
        card.append(heading, amount, progress, details);

        if (goal.goal_status === "ACTIVE") {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "goal-save-btn";
            button.textContent = "+ Add Savings";

            button.addEventListener("click", () => {
                selectedGoalId = goal.goal_id;

                document.getElementById(
                    "selectedGoalName"
                ).textContent = goal.goal_name;

                goalSavingsForm.reset();
                savingsError.hidden = true;
                goalSavingsModal.hidden = false;
            });

            card.appendChild(button);
        }

        container.appendChild(card);
    });
}

async function loadGoals() {
    try {
        const result = await fetchJSON("/api/goals");
        renderGoals(result.goals);
    } catch (error) {
        console.error(error);
        document.getElementById("goalsList").textContent =
            "Unable to load savings goals.";
    }
}

document.getElementById("addGoalBtn").addEventListener(
    "click", () => {
        goalForm.reset();
        goalError.hidden = true;
        goalModal.hidden = false;
    }
);

document.getElementById("closeGoalBtn").addEventListener(
    "click", () => goalModal.hidden = true
);

document.getElementById("closeSavingsBtn").addEventListener(
    "click", () => goalSavingsModal.hidden = true
);

goalModal.addEventListener("click", event => {
    if (event.target === goalModal) goalModal.hidden = true;
});

goalSavingsModal.addEventListener("click", event => {
    if (event.target === goalSavingsModal) {
        goalSavingsModal.hidden = true;
    }
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape") {
        goalModal.hidden = true;
        goalSavingsModal.hidden = true;
    }
});

// Create Goal
goalForm.addEventListener("submit", async event => {
    event.preventDefault();

    const button = document.getElementById("saveGoalBtn");
    button.disabled = true;
    goalError.hidden = true;

    try {
        const response = await fetch("/api/goals", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                goal_name: document.getElementById(
                    "goalName"
                ).value.trim(),
                target_amount: document.getElementById(
                    "goalTarget"
                ).value,
                target_date: document.getElementById(
                    "goalDate"
                ).value || null
            })
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Unable to create goal");
        }

        goalModal.hidden = true;
        await loadGoals();

    } catch (error) {
        goalError.textContent = error.message;
        goalError.hidden = false;

    } finally {
        button.disabled = false;
    }
});

// Add Savings to Goal
goalSavingsForm.addEventListener("submit", async event => {
    event.preventDefault();

    const button = document.getElementById("saveSavingsBtn");
    button.disabled = true;
    savingsError.hidden = true;

    try {
        const response = await fetch(
            `/api/goals/${selectedGoalId}/save`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    amount: document.getElementById(
                        "savingsAmount"
                    ).value
                })
            }
        );

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Unable to add savings");
        }

        goalSavingsModal.hidden = true;
        await loadGoals();

    } catch (error) {
        savingsError.textContent = error.message;
        savingsError.hidden = false;

    } finally {
        button.disabled = false;
    }
});

// Initial load and refresh
loadGoals();

document.getElementById("refreshBtn").addEventListener(
    "click", loadGoals
);


// ==========================================
// Financial Risk Alerts
// ==========================================

function renderRiskAlerts(alerts) {
    const container = document.getElementById("riskAlertsList");
    const count = document.getElementById("riskAlertCount");

    container.replaceChildren();
    count.textContent = `${alerts.length} Alerts`;

    if (!alerts.length) {
        const empty = document.createElement("div");
        empty.className = "risk-empty";
        empty.textContent =
            "✓ No financial risk alerts detected.";
        container.appendChild(empty);
        return;
    }

    alerts.forEach(alert => {
        const card = document.createElement("div");
        card.className = "risk-alert-item";

        if (alert.risk_level === "HIGH") {
            card.classList.add("high");
        }

        const info = document.createElement("div");
        info.className = "risk-alert-info";

        const title = document.createElement("strong");
        title.textContent = `${alert.category} Expense Alert`;

        const reason = document.createElement("p");
        reason.textContent = alert.risk_reason;

        const account = document.createElement("p");
        account.textContent =
            `Account: ${alert.account_name}`;

        const date = document.createElement("p");
        date.textContent = alert.detected_at
            ? new Date(alert.detected_at).toLocaleString("en-IN")
            : "";

        info.append(title, reason, account, date);

        const meta = document.createElement("div");
        meta.className = "risk-alert-meta";

        const level = document.createElement("span");
        level.className = "risk-level";
        level.textContent = alert.risk_level;

        if (alert.risk_level === "HIGH") {
            level.classList.add("high");
        }

        const amount = document.createElement("span");
        amount.className = "risk-amount";
        amount.textContent = formatMoney(alert.amount);

        const status = document.createElement("small");
        status.textContent = alert.alert_status;

        meta.append(level, amount, status);
        card.append(info, meta);

        container.appendChild(card);
    });
}

async function loadRiskAlerts() {
    try {
        const result = await fetchJSON("/api/risk-alerts");
        renderRiskAlerts(result.alerts);
    } catch (error) {
        console.error("Unable to load risk alerts:", error);
        document.getElementById("riskAlertsList").textContent =
            "Unable to load risk alerts.";
    }
}

// Initial load
loadRiskAlerts();

// Refresh when the user clicks Refresh
document.getElementById("refreshBtn").addEventListener(
    "click", loadRiskAlerts
);


// ==========================================
// Financial Audit Trail
// ==========================================

function renderAuditLogs(logs) {
    const container = document.getElementById("auditLogsList");
    const count = document.getElementById("auditLogCount");

    container.replaceChildren();
    count.textContent = `${logs.length} Records`;

    if (logs.length === 0) {
        const empty = document.createElement("div");
        empty.className = "audit-empty";
        empty.textContent =
            "No account balance changes have been audited yet.";
        container.appendChild(empty);
        return;
    }

    logs.forEach(log => {
        const card = document.createElement("div");
        card.className = "audit-log-item";

        const info = document.createElement("div");
        info.className = "audit-log-info";

        const title = document.createElement("strong");
        title.textContent =
            `${log.action_type} — Account #${log.record_id}`;

        const oldValue = document.createElement("p");
        oldValue.textContent =
            `Previous: ${log.old_value ?? "N/A"}`;

        const newValue = document.createElement("p");
        newValue.textContent =
            `Updated: ${log.new_value ?? "N/A"}`;

        const table = document.createElement("p");
        table.textContent = `Table: ${log.table_name}`;

        info.append(title, oldValue, newValue, table);

        const date = document.createElement("span");
        date.className = "audit-log-date";
        date.textContent = log.action_timestamp
            ? new Date(log.action_timestamp).toLocaleString("en-IN")
            : "";

        card.append(info, date);
        container.appendChild(card);
    });
}

async function loadAuditLogs() {
    try {
        const result = await fetchJSON("/api/audit-logs");
        renderAuditLogs(result.logs);
    } catch (error) {
        console.error("Unable to load audit logs:", error);

        const container = document.getElementById("auditLogsList");
        container.textContent = "Unable to load audit records.";
    }
}

// Initial dashboard load
loadAuditLogs();

// Refresh audit logs using existing Refresh button
document.getElementById("refreshBtn").addEventListener(
    "click",
    loadAuditLogs
);

