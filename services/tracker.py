"""TrackerService: CRUD, search and balance for transactions, plus category management."""

from models import Transaction, Category
from datetime import datetime

DEFAULT_CATEGORIES = {
    "income": ["Salary", "Business", "Gift", "Other"],
    "expense": ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"],
}


class TrackerService:
    def __init__(self, storage):
        self.storage = storage
        rows = storage.load("transactions.json", [])
        self.transactions = [Transaction.from_dict(row) for row in rows]

        saved = storage.load("categories.json", [])
        first_run = not saved
        if first_run:
            self.categories = [
                Category(name, type)
                for type, names in DEFAULT_CATEGORIES.items()
                for name in names
            ]
            self._save_categories()
        else:
            self.categories = [Category(row["name"], row["type"]) for row in saved]

    # ---- saving ----------------------------------------------------------
    def _save_transactions(self):
        self.storage.save("transactions.json", [t.to_dict() for t in self.transactions])

    def _save_categories(self):
        self.storage.save("categories.json",
                          [{"name": c.name, "type": c.type} for c in self.categories])

    def _next_id(self):
        return max((t.id for t in self.transactions), default=0) + 1

    # ---- categories (Create / Read / Update / Delete) -----------------------
    def category_names(self, type):
        return [c.name for c in self.categories if c.type == type]

    def _find_category(self, name, type):
        for category in self.categories:
            if category.type == type and category.name.lower() == name.strip().lower():
                return category
        return None

    def add_category(self, name, type):
        name = Category.validate_name(name)
        type = Category.validate_type(type)
        if self._find_category(name, type) is not None:
            raise ValueError(f"That {type} category already exists.")
        self.categories.append(Category(name, type))
        self._save_categories()
        return name

    def rename_category(self, old_name, type, new_name):
        category = self._find_category(old_name, type)
        if category is None:
            raise ValueError("Category not found.")
        new_name = Category.validate_name(new_name)
        existing = self._find_category(new_name, type)
        if existing is not None and existing is not category:
            raise ValueError("A category with that name already exists.")
        old_name = category.name
        category.name = new_name
        for transaction in self.transactions:
            if transaction.category == old_name and transaction.type == type:
                transaction.category = new_name
        self._save_categories()
        self._save_transactions()

    def delete_category(self, name, type):
        category = self._find_category(name, type)
        if category is None:
            raise ValueError("Category not found.")
        if len(self.category_names(type)) == 1:
            raise ValueError(f"You cannot delete the last {type} category.")
        used = sum(1 for t in self.transactions if t.category == category.name and t.type == type)
        if used > 0:
            raise ValueError(f"'{category.name}' is used by {used} transaction(s), so it cannot be deleted.")
        self.categories.remove(category)
        self._save_categories()

    # ---- transactions: Create ----------------------------------------------
    def add_transaction(self, user, trans_type, amount, category, date_text, note=""):
        trans_type = Transaction.validate_type(trans_type)
        amount = Transaction.validate_amount(amount)
        date_text = Transaction.validate_date(date_text)
        note = Transaction.validate_note(note)
        found = self._find_category(category, trans_type)
        if found is None:
            raise ValueError("That category does not exist.")

        transaction = Transaction(
            self._next_id(), user.user_id, trans_type, amount, found.name, date_text, note
        )
        self.transactions.append(transaction)
        self._save_transactions()
        return transaction

    def get_transactions(self, user, include_all=False):
        """Own transactions. Admins may ask for everyone's with include_all=True."""
        if include_all and user.can_manage_users():
            rows = list(self.transactions)
        else:
            rows = [t for t in self.transactions if t.user_id == user.user_id]
        return sorted(rows, key=lambda t: (datetime.strptime(t.date, "%d-%m-%Y"), t.id))

    def get_own(self, user, transaction_id):
        """Find one transaction, but only if it belongs to this user."""
        for transaction in self.transactions:
            if transaction.id == transaction_id and transaction.user_id == user.user_id:
                return transaction
        # Same message whether the ID does not exist or belongs to someone else.
        raise ValueError("Transaction not found.")

    # ---- transactions: Update -----------------------------------------------
    def update_transaction(self, user, transaction_id, trans_type=None, amount=None,
                           category=None, date_text=None, note=None):
        """Change only the fields that are not None."""
        transaction = self.get_own(user, transaction_id)

        # Validate everything first, so a bad value changes nothing.
        new_type = Transaction.validate_type(trans_type) if trans_type is not None else None
        new_amount = Transaction.validate_amount(amount) if amount is not None else None
        new_date = Transaction.validate_date(date_text) if date_text is not None else None
        new_note = Transaction.validate_note(note) if note is not None else None
        new_category = None
        if category is not None:
            check_type = new_type if new_type is not None else transaction.type
            found = self._find_category(category, check_type)
            if found is None:
                raise ValueError("That category does not exist.")
            new_category = found.name

        if new_type is not None:
            transaction.type = new_type
        if new_amount is not None:
            transaction.amount = new_amount
        if new_category is not None:
            transaction.category = new_category
        if new_date is not None:
            transaction.date = new_date
        if new_note is not None:
            transaction.note = new_note
        self._save_transactions()
        return transaction

    # ---- transactions: Delete -----------------------------------------------
    def delete_transaction(self, user, transaction_id):
        transaction = self.get_own(user, transaction_id)
        self.transactions.remove(transaction)
        self._save_transactions()

    def delete_transactions_of_user(self, user_id):
        """Used when an admin deletes a user. Returns how many were removed."""
        before = len(self.transactions)
        self.transactions = [t for t in self.transactions if t.user_id != user_id]
        self._save_transactions()
        return before - len(self.transactions)

    # ---- search and balance -------------------------------------------------
    def search(self, user, keyword, include_all=False):
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("Please type a keyword.")
        return [t for t in self.get_transactions(user, include_all) if t.matches(keyword)]

    def get_balance(self, user):
        """Return (total income, total expense, balance) for this user."""
        rows = self.get_transactions(user)
        income = sum(t.amount for t in rows if t.type == "income")
        expense = sum(t.amount for t in rows if t.type == "expense")
        return round(income, 2), round(expense, 2), round(income - expense, 2)