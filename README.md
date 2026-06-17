# Personal Expense Analyzer

A professional Streamlit web application for tracking personal expenses, managing budgets, and analyzing spending patterns with income tracking and cash flow analysis.

## Features

### 💰 Expense & Income Tracking
- Record expenses by category with date, amount, and description
- Track income from multiple sources (Salary, Freelance, Business, etc.)
- CSV and Excel import/export functionality
- Edit and delete transactions

### 📊 Dashboard & Analytics
- **Key Metrics**: Total income, total spending, net savings, transaction count
- **Cash Flow Analysis**: Side-by-side monthly income vs expense chart
- **Spending Analytics**: Monthly trends, category breakdown (bar and pie charts)
- **Category Insights**: Top spending categories with visualizations
- **Recent Transactions**: View and manage all transactions

### 💳 Budget Management
- Set monthly spending targets
- Track category-specific spending limits
- Budget vs actual comparison
- Monthly budget history

### 🎯 Smart Features
- Category presets for quick expense entry
- Professional gradient UI with responsive design
- Multi-user support with secure authentication
- SQLite database for local data storage

## Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Database**: SQLite
- **Data Processing**: Pandas
- **Visualization**: Plotly, Matplotlib
- **Language**: Python 3.8+

## Project Structure

```
personal-expense-analyzer/
├── app.py              # Main application entry point
├── db.py               # Database operations & queries
├── ui.py               # UI components & page rendering
├── expenses.db         # Local SQLite database
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/personal-expense-analyzer.git
   cd personal-expense-analyzer
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

The app will open in your browser at `http://localhost:8501`

## Usage

### First Time Setup
1. **Register**: Create a new account with username and password
2. **Login**: Sign in with your credentials
3. **Add Categories**: (Optional) Customize your expense categories in Settings
4. **Set Budget**: Define your monthly budget in Settings

### Recording Transactions

#### Adding Expenses
1. Go to "Add Expense" tab
2. Select date, category, and amount
3. Add optional description
4. Click "Save Expense"

#### Adding Income
1. Go to "Add Expense" → "Add Income" tab
2. Enter income source, amount, and date
3. Add optional description
4. Click "Save Income"

#### Importing Data
1. Go to "Add Expense" → "Import File" tab
2. Upload CSV or Excel file with columns: `date`, `category`, `amount`
3. Review preview and click "Import All Expenses"

### Viewing Analytics
1. **Dashboard**: Overview of financial summary and cash flow
2. **Analytics**: Detailed spending analysis with date filters and category filters
3. **Settings**: Manage budgets, categories, and spending limits

## Database Schema

### Tables
- **users**: User accounts with authentication
- **categories**: Expense categories (per user)
- **expenses**: Transaction records
- **income**: Income entries
- **budgets**: Monthly budget targets
- **category_limits**: Spending limits per category

## File Format for Import

### CSV/Excel Format Required:
```
date,category,amount
2026-05-01,Groceries,5000
2026-05-02,Transport,2000
2026-05-05,Dining,3500
```

**Required Columns**:
- `date`: YYYY-MM-DD format
- `category`: Category name (must exist in system)
- `amount`: Numeric value

## Features by Page

### Dashboard
- Quick overview of financial status
- Key performance indicators (Income, Spending, Savings, Transactions)
- Cash flow analysis chart (income vs expenses by month)
- Category spending breakdown (bar and pie charts)
- Recent transactions list

### Add Expense
- **Add Expense**: Single expense entry form with quick stats
- **Add Income**: Income recording form with source tracking
- **Import File**: Bulk import from CSV or Excel

### Analytics
- Customizable date range filtering
- Category-specific analysis
- Daily spending trends
- Spending distribution

### Settings
- Category management
- Monthly budget configuration
- Category spending limits
- Budget history view

## Currency

Default currency: **Nigerian Naira (₦)**

Easily modify in `ui.py`:
```python
CURRENCY_SYMBOL = "N"  # Change to your currency symbol
```

## Security

- User authentication with hashed passwords (SHA256)
- Per-user data isolation
- Local SQLite database (no external servers)
- All data stored locally on your machine

## Troubleshooting

### App won't start
```bash
# Ensure venv is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\Activate.ps1  # Windows

# Reinstall dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

### Import errors
- Ensure CSV/Excel has correct column names: `date`, `category`, `amount`
- Date format must be YYYY-MM-DD
- Categories must already exist in the system

### Database issues
- Delete `expenses.db` to reset (WARNING: loses all data)
- Let app auto-create new database on restart

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

---

**Made with ❤️ for better financial management**