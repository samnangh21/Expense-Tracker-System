# Expense-Tracker-System

A command-line expense tracker built in Python with object-oriented design, user authentication with role-based access, full CRUD operations, keyword search, and visual reports.

## Features

- **User Authentication**
  - Register, login, logout
  - Two roles: `user` and `admin`
  - Password validation (minimum length)
  - Passwords are salted and hashed (never stored in plain text)
  - Login lockout after repeated failed attempts

- **CRUD Operations**
  - Create, view, edit, and delete income/expense transactions
  - Separate categories for income and expense, with admin management (add, rename, delete)
  - Admin can manage user accounts (create, delete, reset password)

- **Search**
  - Keyword search across note, category, and transaction type
  - Case-insensitive, partial-match search
  - Admins can search across all users

- **Reports and Charts**
  - Balance summary (total income, total expense, net balance)
  - Category and monthly breakdown (via Pandas)
  - Line graph: income vs. expenses over a chosen month
  - Pie chart: expenses by category
  - Admin tool to analyze any user's expenses by month

- **Styled Terminal UI**
  - Built with `rich` for colored panels, tables, and menus
  - Clears and redraws the screen between steps for an app-like feel

## Project Structure

```
Expense_Tracker_system/
├── main.py                # Menus, user input, and the App class
├── storage.py              # Reads and writes JSON data files
├── models/
│   ├── __init__.py
│   ├── user.py              # User and Admin classes (inheritance, encapsulation)
│   ├── transaction.py       # Transaction class and validation
│   └── category.py          # Category class and validation
├── services/
│   ├── __init__.py
│   ├── auth.py               # Registration, login, password rules, user management
│   ├── tracker.py            # Transaction CRUD, categories, search, balance
│   └── report.py             # Pandas reports and matplotlib charts
├── data/                    # JSON data files (created automatically)
│   ├── users.json
│   ├── transactions.json
│   └── categories.json
├── requirements.txt
└── README.md
```

## Object-Oriented Design

| Concept | Where it's used |
|---|---|
| **Encapsulation** | `User.__password_hash` and `User.__salt` are private, accessed only through methods like `check_password()` |
| **Inheritance** | `Admin` inherits from `User` and adds admin-only behavior |
| **Polymorphism** | `User.get_menu()` and `Admin.get_menu()` return different menus for the same method call |
| **Abstraction** | `AuthService` and `TrackerService` hide file I/O and validation details from `main.py` |

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt` (pandas, matplotlib, rich, and their sub-dependencies)

## Setup

1. Create and activate a virtual environment:
   ```powershell
   python -m venv expenv
   expenv\Scripts\Activate
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Run the program:
   ```powershell
   python main.py
   ```

On first run, a default admin account is created automatically. The username and password are shown once in the terminal — log in and change the password right away.

## Usage

- From the **Start menu**, log in or register a new account.
- **Regular users** can add income/expense, view/edit/delete their own transactions, search, view reports and charts, and change their password.
- **Admins** can view all transactions, analyze any user's monthly expenses, manage categories, and manage user accounts.

## Data Storage

All data is stored locally in JSON files under the `data/` folder:
- `users.json` — usernames, hashed passwords, roles
- `transactions.json` — all income and expense records
- `categories.json` — income and expense category lists

Dates are stored and displayed in `DD-MM-YYYY` format.

## Notes

- This is a learning project built for a Python fundamentals course. Password hashing uses `hashlib`/`pbkdf2_hmac`, which is appropriate for coursework but not a substitute for production-grade authentication systems.
- Terminal output uses the [`rich`](https://github.com/Textualize/rich) library for colors, tables, and panels. For best results, run in a modern terminal (e.g. Windows Terminal) rather than the legacy PowerShell console host.
