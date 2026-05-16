# 
# PERSONAL EXPENSE ANALYZER - Streamlit App
# This is a simple tool to track, analyze, and manage personal expenses with budget tracking
# 

import datetime      # For handling dates and time
import io            # For reading/writing file data in memory
import sqlite3       # For local database storage
from pathlib import Path

import matplotlib.pyplot as plt  # For creating pie charts and visualizations
import pandas as pd              # For handling tabular data (rows and columns)
import streamlit as st           # Web app framework for creating the UI

# This also Set up the database file location (in the same folder as this app)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "expenses.db"

# This Configure the Streamlit page (title, layout style, etc.)
st.set_page_config(page_title="Personal Expense Analyzer", layout="wide")

# This Display the main title and description
st.title("Personal Expense Analyzer")
st.write("Track your expenses manually, monitor savings progress, and keep data stored locally.")


def safe_rerun():
    """Safely refresh the app after making changes. Clears cached data and reruns the script."""
    if hasattr(st, "experimental_rerun"):
        st.cache_data.clear()              # Clear cached expense data
        st.session_state.data_modified = True  # Mark data as changed
        st.experimental_rerun()            # Rerun the app with fresh data
    else:
        try:
            st.cache_data.clear()
            st.session_state.data_modified = True
            from streamlit.runtime.scriptrunner import script_runner
            raise script_runner.RerunException
        except Exception:
            st.stop()


def format_money(amount):
    """Format a number as Nigerian Naira currency (₦) with 2 decimal places and commas."""
    return f"₦{amount:,.2f}"


@st.cache_resource  # Cache this connection to avoid creating multiple database connections
def get_db_connection():
    """Connect to the SQLite database. The @cache_resource decorator ensures only one connection is created."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # Allow use across threads
    conn.row_factory = sqlite3.Row  # Access rows like dictionaries
    return conn


def init_db(conn):
    """Create database tables if they don't exist. Sets up the database structure on first run."""
    # Table 1: Store each expense with date, category, and amount
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
        """
    )
    # Table 2: This would Store favorite categories (e.g., "Groceries", "Transport", "Entertainment")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_presets (
            name TEXT PRIMARY KEY
        )
        """
    )
    # Table 3: Store monthly budget targets (spending goals for each month)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_targets (
            month TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    # Table 4: Store spending targets for specific categories (e.g., "Groceries: ₦20,000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_targets (
            category TEXT PRIMARY KEY,
            target REAL NOT NULL
        )
        """
    )
    conn.commit()  # Save all table creations to the database


def load_category_presets(conn):
    """Retrieve all saved category presets (favorite categories) from the database."""
    rows = conn.execute("SELECT name FROM category_presets ORDER BY name").fetchall()
    return [row["name"] for row in rows]


def add_category_preset(conn, name):
    """Add a new favorite category to the presets."""
    conn.execute("INSERT OR IGNORE INTO category_presets (name) VALUES (?)", (name,))
    conn.commit()


def remove_category_presets(conn, names):
    """Remove one or more category presets."""
    conn.executemany("DELETE FROM category_presets WHERE name = ?", [(name,) for name in names])
    conn.commit()


def load_expenses(conn):
    """Load all expenses from the database, sorted by most recent first."""
    rows = conn.execute("SELECT id, date, category, amount FROM expenses ORDER BY date DESC, id DESC").fetchall()
    return [dict(row) for row in rows]


@st.cache_data(ttl=300)  # Cache this for 5 minutes to improve performance
def get_expenses_dataframe():
    """Load expenses from database and convert to a pandas DataFrame.
    
    This function is cached (5 minute timeout) to avoid repeated database queries.
    The cache is cleared whenever data is modified via safe_rerun().
    """
    conn = get_db_connection()
    raw_expenses = load_expenses(conn)
    if raw_expenses:
        df = pd.DataFrame(raw_expenses)
        # Rename columns to proper case for display
        df = df.rename(columns={"date": "Date", "category": "Category", "amount": "Amount"})
        df["Date"] = pd.to_datetime(df["Date"]).dt.date  # Convert to date type
        return df
    # Return empty dataframe with correct structure if no expenses yet
    return pd.DataFrame(columns=["id", "Date", "Category", "Amount"])


def add_expense(conn, date, category, amount):
    """Add a single new expense to the database."""
    conn.execute("INSERT INTO expenses (date, category, amount) VALUES (?, ?, ?)", (date, category, amount))
    conn.commit()


def bulk_add_expenses(conn, expenses_list):
    """Efficiently insert multiple expenses at once (used for CSV/Excel imports).
    
    This is much faster than adding expenses one-by-one because it commits once instead of many times.
    """
    if not expenses_list:
        return
    conn.executemany(
        "INSERT INTO expenses (date, category, amount) VALUES (?, ?, ?)",
        expenses_list,
    )
    conn.commit()


def update_expense(conn, expense_id, date, category, amount):
    """Modify an existing expense's details."""
    conn.execute(
        "UPDATE expenses SET date = ?, category = ?, amount = ? WHERE id = ?",
        (date, category, amount, expense_id),
    )
    conn.commit()


def delete_expense(conn, expense_id):
    """Remove an expense from the database."""
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()


def load_budget_history(conn):
    """Get all monthly budgets ever created, sorted by most recent month."""
    rows = conn.execute("SELECT month, amount, created_at FROM budget_targets ORDER BY month DESC").fetchall()
    return [dict(row) for row in rows]


def load_budget_target(conn, month):
    """Get the spending target for a specific month (e.g., "2026-05")."""
    row = conn.execute("SELECT amount FROM budget_targets WHERE month = ?", (month,)).fetchone()
    return float(row["amount"]) if row else 0.0  # Return 0 if no budget set for this month


def save_budget_target(conn, month, amount):
    """Set or update the spending target for a specific month."""
    conn.execute(
        "INSERT OR REPLACE INTO budget_targets (month, amount, created_at) VALUES (?, ?, ?)",
        (month, amount, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()


def load_category_targets(conn):
    """Get all category spending targets (e.g., limit on Groceries or Entertainment)."""
    rows = conn.execute("SELECT category, target FROM category_targets ORDER BY category").fetchall()
    return [dict(row) for row in rows]


def save_category_target(conn, category, target):
    """Set or update the spending limit for a specific category."""
    conn.execute("INSERT OR REPLACE INTO category_targets (category, target) VALUES (?, ?)", (category, target))
    conn.commit()


def delete_category_target(conn, category):
    """Remove the spending limit for a category."""
    conn.execute("DELETE FROM category_targets WHERE category = ?", (category,))
    conn.commit()


def get_month_string(date_value):
    """Convert a date to month string format (e.g., "2026-05" for May 2026)."""
    return date_value.strftime("%Y-%m")


def load_monthly_spending(conn):
    """Calculate total spending for each month from all expenses.
    
    Returns a dictionary like {"2026-05": 15000.00, "2026-04": 18500.00}
    """
    rows = conn.execute(
        "SELECT substr(date, 1, 7) AS month, SUM(amount) AS total_spent FROM expenses GROUP BY month"
    ).fetchall()
    return {row["month"]: float(row["total_spent"]) for row in rows}


def get_rollover_summary(conn):
    """Calculate budget rollover for each month (savings carried forward from previous months).
    
    This shows whether you're under or over budget each month and accumulates savings.
    """
    budget_rows = load_budget_history(conn)
    monthly_spending = load_monthly_spending(conn)
    # Get all months that have either a budget or expenses
    months = sorted(set([row["month"] for row in budget_rows] + list(monthly_spending.keys())))
    rollover = 0.0  # Running total of accumulated savings
    summary = []
    for month in months:
        target = load_budget_target(conn, month)
        spent = monthly_spending.get(month, 0.0)
        remainder = round(target - spent, 2)  # Positive = under budget, Negative = over budget
        rollover += remainder  # Add to cumulative savings
        summary.append(
            {
                "Month": month,
                "Target": target,
                "Spent": spent,
                "Remainder": remainder,
                "Rollover Balance": round(rollover, 2),
            }
        )
    return summary


def get_total_savings(conn):
    """Get the most recent cumulative savings amount (total money saved across all months)."""
    summary = get_rollover_summary(conn)
    return summary[-1]["Rollover Balance"] if summary else 0.0


# 
# Initialize Database and Load Data
# 

conn = get_db_connection()  # Get or create database connection
init_db(conn)              # Create tables if they don't exist

# This is to Load category presets (favorite categories)
category_presets = load_category_presets(conn)
if not category_presets:
    # Add default categories on first run
    default_presets = ["Groceries", "Bills", "Transport", "Dining", "Entertainment", "Healthcare"]
    for preset in default_presets:
        add_category_preset(conn, preset)
    category_presets = default_presets

# Load all data needed for the app
df = get_expenses_dataframe()  # Load expenses dataframe (cached for 5 minutes)
budget_history = load_budget_history(conn)  # Load monthly budgets
category_targets = load_category_targets(conn)  # Load category spending limits
monthly_rollover = get_rollover_summary(conn)  # Calculate budget rollover/savings

# Initialize session state variables (these persist while the user has the app open)
if "budget_month" not in st.session_state:
    st.session_state.budget_month = get_month_string(datetime.date.today())  # Default to current month

if "data_modified" not in st.session_state:
    st.session_state.data_modified = False  # Flag to track if data has been changed


# 
# Create Tabs for Navigation
# 
# The app has 3 main sections: Dashboard (overview), Expenses (add/view/edit), Settings (budgets/presets)

dashboard_tab, expenses_tab, settings_tab = st.tabs(["Dashboard", "Expenses", "Settings"])

# 
# DASHBOARD TAB - Shows key metrics and savings summary
#
with dashboard_tab:
    st.subheader("Dashboard")
    total_spent = float(df["Amount"].sum()) if not df.empty else 0.0
    current_month = st.session_state.budget_month
    current_month_spent = float(df[df["Date"].apply(get_month_string) == current_month]["Amount"].sum()) if not df.empty else 0.0
    current_month_target = load_budget_target(conn, current_month)
    savings_progress = get_total_savings(conn)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total spending", format_money(total_spent))
    col2.metric("This month spent", format_money(current_month_spent))
    col3.metric("Total savings progress", format_money(savings_progress))

    if current_month_target > 0:
        st.metric("Current month target", format_money(current_month_target))
        remaining = round(current_month_target - current_month_spent, 2)
        if remaining >= 0:
            st.success(f"{format_money(remaining)} remaining for {current_month}.")
        else:
            st.error(f"Over budget by {format_money(-remaining)} for {current_month}.")
    else:
        st.info("Set a monthly budget in Settings to track your goals.")

    if monthly_rollover:
        st.subheader("Monthly Rollover Summary")
        summary_df = pd.DataFrame(monthly_rollover)
        st.dataframe(summary_df.sort_values(by="Month", ascending=False).reset_index(drop=True))
        chart_df = summary_df.set_index("Month")[["Spent", "Target", "Rollover Balance"]]
        st.line_chart(chart_df, use_container_width=True)
    else:
        st.info("No rollover data yet. Add budgets and expenses to see progress.")

    if category_targets:
        st.subheader("Saved Category Targets")
        st.dataframe(pd.DataFrame(category_targets))

# 
# EXPENSES TAB - Add, view, edit, import, and analyze expenses
# 
with expenses_tab:
    st.subheader("Expense Entry")
    # Simple form to quickly add a single expense
    with st.form(key="expense_form_tab"):
        date = st.date_input("Date", value=datetime.date.today())
        category_choice = st.selectbox("Category", category_presets + ["Other"])
        if category_choice == "Other":
            custom_category = st.text_input("Custom category")
        else:
            custom_category = category_choice
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Add Expense")

        if submit:
            category = custom_category.strip()
            if category == "":
                st.warning("Please enter a category before adding an expense.")
            elif amount <= 0:
                st.warning("Amount must be greater than zero.")
            else:
                add_expense(conn, date.isoformat(), category.title(), float(amount))
                st.success(f"Added expense: {category.title()} — {format_money(amount)}")
                safe_rerun()
    st.markdown("---")
    st.subheader("Import / Export")
    # Two columns: left for importing, right for exporting
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Upload a CSV or Excel file with columns: Date, Category, Amount.")
        # This allows user to upload a file with multiple expenses to add at once
        uploaded_file = st.file_uploader("Import expenses from CSV or Excel", type=["csv", "xls", "xlsx"], key="import_csv")
        if uploaded_file is not None:
            try:
                filename = uploaded_file.name.lower()
                if filename.endswith(".csv"):
                    imported_df = pd.read_csv(uploaded_file)
                else:
                    imported_df = pd.read_excel(uploaded_file)
                imported_df.columns = imported_df.columns.str.strip()
                lower_cols = {col.lower(): col for col in imported_df.columns}
                required = {"date", "category", "amount"}
                if required.issubset(set(lower_cols.keys())):
                    mapped_columns = {
                        lower_cols["date"]: "Date",
                        lower_cols["category"]: "Category",
                        lower_cols["amount"]: "Amount",
                    }
                    imported_df = imported_df.rename(columns=mapped_columns)
                    imported_df["Date"] = pd.to_datetime(imported_df["Date"]).dt.date
                    imported_df["Category"] = imported_df["Category"].astype(str).str.title()
                    imported_df["Amount"] = imported_df["Amount"].astype(float)
                    
                    progress_placeholder = st.empty()
                    progress_placeholder.text("Importing expenses...")
                    progress_bar = st.progress(0)
                    expenses_list = [
                        (row["Date"].isoformat(), row["Category"], row["Amount"])
                        for _, row in imported_df.iterrows()
                    ]
                    bulk_add_expenses(conn, expenses_list)
                    progress_bar.progress(100)
                    progress_placeholder.text(
                        f"✓ Successfully imported {len(imported_df)} expense(s)!"
                    )
                    st.success(f"Imported {len(imported_df)} expense(s) from file.")
                    safe_rerun()
                else:
                    st.error("File must include Date, Category, and Amount columns.")
            except Exception as exc:
                st.error(f"Failed to import file: {exc}")
    with col2:
        st.caption("Download all saved expenses as CSV or Excel.")
        if not df.empty:
            export_df = df.drop(columns=["id"]) if "id" in df.columns else df.copy()
            csv = export_df.to_csv(index=False)
            st.download_button("Download expenses as CSV", csv, file_name="expenses.csv", mime="text/csv")

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Expenses")
            excel_buffer.seek(0)
            st.download_button(
                "Download expenses as Excel",
                excel_buffer,
                file_name="expenses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.write("Add expenses to enable export.")

    st.markdown("---")
    if not df.empty:
        if st.button("Clear all expenses", key="clear_expenses"):
            conn.execute("DELETE FROM expenses")
            conn.commit()
            safe_rerun()

        st.subheader("Filters")
        categories = ["All"] + sorted(df["Category"].unique().tolist())
        selected_category = st.selectbox("Category filter", categories, key="filter_category")
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        date_range = st.date_input("Date range", [min_date, max_date], key="filter_range")
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date

        filtered_df = df.copy()
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df["Category"] == selected_category]
        filtered_df = filtered_df[(filtered_df["Date"] >= start_date) & (filtered_df["Date"] <= end_date)]

        st.write(f"Showing {len(filtered_df)} expense(s) after filters.")
        display_df = filtered_df.sort_values(by="Date", ascending=False).reset_index(drop=True).copy()
        display_df["Amount"] = display_df["Amount"].apply(format_money)
        st.dataframe(display_df)

        st.subheader("Edit / Remove Expenses")
        if hasattr(st, "experimental_data_editor"):
            edited_df = st.experimental_data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Save expense edits", key="save_expense_edits"):
                try:
                    edited_df["Date"] = pd.to_datetime(edited_df["Date"]).dt.date
                    edited_df["Category"] = edited_df["Category"].astype(str).str.title()
                    edited_df["Amount"] = edited_df["Amount"].astype(float)
                    original_ids = set(df["id"].astype(int).tolist())
                    updated_ids = set()
                    for _, row in edited_df.iterrows():
                        if pd.isna(row.get("id", None)):
                            add_expense(conn, row["Date"].isoformat(), row["Category"], row["Amount"])
                        else:
                            expense_id = int(row["id"])
                            update_expense(conn, expense_id, row["Date"].isoformat(), row["Category"], row["Amount"])
                            updated_ids.add(expense_id)
                    to_delete = original_ids - updated_ids
                    for expense_id in to_delete:
                        delete_expense(conn, expense_id)
                    st.success("Expenses updated.")
                    safe_rerun()
                except Exception as exc:
                    st.error(f"Unable to save changes: {exc}")
        else:
            st.info("Your Streamlit version does not support row editing. Use the form to update expenses.")

        total_spending = filtered_df["Amount"].sum()
        if total_spending > 0:
            spending_by_category = filtered_df.groupby("Category", as_index=False)["Amount"].sum()
            spending_by_category["Percentage"] = (spending_by_category["Amount"] / total_spending * 100).round(1)
            top_category_row = spending_by_category.sort_values(by="Amount", ascending=False).iloc[0]
            top_category = top_category_row["Category"]
            top_amount = top_category_row["Amount"]
            top_percentage = top_category_row["Percentage"]

            st.subheader("Expense Summary")
            st.metric("Total Spending", format_money(total_spending))
            st.write(f"**Top category:** {top_category} ({format_money(top_amount)}, {top_percentage}% of total spending)")

            if top_percentage > 40:
                st.warning(f"Warning: {top_category} accounts for {top_percentage}% of your total spending.")

            st.subheader("Spending by Category")
            display_spending = spending_by_category.sort_values(by="Amount", ascending=False).reset_index(drop=True).copy()
            display_spending["Amount"] = display_spending["Amount"].apply(format_money)
            st.dataframe(display_spending)

            monthly_summary = filtered_df.copy()
            monthly_summary["Month"] = pd.to_datetime(monthly_summary["Date"]).dt.to_period("M").astype(str)
            monthly_totals = monthly_summary.groupby("Month", as_index=False)["Amount"].sum()
            st.subheader("Monthly Spending Totals")
            display_monthly_totals = monthly_totals.sort_values(by="Month", ascending=False).reset_index(drop=True).copy()
            display_monthly_totals["Amount"] = display_monthly_totals["Amount"].apply(format_money)
            st.dataframe(display_monthly_totals)

            st.subheader("Category Spend Chart")
            st.bar_chart(data=spending_by_category.set_index("Category")["Amount"], use_container_width=True)

            st.subheader("Category Spend Pie Chart")
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Professional color palette for categories
            color_palette = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
                "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#A9DFBF",
                "#F5B7B1", "#D7BDE2", "#FAD7A0", "#A3E4D7", "#F9E79F",
            ]
            
            # Map categories to consistent colors
            categories = spending_by_category["Category"].tolist()
            category_colors = {}
            for i, cat in enumerate(categories):
                category_colors[cat] = color_palette[i % len(color_palette)]
            
            colors = [category_colors[cat] for cat in categories]
            
            # This would Create pie chart with only percentages on slices
            wedges, texts, autotexts = ax.pie(
                spending_by_category["Amount"],
                labels=None,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                textprops={"fontsize": 11, "weight": "bold", "color": "white"},
                pctdistance=0.82,
                explode=[0.05] * len(spending_by_category),
            )
            
            # This would Style percentage text
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_weight("bold")
                autotext.set_fontsize(11)
            
            # Create legend with amounts
            legend_labels = [
                f"{cat}: {format_money(amt)}"
                for cat, amt in zip(
                    spending_by_category["Category"],
                    spending_by_category["Amount"],
                )
            ]
            ax.legend(
                wedges,
                legend_labels,
                title="Categories",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=10,
                title_fontsize=11,
            )
            
            ax.set_title(
                "Spending Distribution by Category",
                fontsize=14,
                weight="bold",
                pad=20,
            )
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)

            st.subheader("Budget Tracking")
            budget_target_value = load_budget_target(conn, st.session_state.budget_month)
            budget_month_total = df["Date"].apply(get_month_string).eq(st.session_state.budget_month)
            month_spending = df.loc[budget_month_total, "Amount"].sum()
            st.metric("Budget month", st.session_state.budget_month)
            st.metric("Budget target", format_money(budget_target_value))
            st.metric("Spent this month", format_money(month_spending))
            budget_left = budget_target_value - month_spending
            if budget_target_value > 0:
                if budget_left < 0:
                    st.error(f"You are over budget by {format_money(-budget_left)} for {st.session_state.budget_month}.")
                else:
                    st.success(f"You are under budget by {format_money(budget_left)} for {st.session_state.budget_month}.")
            else:
                st.info("Set a monthly budget target in settings to track your spending goals.")

            if category_targets:
                category_target_df = pd.DataFrame(category_targets)
                spending_by_category_full = df.groupby("Category", as_index=False)["Amount"].sum()
                merged = pd.merge(
                    category_target_df,
                    spending_by_category_full,
                    left_on="category",
                    right_on="Category",
                    how="left",
                ).fillna(0)
                merged["Remaining"] = merged["target"] - merged["Amount"]
                merged = merged[["category", "target", "Amount", "Remaining"]].rename(
                    columns={"category": "Category", "target": "Target", "Amount": "Spent"}
                )
                st.subheader("Category Budget Targets")
                st.dataframe(merged.sort_values(by="Category").reset_index(drop=True))

            st.subheader("Insights")
            insight_lines = []
            insight_lines.append(
                f"You have entered {len(filtered_df)} expense item(s) in the selected range for a total of ₦{total_spending:.2f}."
            )
            insight_lines.append(
                f"Your highest spending category is {top_category}, which makes up {top_percentage}% of filtered spending."
            )

            if top_percentage > 40:
                insight_lines.append(
                    "This suggests your budget may be too concentrated in one area. Consider reviewing that category for potential savings."
                )
            else:
                insight_lines.append(
                    "Your spending is reasonably distributed across selected categories, but keep tracking to stay on budget."
                )

            for line in insight_lines:
                st.write(f"- {line}")
        else:
            st.warning("No spending in the selected filter range. Adjust the category or date range.")
    else:
        st.info("No expenses available yet. Add a few entries first.")

# 
# SETTINGS TAB - Manage category presets and budget targets
#
with settings_tab:
    st.subheader("Settings")
    # Section 1: Manage favorite categories
    with st.expander("Category presets", expanded=True):
        new_preset = st.text_input("Add a preset category", "", key="settings_new_preset")
        if st.button("Add preset", key="settings_add_preset"):
            preset_name = new_preset.strip().title()
            if preset_name == "":
                st.warning("Enter a category name before adding a preset.")
            elif preset_name in category_presets:
                st.warning("This preset already exists.")
            else:
                add_category_preset(conn, preset_name)
                st.success(f"Added preset: {preset_name}")
                safe_rerun()

        if category_presets:
            st.write("Current category presets:")
            st.write(", ".join(category_presets))
            remove_presets = st.multiselect("Remove selected presets", category_presets, key="settings_remove_presets")
            if st.button("Remove presets", key="settings_remove_presets_button"):
                if remove_presets:
                    remove_category_presets(conn, remove_presets)
                    st.success("Removed selected presets.")
                    safe_rerun()
        else:
            st.info("No presets yet. Add one above.")

    st.markdown("---")

    # Section 2: Set monthly spending budgets
    with st.expander("Monthly budget targets", expanded=True):
        budget_month_date = st.date_input(
            "Select budget month",
            value=datetime.date.fromisoformat(st.session_state.budget_month + "-01"),
            key="settings_budget_month",
        )
        budget_month = get_month_string(budget_month_date)
        st.session_state.budget_month = budget_month
        budget_target_value = load_budget_target(conn, budget_month)
        budget_target_input = st.number_input(
            "Budget target for selected month (₦)",
            value=budget_target_value,
            min_value=0.0,
            format="%.2f",
            step=10.0,
            key="settings_budget_target",
        )
        if st.button("Save monthly budget", key="save_monthly_budget"):
            save_budget_target(conn, budget_month, float(budget_target_input))
            st.success(f"Saved budget target for {budget_month}.")
            safe_rerun()

        if budget_history:
            st.subheader("Budget history")
            st.dataframe(pd.DataFrame(budget_history).sort_values(by="month", ascending=False).reset_index(drop=True))
        else:
            st.info("No budget history yet. Save a budget to begin tracking.")

    st.markdown("---")

    # Section 3: Set spending limits for specific categories
    with st.expander("Category budget targets", expanded=True):
        category_options = sorted(set(category_presets + df["Category"].dropna().astype(str).tolist()))
        if category_options:
            category_target_choice = st.selectbox("Category", category_options, key="target_category_choice")
            category_target_amount = st.number_input(
                "Category target (₦)",
                min_value=0.0,
                format="%.2f",
                step=5.0,
                key="settings_category_target_amount",
            )
            if st.button("Save category target", key="save_category_target"):
                save_category_target(conn, category_target_choice, float(category_target_amount))
                st.success(f"Saved target for {category_target_choice}.")
                safe_rerun()

            if category_targets:
                target_df = pd.DataFrame(category_targets)
                st.subheader("Saved category targets")
                st.dataframe(target_df)
                remove_target = st.selectbox("Remove target", target_df["category"].tolist(), key="remove_target")
                if st.button("Remove category target", key="remove_category_target"):
                    delete_category_target(conn, remove_target)
                    st.success(f"Removed target for {remove_target}.")
                    safe_rerun()
        else:
            st.info("Add expenses or presets to set category targets.")
# Enjoy the app and happy budgeting Big Sis! :)