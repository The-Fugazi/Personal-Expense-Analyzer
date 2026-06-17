"""UI Components for Personal Expense Analyzer.

Provides Streamlit-based UI components for rendering different pages
of the application with proper type hints, caching, and error handling.
"""

from typing import Callable, Dict, List, Optional, Tuple
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import datetime
import io
from db import (
    get_categories, add_expense, get_expenses, get_monthly_spending,
    get_category_spending, save_budget, get_budget, get_budgets,
    get_category_limits, save_category_limit, add_income, get_income,
    get_monthly_income, get_income_sources, clear_all_expenses
)

# UI Configuration Constants
CURRENCY_SYMBOL = "N"
CURRENCY_FORMAT = lambda x: f"{CURRENCY_SYMBOL}{x:,.0f}"
PAGE_NAMES = ["Dashboard", "Add Expense", "Analytics", "Settings"]
CHART_HEIGHT = 300
CHART_MARGIN = dict(l=0, r=0, t=0, b=0)
COLOR_PRIMARY = "#1f77b4"
COLOR_SECONDARY = "#2E86AB"
COLOR_ACCENT = "#A23B72"
DEFAULT_COLUMNS = [2, 1]

# Error Messages
ERROR_MESSAGES = {
    "required_fields": "All fields required",
    "password_mismatch": "Passwords don't match",
    "amount_invalid": "Amount must be greater than 0",
    "generic": "An error occurred. Please try again.",
}

# Success Messages
SUCCESS_MESSAGES = {
    "expense_added": "Added {category} expense for {amount}",
    "account_created": "Account created! Please login.",
    "budget_saved": "Budget for {month} set to {amount}",
    "limit_saved": "Limit set for {category}",
}


def _format_currency(value: float) -> str:
    """Format value as currency string.
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted currency string
    """
    return CURRENCY_FORMAT(value)


def _safe_get_data(func: Callable, *args, **kwargs) -> Optional[any]:
    """Safely execute database function with error handling.
    
    Args:
        func: Database function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result or None if error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"{ERROR_MESSAGES['generic']} ({str(e)})") 
        return None


@st.cache_data
def _get_category_dict(categories: List[Dict]) -> Dict[str, int]:
    """Convert categories list to name->id mapping.
    
    Args:
        categories: List of category dictionaries
        
    Returns:
        Dictionary mapping category names to IDs
    """
    return {cat['name']: cat['id'] for cat in categories}


def _render_metric_row(
    metrics: List[Tuple[str, str, Optional[str]]],
    num_columns: int = 4
) -> None:
    """Render a row of metric cards.
    
    Args:
        metrics: List of (label, value, delta) tuples
        num_columns: Number of columns for layout
    """
    if not metrics:
        return
        
    columns = st.columns(num_columns)
    for idx, (label, value, delta) in enumerate(metrics):
        with columns[idx % num_columns]:
            st.metric(label, value, delta=delta)


def _render_plotly_chart(
    fig: go.Figure,
    use_container_width: bool = True,
    height: int = CHART_HEIGHT
) -> None:
    """Render Plotly chart with consistent settings.
    
    Args:
        fig: Plotly figure object
        use_container_width: Whether to use full container width
        height: Chart height in pixels
    """
    fig.update_layout(
        height=height,
        margin=CHART_MARGIN,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=use_container_width)


def _clear_and_rerun() -> None:
    """Clear cache and rerun the application."""
    st.cache_data.clear()
    st.rerun()


def export_expenses_to_csv(expenses: List[Dict]) -> bytes:
    """Export expenses to CSV format.
    
    Args:
        expenses: List of expense dictionaries
        
    Returns:
        CSV data as bytes
    """
    if not expenses:
        return b""
    
    df = pd.DataFrame(expenses)
    # Extract just the date part (first 10 characters) to handle any datetime format
    df['date'] = df['date'].astype(str).str[:10]
    return df.to_csv(index=False).encode('utf-8')


def export_expenses_to_excel(expenses: List[Dict]) -> bytes:
    """Export expenses to Excel format with formatting.
    
    Args:
        expenses: List of expense dictionaries
        
    Returns:
        Excel data as bytes
    """
    if not expenses:
        return b""
    
    df = pd.DataFrame(expenses)
    # Extract just the date part (first 10 characters) to handle any datetime format
    df['date'] = df['date'].astype(str).str[:10]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Expenses', index=False)
        
        # Format Excel worksheet
        worksheet = writer.sheets['Expenses']
        for idx, col in enumerate(df.columns, 1):
            worksheet.column_dimensions[chr(64 + idx)].width = 15
    
    return output.getvalue()


def import_expenses_from_csv(uploaded_file) -> Tuple[bool, str, List[Dict]]:
    """Import expenses from CSV file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (success, message, expenses_list)
    """
    try:
        df = pd.read_csv(uploaded_file)
        required_cols = {'date', 'category', 'amount'}
        
        if not required_cols.issubset(df.columns):
            return False, f"CSV must contain columns: {', '.join(required_cols)}", []
        
        expenses = df.to_dict(orient='records')
        return True, f"Successfully imported {len(expenses)} expenses", expenses
    except Exception as e:
        return False, f"Error importing CSV: {str(e)}", []


def import_expenses_from_excel(uploaded_file) -> Tuple[bool, str, List[Dict]]:
    """Import expenses from Excel file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (success, message, expenses_list)
    """
    try:
        df = pd.read_excel(uploaded_file)
        required_cols = {'date', 'category', 'amount'}
        
        if not required_cols.issubset(df.columns):
            return False, f"Excel must contain columns: {', '.join(required_cols)}", []
        
        expenses = df.to_dict(orient='records')
        return True, f"Successfully imported {len(expenses)} expenses", expenses
    except Exception as e:
        return False, f"Error importing Excel: {str(e)}", []


def render_login_page(
    authenticate_user: Callable,
    register_user: Callable,
    get_connection: Callable
) -> None:
    """Render login and registration page.
    
    Args:
        authenticate_user: Authentication function
        register_user: User registration function
        get_connection: Database connection function
    """
    st.markdown("""
    <style>
    .login-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .login-subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .form-label {
        font-weight: 600;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-title">Personal Expense Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Track your expenses, manage your budget, achieve your financial goals</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("### Login")
        with st.form("login_form", clear_on_submit=True):
            login_username = st.text_input("Username", placeholder="Enter your username")
            login_password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if login_submitted:
                if not login_username or not login_password:
                    st.error(ERROR_MESSAGES["required_fields"])
                else:
                    with st.spinner("Authenticating..."):
                        conn = get_connection()
                        success, user_id, error = authenticate_user(conn, login_username, login_password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user_id
                            st.session_state.username = login_username
                            _clear_and_rerun()
                        else:
                            st.error(error)
    
    with col2:
        st.markdown("### Create Account")
        with st.form("register_form", clear_on_submit=True):
            reg_username = st.text_input("Username", key="reg_user", placeholder="Choose a username")
            reg_password = st.text_input("Password", key="reg_pass", type="password", placeholder="Create a password")
            reg_confirm = st.text_input("Confirm Password", key="reg_confirm", type="password", placeholder="Confirm password")
            register_submitted = st.form_submit_button("Register", use_container_width=True)
            
            if register_submitted:
                if not reg_username or not reg_password or not reg_confirm:
                    st.error(ERROR_MESSAGES["required_fields"])
                elif reg_password != reg_confirm:
                    st.error(ERROR_MESSAGES["password_mismatch"])
                else:
                    with st.spinner("Creating account..."):
                        conn = get_connection()
                        success, error = register_user(conn, reg_username, reg_password)
                        if success:
                            st.success(SUCCESS_MESSAGES["account_created"])
                        else:
                            st.error(error)


def render_sidebar(username: str) -> str:
    """Render sidebar navigation.
    
    Args:
        username: Current user's username
        
    Returns:
        Selected page name
    """
    with st.sidebar:
        st.title(f"User: {username}")
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            PAGE_NAMES,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            _clear_and_rerun()
    
    return page


def render_dashboard(conn, user_id: int) -> None:
    """Render enhanced financial dashboard page.
    
    Args:
        conn: Database connection
        user_id: Current user ID
    """
    # Custom CSS styling
    st.markdown("""
    <style>
    .dashboard-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2E86AB;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        font-weight: 500;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }
    .summary-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="dashboard-title">Financial Dashboard</div>', unsafe_allow_html=True)
    st.markdown("Track your expenses, manage budgets, and gain financial insights")
    
    today = datetime.date.today()
    current_month = today.strftime("%Y-%m")
    
    with st.spinner("Loading dashboard data..."):
        expenses = _safe_get_data(get_expenses, conn, user_id) or []
        monthly_spending = _safe_get_data(get_monthly_spending, conn, user_id) or {}
        current_month_spent = monthly_spending.get(current_month, 0.0)
        budget = _safe_get_data(get_budget, conn, user_id, current_month) or 0.0
        
        # Load income data
        income = _safe_get_data(get_income, conn, user_id) or []
        monthly_income = _safe_get_data(get_monthly_income, conn, user_id) or {}
        current_month_income = monthly_income.get(current_month, 0.0)
    
    total_spent = sum(monthly_spending.values())
    total_income = sum(monthly_income.values())
    net_savings = total_income - total_spent
    remaining_budget = budget - current_month_spent if budget > 0 else None
    
    # Dashboard Header with KPIs - Enhanced with colors
    st.markdown('<div class="section-title">Key Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    
    with col1:
        with st.container():
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="metric-label">Total Income</div>
                <div class="metric-value">{_format_currency(total_income)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="metric-label">Total Spent</div>
                <div class="metric-value">{_format_currency(total_spent)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        status_color = "#10b981" if net_savings >= 0 else "#ef4444"
        with st.container():
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {status_color} 0%, {status_color}dd 100%);">
                <div class="metric-label">Net Savings</div>
                <div class="metric-value">{_format_currency(net_savings)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        with st.container():
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="metric-label">Transactions</div>
                <div class="metric-value">{len(expenses) + len(income)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Summary Section
    st.markdown('<div class="section-title">Spending Summary</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    
    with col1:
        if monthly_spending:
            avg_monthly = total_spent / len(monthly_spending)
            st.metric("Average Monthly", _format_currency(avg_monthly), help="Average spending per month")
        else:
            st.metric("Average Monthly", _format_currency(0))
    
    with col2:
        if budget > 0:
            percent_spent = (current_month_spent / budget) * 100
            delta = f"{percent_spent:.1f}%"
            st.metric("Budget Used", delta, help=f"Out of {_format_currency(budget)}")
        else:
            st.metric("Budget Used", "No Budget", help="Set a budget in Settings")
    
    with col3:
        if expenses:
            avg_expense = total_spent / len(expenses)
            st.metric("Average Expense", _format_currency(avg_expense), help="Average per transaction")
        else:
            st.metric("Average Expense", _format_currency(0))
    
    st.divider()
    
    # Charts Section
    st.markdown('<div class="section-title">Spending Analytics</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(DEFAULT_COLUMNS)
    
    with col1:
        st.markdown("#### Monthly Trend")
        if monthly_spending and len(monthly_spending) > 0:
            # Filter out None keys and sort
            valid_months = [m for m in monthly_spending.keys() if m is not None]
            if valid_months:
                months = sorted(valid_months)
                amounts = [monthly_spending[m] for m in months]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=months, y=amounts,
                    mode='lines+markers',
                    name='Spending',
                    line=dict(color=COLOR_PRIMARY, width=3),
                    marker=dict(size=8, color=COLOR_PRIMARY),
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.2)',
                    hovertemplate='<b>%{x}</b><br>Amount: %{y:,.0f}<extra></extra>'
                ))
                fig.update_layout(
                    xaxis_title='Month',
                    yaxis_title='Amount',
                    height=CHART_HEIGHT,
                    margin=CHART_MARGIN,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No spending data available. Add your first expense!")
        else:
            st.info("No spending data available. Add your first expense!")
    
    with col2:
        st.markdown("#### Top 5 Categories")
        category_spending = _safe_get_data(get_category_spending, conn, user_id) or []
        
        if category_spending:
            top_cats = category_spending[:5]
            max_amount = max([c['total'] for c in top_cats])
            
            for idx, cat in enumerate(top_cats, 1):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    pct = (cat['total'] / max_amount) * 100 if max_amount > 0 else 0
                    st.markdown(f"**{idx}. {cat['name']}**")
                    st.progress(pct / 100, text=f"{pct:.0f}%")
                with col_b:
                    st.metric("Amount", _format_currency(cat['total']), label_visibility="collapsed")
        else:
            st.info("No category data available")
    
    st.divider()
    
    # Category Breakdown
    st.markdown('<div class="section-title">Category Breakdown</div>', unsafe_allow_html=True)
    category_spending = _safe_get_data(get_category_spending, conn, user_id) or []
    if category_spending:
        col1, col2 = st.columns([1, 1], gap="medium")
        
        with col1:
            cat_names = [c['name'] for c in category_spending]
            cat_amounts = [c['total'] for c in category_spending]
            
            fig = go.Figure(data=[go.Bar(
                y=cat_names,
                x=cat_amounts,
                orientation='h',
                marker=dict(
                    color=cat_amounts,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Amount", thickness=15)
                ),
                text=[_format_currency(x) for x in cat_amounts],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Amount: %{x:,.0f}<extra></extra>'
            )])
            fig.update_layout(
                xaxis_title='Amount',
                yaxis_title=None,
                height=CHART_HEIGHT + 100,
                margin=CHART_MARGIN,
                hovermode='y unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure(data=[go.Pie(
                labels=[c['name'] for c in category_spending],
                values=[c['total'] for c in category_spending],
                marker=dict(line=dict(color='white', width=2)),
                textposition='inside',
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>Amount: %{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
            )])
            fig.update_layout(
                height=CHART_HEIGHT + 100,
                margin=CHART_MARGIN
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category spending data available")
    
    st.divider()
    
    # Recent Transactions
    st.markdown('<div class="section-title">Recent Transactions</div>', unsafe_allow_html=True)
    if expenses:
        recent = expenses[:10]
        df = pd.DataFrame(recent)
        # Extract just the date part (first 10 characters) to handle any datetime format
        df['date'] = df['date'].astype(str).str[:10]
        df['amount'] = df['amount'].apply(_format_currency)
        
        st.dataframe(
            df[['date', 'category', 'amount', 'description']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'date': st.column_config.TextColumn('Date', width='small'),
                'category': st.column_config.TextColumn('Category', width='medium'),
                'amount': st.column_config.TextColumn('Amount', width='small'),
                'description': st.column_config.TextColumn('Description', width='large')
            }
        )
    else:
        st.info("No transactions yet. Add your first expense to get started!")
    
    st.divider()
    
    # Export Section
    st.markdown('<div class="section-title">Export Data</div>', unsafe_allow_html=True)
    st.markdown("Download your expense data for backup or analysis")
    
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        csv_data = export_expenses_to_csv(expenses)
        if csv_data:
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"expenses_{datetime.date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
                icon="📥"
            )
        else:
            st.info("No expenses to export yet")
    
    with col2:
        excel_data = export_expenses_to_excel(expenses)
        if excel_data:
            st.download_button(
                label="Download as Excel",
                data=excel_data,
                file_name=f"expenses_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                icon="📊"
            )
        else:
            st.info("No expenses to export yet")


def render_add_expense(conn, user_id: int) -> None:
    """Render add expense page with import functionality.
    
    Args:
        conn: Database connection
        user_id: Current user ID
    """
    st.markdown("""
    <style>
    .add-expense-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="add-expense-title">Add New Expense</div>', unsafe_allow_html=True)
    st.markdown("Record your spending or import from a file")
    
    st.divider()
    
    # Tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["Add Expense", "Add Income", "Import File"])
    
    with tab1:
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown("#### Record Transaction")
            with st.form("expense_form"):
                expense_date = st.date_input("Date", value=datetime.date.today())
                
                categories = _safe_get_data(get_categories, conn, user_id) or []
                if not categories:
                    st.error("No categories available")
                    return
                
                cat_options = _get_category_dict(categories)
                category_name = st.selectbox(
                    "Category",
                    options=list(cat_options.keys()),
                    help="Select expense category"
                )
                category_id = cat_options[category_name]
                
                amount = st.number_input(
                    f"Amount ({CURRENCY_SYMBOL})",
                    min_value=0.01,
                    step=0.01,
                    help="Enter expense amount"
                )
                
                description = st.text_area(
                    "Description (optional)",
                    max_chars=200,
                    placeholder="Add notes about this expense"
                )
                
                submitted = st.form_submit_button("Save Expense", type="primary", use_container_width=True)
                
                if submitted:
                    if amount <= 0:
                        st.error(ERROR_MESSAGES["amount_invalid"])
                    else:
                        with st.spinner("Saving expense..."):
                            try:
                                _safe_get_data(
                                    add_expense,
                                    conn, user_id, category_id, amount, expense_date, description
                                )
                                st.success(SUCCESS_MESSAGES["expense_added"].format(
                                    category=category_name,
                                    amount=_format_currency(amount)
                                ))
                                _clear_and_rerun()
                            except Exception as e:
                                st.error(f"{ERROR_MESSAGES['generic']} ({str(e)})") 
        
        with col2:
            st.markdown("#### Quick Stats")
            today = datetime.date.today()
            month_start = today.replace(day=1)
            
            month_expenses = _safe_get_data(
                get_expenses, conn, user_id, month_start.isoformat(), today.isoformat()
            ) or []
            
            if month_expenses:
                st.metric("Expenses This Month", len(month_expenses), help="Total transactions recorded")
                total = sum([e['amount'] for e in month_expenses])
                st.metric("Spending This Month", _format_currency(total), help="Total amount spent")
                
                budget = _safe_get_data(get_budget, conn, user_id, today.strftime("%Y-%m")) or 0.0
                if budget > 0:
                    remaining = budget - total
                    status = "Under budget" if remaining >= 0 else "Over budget"
                    st.write(f"**{status}**: {_format_currency(abs(remaining))}")
            else:
                st.info("No expenses this month yet. Add your first expense!")
    
    with tab2:
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown("#### Record Income")
            with st.form("income_form"):
                income_date = st.date_input("Date", value=datetime.date.today(), key="income_date")
                
                income_source = st.text_input(
                    "Income Source",
                    placeholder="e.g., Salary, Freelance, Business",
                    help="Where the income is from"
                )
                
                income_amount = st.number_input(
                    f"Amount ({CURRENCY_SYMBOL})",
                    min_value=0.01,
                    step=0.01,
                    help="Enter income amount",
                    key="income_amount"
                )
                
                income_description = st.text_area(
                    "Description (optional)",
                    max_chars=200,
                    placeholder="Add notes about this income",
                    key="income_description"
                )
                
                submitted_income = st.form_submit_button("Save Income", type="primary", use_container_width=True)
                
                if submitted_income:
                    if not income_source:
                        st.error("Please enter an income source")
                    elif income_amount <= 0:
                        st.error(ERROR_MESSAGES["amount_invalid"])
                    else:
                        with st.spinner("Saving income..."):
                            try:
                                _safe_get_data(
                                    add_income,
                                    conn, user_id, income_amount, income_source, income_date, income_description
                                )
                                st.success(f"Added {income_source} income for {_format_currency(income_amount)}")
                                _clear_and_rerun()
                            except Exception as e:
                                st.error(f"{ERROR_MESSAGES['generic']} ({str(e)})")
        
        with col2:
            st.markdown("#### Income Summary")
            today = datetime.date.today()
            month_start = today.replace(day=1)
            
            month_income = _safe_get_data(
                get_income, conn, user_id, month_start.isoformat(), today.isoformat()
            ) or []
            
            if month_income:
                st.metric("Income Entries", len(month_income), help="Total income records")
                total_income = sum([i['amount'] for i in month_income])
                st.metric("Income This Month", _format_currency(total_income), help="Total income received")
                
                expenses_this_month = _safe_get_data(
                    get_expenses, conn, user_id, month_start.isoformat(), today.isoformat()
                ) or []
                expenses_total = sum([e['amount'] for e in expenses_this_month])
                
                net = total_income - expenses_total
                status = "Saving" if net >= 0 else "Spending"
                st.write(f"**{status}**: {_format_currency(abs(net))}")
            else:
                st.info("No income recorded this month yet. Add your first income!")
    
    with tab3:
        st.markdown("#### Import Expenses")
        st.markdown("Upload a CSV or Excel file containing your expenses")
        
        file_type = st.radio("Select file type:", ["CSV", "Excel"], horizontal=True)
        uploaded_file = st.file_uploader(
            f"Upload {file_type} file",
            type=["csv"] if file_type == "CSV" else ["xlsx", "xls"],
            help="File must contain: date, category, amount columns"
        )
        
        if uploaded_file:
            st.info(f"File: {uploaded_file.name} | Size: {uploaded_file.size / 1024:.2f} KB")
            
            if file_type == "CSV":
                success, message, expenses = import_expenses_from_csv(uploaded_file)
            else:
                success, message, expenses = import_expenses_from_excel(uploaded_file)
            
            if success:
                st.success(message)
            else:
                st.error(message)
            
            if success and expenses:
                st.markdown("##### Preview")
                preview_df = pd.DataFrame(expenses[:5])
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
                
                if st.button("Import All Expenses", type="primary", use_container_width=True):
                    with st.spinner("Importing expenses..."):
                        imported_count = 0
                        errors = []
                        
                        categories = _safe_get_data(get_categories, conn, user_id) or []
                        cat_dict = {c['name']: c['id'] for c in categories}
                        
                        for expense in expenses:
                            try:
                                category_id = cat_dict.get(str(expense.get('category')))
                                if not category_id:
                                    errors.append(f"Category '{expense.get('category')}' not found")
                                    continue
                                
                                _safe_get_data(
                                    add_expense,
                                    conn,
                                    user_id,
                                    category_id,
                                    float(expense.get('amount', 0)),
                                    str(expense.get('date')),
                                    str(expense.get('description', ''))
                                )
                                imported_count += 1
                            except Exception as e:
                                errors.append(f"Error importing expense: {str(e)}")
                        
                        if imported_count > 0:
                            st.success(f"Successfully imported {imported_count} expenses!")
                            _clear_and_rerun()
                        
                        if errors:
                            with st.expander(f"View {len(errors)} errors"):
                                for error in errors:
                                    st.warning(error)
    
    st.divider()
    st.markdown("#### Recent Expenses")
    
    recent = _safe_get_data(get_expenses, conn, user_id) or []
    if recent:
        recent = recent[:20]
        df = pd.DataFrame(recent)
        # Extract just the date part (first 10 characters) to handle any datetime format
        df['date'] = df['date'].astype(str).str[:10]
        df['amount'] = df['amount'].apply(_format_currency)
        
        st.dataframe(
            df[['date', 'category', 'amount', 'description']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No expenses yet")


def render_analytics(conn, user_id: int) -> None:
    """Render analytics page.
    
    Args:
        conn: Database connection
        user_id: Current user ID
    """
    st.markdown("""
    <style>
    .analytics-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="analytics-title">Analytics & Insights</div>', unsafe_allow_html=True)
    st.markdown("Analyze your spending patterns and trends")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3, gap="medium")
    
    with col1:
        start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=90))
    
    with col2:
        end_date = st.date_input("End Date", value=datetime.date.today())
    
    with col3:
        categories = _safe_get_data(get_categories, conn, user_id) or []
        selected_cat = st.selectbox("Filter by Category", ["All"] + [c['name'] for c in categories])
    
    cat_id = None
    if selected_cat != "All" and categories:
        cat_id = next((c['id'] for c in categories if c['name'] == selected_cat), None)
    
    with st.spinner("Loading analytics..."):
        expenses = _safe_get_data(
            get_expenses, conn, user_id, start_date.isoformat(), end_date.isoformat(), cat_id
        ) or []
    
    if expenses:
        df = pd.DataFrame(expenses)
        total = df['amount'].sum()
        avg = df['amount'].mean()
        max_exp = df['amount'].max()
        
        st.markdown("### Key Statistics")
        metrics = [
            ("Total Spending", _format_currency(total), None),
            ("Average", _format_currency(avg), None),
            ("Largest", _format_currency(max_exp), None),
            ("Transactions", str(len(expenses)), None),
        ]
        _render_metric_row(metrics)
        
        st.divider()
        
        st.markdown("### Detailed Analysis")
        col1, col2 = st.columns([1, 1], gap="medium")
        
        with col1:
            st.markdown("#### Daily Spending Trend")
            daily = df.groupby('date')['amount'].sum().sort_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=daily.index,
                y=daily.values,
                marker=dict(
                    color=daily.values,
                    colorscale='Reds',
                    showscale=True,
                    colorbar=dict(title="Amount")
                ),
                text=[_format_currency(x) for x in daily.values],
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>Amount: %{y:,.0f}<extra></extra>'
            ))
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Amount',
                height=CHART_HEIGHT,
                margin=CHART_MARGIN,
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Spending by Category")
            cat_data = df.groupby('category')['amount'].sum().sort_values(ascending=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cat_data.values,
                y=cat_data.index,
                orientation='h',
                marker=dict(
                    color=cat_data.values,
                    colorscale='Blues',
                    showscale=True,
                    colorbar=dict(title="Amount")
                ),
                text=[_format_currency(x) for x in cat_data.values],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Amount: %{x:,.0f}<extra></extra>'
            ))
            fig.update_layout(
                xaxis_title='Amount',
                yaxis_title=None,
                height=CHART_HEIGHT,
                margin=CHART_MARGIN,
                hovermode='y unified'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expenses in selected range. Try adjusting your filters.")


def render_settings(conn, user_id: int) -> None:
    """Render settings page.
    
    Args:
        conn: Database connection
        user_id: Current user ID
    """
    st.markdown("""
    <style>
    .settings-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .tab-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2E86AB;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="settings-title">Settings & Configuration</div>', unsafe_allow_html=True)
    st.markdown("Manage your categories, budgets, and spending limits")
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Categories", "Budget", "Spending Limits", "Data Management"])
    
    with tab1:
        st.markdown('<div class="tab-title">Manage Categories</div>', unsafe_allow_html=True)
        categories = _safe_get_data(get_categories, conn, user_id) or []
        
        if categories:
            cols = st.columns(2, gap="large")
            for idx, cat in enumerate(categories):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div style="background: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                        <p style="margin: 0; font-weight: 600; color: #333;">{idx + 1}. {cat['name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No categories available")
    
    with tab2:
        st.markdown('<div class="tab-title">Monthly Budget</div>', unsafe_allow_html=True)
        st.markdown("Set and track your monthly spending target")
        
        today = datetime.date.today()
        month_options = pd.date_range(
            today - pd.DateOffset(years=1), today, freq='MS'
        ).strftime('%Y-%m').tolist()
        
        col1, col2 = st.columns([1, 1], gap="medium")
        
        with col1:
            month = st.selectbox(
                "Select Month",
                month_options,
                index=0,
                help="Choose month to set budget"
            )
        
        current_budget = _safe_get_data(get_budget, conn, user_id, month) or 0.0
        
        with col2:
            new_budget = st.number_input(
                f"Budget Amount ({CURRENCY_SYMBOL})",
                value=current_budget,
                min_value=0.0,
                step=1000.0,
                help="Set monthly budget target"
            )
        
        if st.button("Save Budget", use_container_width=True, type="primary"):
            with st.spinner("Saving budget..."):
                _safe_get_data(save_budget, conn, user_id, month, new_budget)
                st.success(SUCCESS_MESSAGES["budget_saved"].format(
                    month=month,
                    amount=_format_currency(new_budget)
                ))
                _clear_and_rerun()
        
        st.divider()
        st.markdown("#### Budget History")
        
        budgets = _safe_get_data(get_budgets, conn, user_id) or []
        if budgets:
            budget_df = pd.DataFrame(budgets)
            budget_df['amount'] = budget_df['amount'].apply(_format_currency)
            budget_df = budget_df[['month', 'amount']]
            st.dataframe(budget_df, use_container_width=True, hide_index=True)
        else:
            st.info("No budget history yet")
    
    with tab3:
        st.markdown('<div class="tab-title">Category Spending Limits</div>', unsafe_allow_html=True)
        st.markdown("Set maximum spending limits for each category")
        
        categories = _safe_get_data(get_categories, conn, user_id) or []
        
        if categories:
            col1, col2 = st.columns([1, 1], gap="medium")
            
            with col1:
                category_name = st.selectbox(
                    "Category",
                    [c['name'] for c in categories],
                    help="Select category to set spending limit"
                )
                category_id = next(c['id'] for c in categories if c['name'] == category_name)
            
            with col2:
                limit_amount = st.number_input(
                    f"Spending Limit ({CURRENCY_SYMBOL})",
                    min_value=0.01,
                    step=100.0,
                    help="Set maximum spending limit for this category"
                )
            
            if st.button("Save Limit", use_container_width=True, type="primary"):
                with st.spinner("Saving limit..."):
                    _safe_get_data(save_category_limit, conn, user_id, category_id, limit_amount)
                    st.success(SUCCESS_MESSAGES["limit_saved"].format(category=category_name))
                    _clear_and_rerun()
            
            st.divider()
            st.markdown("#### Current Limits")
            
            limits = _safe_get_data(get_category_limits, conn, user_id) or []
            if limits:
                col1, col2 = st.columns([2, 1], gap="medium")
                for limit in limits:
                    with col1:
                        st.markdown(f"**{limit['name']}**")
                    with col2:
                        st.write(_format_currency(limit['limit_amount']))
            else:
                st.info("No limits set yet")
        else:
            st.info("No categories available")
    
    with tab4:
        st.markdown('<div class="tab-title">Data Management</div>', unsafe_allow_html=True)
        st.markdown("Manage and clean your expense data")
        
        st.divider()
        
        st.markdown("#### Clear All Expenses")
        st.warning("This will permanently delete ALL your expenses. This action cannot be undone!")
        
        if 'show_delete_confirmation' not in st.session_state:
            st.session_state.show_delete_confirmation = False
        
        if not st.session_state.show_delete_confirmation:
            if st.button("Clear All Expenses", type="secondary", use_container_width=True):
                st.session_state.show_delete_confirmation = True
                st.rerun()
        else:
            st.error("Are you absolutely sure? This will delete ALL expenses permanently!")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Cancel", use_container_width=True, key="cancel_delete"):
                    st.session_state.show_delete_confirmation = False
                    st.rerun()
            
            with col2:
                if st.button("Yes, Delete All", type="primary", use_container_width=True, key="confirm_delete"):
                    with st.spinner("Deleting all expenses..."):
                        try:
                            _safe_get_data(clear_all_expenses, conn, user_id)
                            st.success("All expenses have been deleted successfully!")
                            st.session_state.show_delete_confirmation = False
                            st.balloons()
                            import time
                            time.sleep(2)
                            _clear_and_rerun()
                        except Exception as e:
                            st.error(f"Error deleting expenses: {str(e)}")
                            st.session_state.show_delete_confirmation = False
