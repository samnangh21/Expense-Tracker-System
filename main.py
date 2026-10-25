"""Expense Tracker: menus and user input. All the real work is done by the services."""
import os
import time
from datetime import date, datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from models import Transaction
from services.auth import AuthService, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from services.tracker import TrackerService
from storage import Storage

CURRENCY = "$"
console = Console()


# =============================================================================
# Small input helpers (they keep asking until the answer is valid)
# =============================================================================

def clear_screen():
    os.system("cls")
    console.clear()

def ask(prompt):
    return Prompt.ask(f"[cyan]{prompt}[/cyan]").strip()


def ask_valid(prompt, validator, allow_blank=False):
    """Ask until `validator` accepts the text. Returns None for a blank answer if allowed."""
    while True:
        text = ask(prompt)
        if allow_blank and text == "":
            return None
        try:
            return validator(text)
        except ValueError as error:
            console.print(f"  [red]Error:[/red] {error}")


def ask_choice(prompt, count):
    """Ask for a menu number from 1 to count."""
    while True:
        text = ask(prompt)
        if text.isdecimal() and 1 <= int(text) <= count:
            return int(text)
        console.print(f"  [red]please enter a number from 1 to {count}.")


def confirm(question):
    return Confirm.ask(f"[yellow]{question}[/yellow]")

def pause():
    console.print("\n[grey50]Press Enter to continue...[/grey50]", end="")
    input()

def parse_id(text):
    if not text.isdecimal() or int(text) < 1:
        raise ValueError("Please enter a valid ID number.")
    return int(text)


def parse_keyword(text):
    if not text:
        raise ValueError("Please type a keyword.")
    return text


def choose_category(tracker, type, allow_blank=False, current=None):
    """Show the numbered category list (for this type) and return the chosen name."""
    names = tracker.category_names(type)
    table = Table(title=f"{type.capitalize()} categories", show_header=False, border_style="grey50")
    for number, name in enumerate(names, start=1):
        table.add_row(f"[cyan]{number}[/cyan]", name)
    console.print(table)
    prompt = "Category number" if current is None else f"Category number [{current}]"
    while True:
        text = ask(f"{prompt}: ")
        if text == "" and allow_blank:
            return None
        if text.isdecimal() and 1 <= int(text) <= len(names):
            return names[int(text) - 1]
        console.print(f"  [red]Error:[/red] please enter a number from 1 to {len(names)}.")


# =============================================================================
class App:
    def __init__(self):
        storage = Storage()
        self.auth = AuthService(storage)
        self.tracker = TrackerService(storage)
        # Menu action names (from get_menu) -> the method that runs them.
        self.actions = {
            "add_income": lambda: self.add_transaction("income"),
            "add_expense": lambda: self.add_transaction("expense"),
            "view_transactions": self.view_transactions,
            "edit_transaction": self.edit_transaction,
            "delete_transaction": self.delete_transaction,
            "search": self.search,
            "report": self.report,
            "charts": self.charts,
            "change_password": self.change_password,
            "view_all": self.view_all,
            "analyze_users": self.analyze_users,
            "manage_categories": self.manage_categories,
            "manage_users": self.manage_users,
            "logout": self.logout,
        }

    # ---- start menu ---------------------------------------------------------
    def run(self):
        while True:
            console.screen()
            console.print(Panel("[bold]Welcome to the Expense Tracker![/bold]", style="green"))
            if self.auth.default_admin_created:
                console.print(
                    f"[yellow]First run:[/yellow] an admin account was created "
                    f"(username: [bold]{DEFAULT_ADMIN_USERNAME}[/bold], "
                    f"password: [bold]{DEFAULT_ADMIN_PASSWORD}[/bold])."
                )
                console.print("Please log in and change the password.")
            console.print(Panel("[ 1 ] Login\n[ 2 ] Register\n[ 3 ] Exit", title="Start menu", style="blue"))
            choice = ask_choice("Choose: ", 3)
            if choice == 1:
                self.login()
            elif choice == 2:
                self.register()
            else:
                console.print("[bold]Goodbye![/bold]")
                break

    def register(self):
        clear_screen()
        console.print(Panel("Register", style="blue"))
        # console.print("Username: 3-20 letters, numbers or underscore.")
        # console.print("Password: at least 4 characters.")
        username = ask("Username ")
        password = ask("Password ")
        confirm_password = ask("Confirm password ")

        with console.status("[cyan]Creating account...[/cyan]", spinner="dots"):
            time.sleep(1)
            try:
                self.auth.register(username, password, confirm_password)
                error = None
            except ValueError as e:
                error = e

        if error is not None:
            console.print(f"[red]Could not register:[/red]\n{error}")
            return

        console.print(f"[green]✔ Account created! Welcome, {username}.[/green] You can now log in.")

    def login(self):
        clear_screen()
        console.print(Panel("Login", style="blue"))
        username = ask("Username ")
        password = ask("Password ")

        with console.status("[cyan]Verifying credentials...[/cyan]", spinner="dots"):
            time.sleep(1)
            try:
                user = self.auth.login(username, password)
                error = None
            except ValueError as e:
                user = None
                error = e

        if user is None:
            console.print(f"[red]Login failed:[/red] {error}")
            return

        console.print(f"[green]✔ Login successful! Welcome, {user.username}[/green]")

        with console.status("[cyan]Loading system...[/cyan]", spinner="dots"):
            time.sleep(3)

        if self.auth.uses_default_password(user):
            console.print("[yellow]Warning: you are using the default password. "
                        "Please change it (Change password).[/yellow]")
        self.session()

    # ---- role menu (runs until logout) ----------------------------------------
    def session(self):
        while self.auth.current_user is not None:
            clear_screen()
            user = self.auth.current_user
            menu = user.get_menu()
            lines = "\n".join(f"{n}. {label}" for n, (label, _a) in enumerate(menu, start=1))
            console.print(Panel(lines, title=f"Menu: {user.username} ({user.role})", style="blue"))
            choice = ask_choice("Choose", len(menu))
            action = menu[choice - 1][1]
            self.actions[action]()
            if self.auth.current_user is not None:  # skip the pause if this action logged out
                pause()

    def logout(self):
        self.auth.logout()
        console.print("[green]You have been logged out.[/green]")

    # ---- display helpers ------------------------------------------------------
    def print_transactions(self, rows, show_user=False, title="Transactions"):
        table = Table(title=title, border_style="grey50")
        table.add_column("ID", style="cyan", justify="right")
        if show_user:
            table.add_column("User")
        table.add_column("Date")
        table.add_column("Type")
        table.add_column("Category")
        table.add_column(f" Amount($)({CURRENCY})", justify="right")
        table.add_column("Note")
        for t in rows:
            type_style = "green" if t.type == "income" else "red"
            row = [str(t.id)]
            if show_user:
                row.append(self.auth.get_username(t.user_id))
            row += [
                t.date,
                f"[{type_style}]{t.type}[/{type_style}]",
                t.category,
                f"{t.amount:,.2f}",
                t.note,
            ]
            table.add_row(*row)
        console.print(table)

    # ---- Create ------------------------------------------------------------------
    def add_transaction(self, trans_type):
        console.print(Panel(f"Add {trans_type}", style="blue"))
        amount = ask_valid("Amount($) ", Transaction.validate_amount)
        category = choose_category(self.tracker, trans_type)
        date_text = ask_valid("Date DD-MM-YYYY (Enter = today) ",
                            Transaction.validate_date, allow_blank=True)
        if date_text is None:
            date_text = date.today().strftime("%d-%m-%Y")
        note = ask_valid("Note (optional) ", Transaction.validate_note)

        with console.status("[cyan]Saving...[/cyan]", spinner="dots"):
            time.sleep(1.5)
            try:
                t = self.tracker.add_transaction(
                    self.auth.current_user, trans_type, amount, category, date_text, note)
                error = None
            except ValueError as e:
                t = None
                error = e

        if error is not None:
            console.print(f"[red]Could not save:[/red] {error}")
            return

        console.print(f"[green]✔ Saved![/green] {t.type} of {CURRENCY}{t.amount:,.2f} "
                    f"in {t.category} (ID {t.id}).")

    # ---- Read ----------------------------------------------------------------------
    def view_transactions(self):
        # clear_screen()
        rows = self.tracker.get_transactions(self.auth.current_user)
        if not rows:
            console.print("[yellow]You have no transactions yet.[/yellow]")
            return
        self.print_transactions(rows, title="Your transactions")

    def view_all_transactions(self):
        rows = self.tracker.get_transactions(self.auth.current_user, include_all=True)
        if not rows:
            console.print("[yellow]There are no transactions yet.[/yellow]")
            return
        self.print_transactions(rows, show_user=True, title="All transactions")

    def view_user_transactions(self):
        self.list_users()
        user_id = ask_valid("Enter a user ID to view (Enter to cancel)", parse_id, allow_blank=True)
        if user_id is None:
            return
        target = self.auth.find_by_id(user_id)
        if target is None:
            console.print("[red]User not found.[/red]")
            return
        rows = [t for t in self.tracker.get_transactions(self.auth.current_user, include_all=True)
                if t.user_id == user_id]
        if not rows:
            console.print(f"[yellow]{target.username} has no transactions.[/yellow]")
            return
        self.print_transactions(rows, title=f"Transactions for {target.username}")

    def view_all(self):
        while True:
            clear_screen()
            console.print(Panel("1. All transactions\n2. View user\n3. Back",
                                title="View transaction", style="blue"))
            choice = ask_choice("Choose ", 3)
            if choice == 1:
                self.view_all_transactions()
            elif choice == 2:
                self.view_user_transactions()
            else:
                return

            if choice != 3:
                pause()

    # ---- Update ----------------------------------------------------------------------
    def edit_transaction(self):
        # clear_screen()
        user = self.auth.current_user
        rows = self.tracker.get_transactions(user)
        if not rows:
            console.print("[yellow]You have no transactions to edit.[/yellow]")
            return
        self.print_transactions(rows, title="Your transactions")
        transaction_id = ask_valid("Enter the ID to edit (Enter to cancel): ", parse_id, allow_blank=True)
        if transaction_id is None:
            return
        try:
            current = self.tracker.get_own(user, transaction_id)
        except ValueError as error:
            console.print(f"[red]{error}[/red]")
            return

        def check_note(text):
            return "" if text == "-" else Transaction.validate_note(text)

        console.print("[grey50]Press Enter to keep the current value.[/grey50]")
        trans_type = ask_valid(f"Type (income/expense) [{current.type}] ",
                       Transaction.validate_type, allow_blank=True)
        amount = ask_valid(f"Amount($) [{current.amount}] ", Transaction.validate_amount, allow_blank=True)
        category = choose_category(self.tracker, trans_type or current.type,
                                allow_blank=True, current=current.category)
        date_text = ask_valid(f"Date [{current.date}] ", Transaction.validate_date, allow_blank=True)
        note = ask_valid(f"Note [{current.note}] (type - to clear) ", check_note, allow_blank=True)
        try:
            self.tracker.update_transaction(user, transaction_id, trans_type, amount, category, date_text, note)
            console.print("[green]Transaction updated.[/green]")
        except ValueError as error:
            console.print(f"[red]Could not update[:/red] {error}")

    # ---- Delete ----------------------------------------------------------------------
    def delete_transaction(self):
        # clear_screen()
        user = self.auth.current_user
        rows = self.tracker.get_transactions(user)
        if not rows:
            console.print("[yellow]You have no transactions to delete.[/yellow]")
            return
        self.print_transactions(rows, title="Your transactions")
        transaction_id = ask_valid("Enter the ID to delete (Enter to cancel) ", parse_id, allow_blank=True)
        if transaction_id is None:
            return
        try:
            self.tracker.get_own(user, transaction_id)
        except ValueError as error:
            console.print(f"[red]{error}[/red]")
            return
        if confirm(f"Delete transaction {transaction_id}?"):
            self.tracker.delete_transaction(user, transaction_id)
            console.print("[green]Transaction deleted.[/green]")
        else:
            console.print("Cancelled.")

    # ---- Search ----------------------------------------------------------------------
    def search(self):
        # clear_screen()
        user = self.auth.current_user
        keyword = ask_valid("Keyword (searches note, category and type): ", parse_keyword)
        include_all = user.can_manage_users() and confirm("Search all users' transactions?")
        results = self.tracker.search(user, keyword, include_all)
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        self.print_transactions(results, show_user=include_all, title=f"{len(results)} result(s)")

    # ---- Balance and report ----------------------------------------------------------
    def report(self):
        # clear_screen()
        user = self.auth.current_user
        income, expense, balance = self.tracker.get_balance(user)
        balance_style = "green" if balance >= 0 else "red"
        console.print(Panel(
            f"Total income : [green]{CURRENCY}{income:,.2f}[/green]\n"
            f"Total expense: [red]{CURRENCY}{expense:,.2f}[/red]\n"
            f"Balance      : [{balance_style}]{CURRENCY}{balance:,.2f}[/{balance_style}]",
            title="Balance", style="blue"
        ))
        rows = self.tracker.get_transactions(user)
        if not rows:
            return
        try:
            from services import report as report_tools
        except ImportError:
            console.print("[yellow](Reports need Pandas. Run: pip install -r requirements.txt)[/yellow]")
            return

        cat_df = report_tools.category_report(rows)
        cat_table = Table(title="By category", border_style="grey50")
        for col in cat_df.columns:
            cat_table.add_column(str(col))
        for _, row in cat_df.iterrows():
            cat_table.add_row(*[str(v) for v in row])
        console.print(cat_table)

        month_df = report_tools.monthly_report(rows)
        month_table = Table(title="By month", border_style="grey50")
        month_table.add_column("Month")
        for col in month_df.columns:
            month_table.add_column(str(col))
        for idx, row in month_df.iterrows():
            month_table.add_row(str(idx), *[str(v) for v in row])
        console.print(month_table)

    # ---- Charts -----------------------------------------------------------------------
    def charts(self):
        user = self.auth.current_user
        rows = self.tracker.get_transactions(user)
        if not rows:
            console.print("[yellow]You have no transactions to chart.[/yellow]")
            return

        months = sorted(
            {datetime.strptime(t.date, "%d-%m-%Y").strftime("%m-%Y") for t in rows},
            key=lambda m: datetime.strptime(m, "%m-%Y"),
        )
        console.print(Panel("\n".join(f"{n}. {m}" for n, m in enumerate(months, start=1)),
                            title="Choose a month", style="blue"))
        choice = ask_choice("Choose a month ", len(months))
        chosen_month = months[choice - 1]
        month_rows = [t for t in rows
                    if datetime.strptime(t.date, "%d-%m-%Y").strftime("%m-%Y") == chosen_month]

        try:
            from services import report as report_tools
        except ImportError:
            console.print("[yellow]Charts need matplotlib. Run: pip install matplotlib[/yellow]")
            return

        label = f"{user.username} ({chosen_month})"
        console.print(Panel("1. Line graph (income vs expenses)\n2. Pie chart (expenses by category)",
                            title="View charts", style="blue"))
        choice = ask_choice("Choose ", 2)
        if choice == 1:
            report_tools.income_expense_line_chart(month_rows, label)
        else:
            expense_only = [t for t in month_rows if t.type == "expense"]
            report_tools.expense_pie_chart(expense_only, label)
            
    # ---- Analyze users (admin) ---------------------------------------------------------
    def analyze_users(self):
        self.list_users()
        user_id = ask_valid("Enter a user ID to analyze (Enter to cancel) ", parse_id, allow_blank=True)
        if user_id is None:
            return
        target = self.auth.find_by_id(user_id)
        if target is None:
            console.print("[red]User not found.[/red]")
            return

        all_rows = self.tracker.get_transactions(self.auth.current_user, include_all=True)
        rows = [t for t in all_rows if t.user_id == user_id]
        if not rows:
            console.print(f"[yellow]{target.username} has no transactions to analyze.[/yellow]")
            return

        months = sorted(
            {datetime.strptime(t.date, "%d-%m-%Y").strftime("%m-%Y") for t in rows},
            key=lambda m: datetime.strptime(m, "%m-%Y"),
        )
        console.print(Panel("\n".join(f"{n}. {m}" for n, m in enumerate(months, start=1)),
                            title=f"Months available for {target.username}", style="blue"))
        choice = ask_choice("Choose a month ", len(months))
        chosen_month = months[choice - 1]
        month_rows = [t for t in rows
                    if datetime.strptime(t.date, "%d-%m-%Y").strftime("%m-%Y") == chosen_month]

        try:
            from services import report as report_tools
        except ImportError:
            console.print("[yellow]Charts need matplotlib. Run: pip install matplotlib[/yellow]")
            return

        label = f"{target.username} ({chosen_month})"
        report_tools.income_expense_line_chart(month_rows, label)
        expense_only = [t for t in month_rows if t.type == "expense"]
        report_tools.expense_pie_chart(expense_only, label)

    # ---- Password --------------------------------------------------------------------
    def change_password(self):
        # clear_screen()
        user = self.auth.current_user
        old = ask("Current password ")
        new = ask("New password ")
        confirm_new = ask("Confirm new password ")
        try:
            self.auth.change_password(user, old, new, confirm_new)
            console.print("[green]Password changed.[/green]")
        except ValueError as error:
            console.print(f"[red]Could not change password:[/red]\n{error}")

    # ---- Admin: categories -----------------------------------------------------------
    def manage_categories(self):
        while True:
            clear_screen()
            console.print(Panel("1. View\n2. Add\n3. Rename\n4. Delete\n5. Back",
                                title="Manage categories", style="blue"))
            choice = ask_choice("Choose ", 5)
            try:
                if choice == 1:
                    for type in ("income", "expense"):
                        console.print(f"[bold]{type.capitalize()}:[/bold] "
                                    + ", ".join(self.tracker.category_names(type)))
                elif choice == 2:
                    type = "income" if ask_choice("Type (1 = income, 2 = expense) ", 2) == 1 else "expense"
                    name = ask("New category name: ")
                    console.print(f"[green]Added '{self.tracker.add_category(name, type)}' ({type}).[/green]")
                elif choice == 3:
                    type = "income" if ask_choice("Type (1 = income, 2 = expense) ", 2) == 1 else "expense"
                    old = choose_category(self.tracker, type)
                    new = ask("New name ")
                    self.tracker.rename_category(old, type, new)
                    console.print("[green]Category renamed.[/green]")
                elif choice == 4:
                    type = "income" if ask_choice("Type (1 = income, 2 = expense) ", 2) == 1 else "expense"
                    name = choose_category(self.tracker, type)
                    if confirm(f"Delete category '{name}'?"):
                        self.tracker.delete_category(name, type)
                        console.print("[green]Category deleted.[/green]")
                else:
                    return
            except ValueError as error:
                console.print(f"[red]Error:[/red] {error}")

            if choice != 5:
                pause()

    # ---- Admin: users ----------------------------------------------------------------
    def manage_users(self):
        admin = self.auth.current_user
        while True:
            clear_screen()
            console.print(Panel("1. List\n2. Create\n3. Delete\n4. Reset password\n5. Back",
                                title="Manage users", style="blue"))
            choice = ask_choice("Choose ", 5)
            try:
                if choice == 1:
                    self.list_users()
                elif choice == 2:
                    self.create_user()
                elif choice == 3:
                    self.list_users()
                    user_id = ask_valid("ID of the user to delete (Enter to cancel)", parse_id, allow_blank=True)
                    if user_id is not None:
                        self.delete_user(admin, user_id)
                elif choice == 4:
                    self.list_users()
                    user_id = ask_valid("ID of the user (Enter to cancel): ", parse_id, allow_blank=True)
                    if user_id is not None:
                        new = ask("New password ")
                        again = ask("Confirm new password ")
                        user = self.auth.reset_password(admin, user_id, new, again)
                        console.print(f"[green]Password reset for {user.username}.[/green]")
                else:
                    return
            except ValueError as error:
                console.print(f"[red]Error:[/red]\n{error}")

            if choice != 5:
                pause()

    def list_users(self):
        table = Table(title="Users", border_style="grey50")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Username")
        table.add_column("Role")
        table.add_column("Created")
        for user in self.auth.users:
            role_style = "magenta" if user.role == "admin" else "white"
            table.add_row(str(user.user_id), user.username, f"[{role_style}]{user.role}[/{role_style}]", user.created_at)
        console.print(table)

    def create_user(self):
        username = ask("Username: ")
        role = "admin" if ask_choice("Role (1 = user, 2 = admin): ", 2) == 2 else "user"
        password = ask("Password ")
        again = ask("Confirm password ")
        user = self.auth.register(username, password, again, role)
        console.print(f"[green]Created {user.role} '{user.username}'.[/green]")

    def delete_user(self, admin, user_id):
        target = self.auth.find_by_id(user_id)
        if target is None:
            raise ValueError("User not found.")
        if confirm(f"Delete '{target.username}' and ALL their transactions?"):
            self.auth.delete_user(admin, user_id)
            removed = self.tracker.delete_transactions_of_user(user_id)
            console.print(f"[green]User deleted ({removed} transaction(s) removed).[/green]")


def main():
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold]Goodbye! (Your data is already saved.)[/bold]")


if __name__ == "__main__":
    main()