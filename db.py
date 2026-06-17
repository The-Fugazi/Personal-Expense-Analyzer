"""Database module for Personal Expense Analyzer with optimized schema."""

import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "expenses.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Initialize database with optimized schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, 
            name TEXT NOT NULL,
            color TEXT DEFAULT '#4ECDC4',
            icon TEXT DEFAULT '',
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, name)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, month)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            limit_amount REAL NOT NULL CHECK(limit_amount > 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(user_id, category_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            source TEXT NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_user_date 
        ON expenses(user_id, date DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_category 
        ON expenses(category_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_budgets_user_month 
        ON budgets(user_id, month)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_income_user_date 
        ON income(user_id, date DESC)
    """)
    
    conn.commit()
    conn.close()


def get_user_id(conn, username):
    """Get user ID from username."""
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    return row["id"] if row else None


def create_default_categories(conn, user_id):
    """Create default categories for a new user."""
    default_categories = [
        ("Groceries", ""),
        ("Bills", ""),
        ("Transport", ""),
        ("Dining", ""),
        ("Entertainment", ""),
        ("Healthcare", ""),
        ("Shopping", ""),
        ("Other", ""),
    ]
    
    for name, icon in default_categories:
        try:
            conn.execute(
                "INSERT INTO categories (user_id, name, icon, is_default) VALUES (?, ?, ?, 1)",
                (user_id, name, icon)
            )
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()


def get_categories(conn, user_id):
    """Get all categories for a user."""
    rows = conn.execute(
        "SELECT id, name, icon FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_category_id(conn, user_id, category_name):
    """Get category ID by name."""
    row = conn.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ?",
        (user_id, category_name)
    ).fetchone()
    return row["id"] if row else None


def add_expense(conn, user_id, category_id, amount, date, description=""):
    """Add a new expense."""
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO expenses 
           (user_id, category_id, amount, date, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (user_id, category_id, amount, date, description)
    )
    conn.commit()
    return cursor.lastrowid


def get_expenses(conn, user_id, start_date=None, end_date=None, category_id=None):
    """Get expenses with optional filters."""
    query = """
        SELECT e.id, e.amount, e.date, e.description, c.name as category, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
    """
    params = [user_id]
    
    if start_date:
        query += " AND e.date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND e.date <= ?"
        params.append(end_date)
    
    if category_id:
        query += " AND e.category_id = ?"
        params.append(category_id)
    
    query += " ORDER BY e.date DESC, e.id DESC"
    
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_monthly_spending(conn, user_id):
    """Get total spending by month."""
    rows = conn.execute(
        """SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
           FROM expenses WHERE user_id = ?
           GROUP BY month ORDER BY month DESC""",
        (user_id,)
    ).fetchall()
    return {row["month"]: float(row["total"]) for row in rows}


def get_category_spending(conn, user_id, start_date=None, end_date=None):
    """Get spending by category."""
    query = """
        SELECT c.name, c.icon, SUM(e.amount) as total, COUNT(*) as count
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
    """
    params = [user_id]
    
    if start_date:
        query += " AND e.date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND e.date <= ?"
        params.append(end_date)
    
    query += " GROUP BY c.id ORDER BY total DESC"
    
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def save_budget(conn, user_id, month, amount):
    """Save or update monthly budget."""
    conn.execute(
        """INSERT OR REPLACE INTO budgets (user_id, month, amount, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, month, amount)
    )
    conn.commit()


def get_budget(conn, user_id, month):
    """Get budget for a month."""
    row = conn.execute(
        "SELECT amount FROM budgets WHERE user_id = ? AND month = ?",
        (user_id, month)
    ).fetchone()
    return float(row["amount"]) if row else 0.0


def get_budgets(conn, user_id):
    """Get all budgets for a user."""
    rows = conn.execute(
        "SELECT month, amount FROM budgets WHERE user_id = ? ORDER BY month DESC",
        (user_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def save_category_limit(conn, user_id, category_id, limit_amount):
    """Save or update category spending limit."""
    conn.execute(
        """INSERT OR REPLACE INTO category_limits 
           (user_id, category_id, limit_amount, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, category_id, limit_amount)
    )
    conn.commit()


def get_category_limits(conn, user_id):
    """Get category limits for a user."""
    rows = conn.execute(
        """SELECT cl.id, c.name, c.icon, cl.limit_amount
           FROM category_limits cl
           JOIN categories c ON cl.category_id = c.id
           WHERE cl.user_id = ?
           ORDER BY c.name""",
        (user_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def delete_expense(conn, expense_id, user_id):
    """Delete an expense (verify user_id for security)."""
    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    conn.commit()


def update_expense(conn, expense_id, user_id, category_id, amount, date, description=""):
    """Update an expense."""
    conn.execute(
        """UPDATE expenses 
           SET category_id = ?, amount = ?, date = ?, description = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?""",
        (category_id, amount, date, description, expense_id, user_id)
    )
    conn.commit()


def clear_all_expenses(conn, user_id):
    """Delete all expenses for a user (for fresh start)."""
    conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.commit()


# ============================================================================
# INCOME FUNCTIONS
# ============================================================================

def add_income(conn, user_id, amount, source, date, description=""):
    """Add a new income entry."""
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO income 
           (user_id, amount, source, date, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (user_id, amount, source, date, description)
    )
    conn.commit()
    return cursor.lastrowid


def get_income(conn, user_id, start_date=None, end_date=None):
    """Get income entries with optional filters."""
    query = """
        SELECT id, amount, source, date, description
        FROM income
        WHERE user_id = ?
    """
    params = [user_id]
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " ORDER BY date DESC, id DESC"
    
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_monthly_income(conn, user_id):
    """Get total income by month."""
    rows = conn.execute(
        """SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
           FROM income WHERE user_id = ?
           GROUP BY month ORDER BY month DESC""",
        (user_id,)
    ).fetchall()
    return {row["month"]: float(row["total"]) for row in rows}


def get_income_sources(conn, user_id, start_date=None, end_date=None):
    """Get income grouped by source."""
    query = """
        SELECT source, SUM(amount) as total, COUNT(*) as count
        FROM income
        WHERE user_id = ?
    """
    params = [user_id]
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " GROUP BY source ORDER BY total DESC"
    
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def delete_income(conn, income_id, user_id):
    """Delete an income entry (verify user_id for security)."""
    conn.execute(
        "DELETE FROM income WHERE id = ? AND user_id = ?",
        (income_id, user_id)
    )
    conn.commit()


def update_income(conn, income_id, user_id, amount, source, date, description=""):
    """Update an income entry."""
    conn.execute(
        """UPDATE income 
           SET amount = ?, source = ?, date = ?, description = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?""",
        (amount, source, date, description, income_id, user_id)
    )
    conn.commit()
