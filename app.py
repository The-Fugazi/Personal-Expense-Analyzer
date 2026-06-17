"""Personal Expense Analyzer - Application Entry Point"""

import streamlit as st
import datetime
import hashlib
import re
import sqlite3
from db import get_connection, init_database, create_default_categories
from ui import (
    render_login_page, render_sidebar, render_dashboard,
    render_add_expense, render_analytics, render_settings
)

# Page Configuration
st.set_page_config(
    page_title="Personal Expense Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database
init_database()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

# Authentication Functions
def hash_password(password):
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_username(username):
    """Validate username format."""
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username cannot exceed 30 characters"
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    return True, None

def validate_password(password):
    """Validate password strength."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters"
    return True, None

def register_user(conn, username, password):
    """Register new user in database."""
    valid, error = validate_username(username)
    if not valid:
        return False, error
    
    valid, error = validate_password(password)
    if not valid:
        return False, error
    
    try:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        
        # Create default categories for new user
        user_id = cursor.lastrowid
        create_default_categories(conn, user_id)
        
        return True, "User registered successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, f"Registration error: {str(e)}"

def authenticate_user(conn, username, password):
    """Authenticate user and return user_id."""
    try:
        password_hash = hash_password(password)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        result = cursor.fetchone()
        if result:
            return True, result[0], "Login successful"
        return False, None, "Invalid username or password"
    except Exception as e:
        return False, None, f"Authentication error: {str(e)}"

# Main Application
if not st.session_state.authenticated:
    render_login_page(authenticate_user, register_user, get_connection)
else:
    conn = get_connection()
    user_id = st.session_state.user_id
    username = st.session_state.username
    
    page = render_sidebar(username)
    
    if page == "Dashboard":
        render_dashboard(conn, user_id)
    
    elif page == "Add Expense":
        render_add_expense(conn, user_id)
    
    elif page == "Analytics":
        render_analytics(conn, user_id)
    
    elif page == "Settings":
        render_settings(conn, user_id)
