"""Transaction class: one income or expense record."""

import math
from datetime import datetime

TYPES = ("income", "expense")
MAX_NOTE_LENGTH = 50


class Transaction:
    def __init__(self, id, user_id, type, amount, category, date, note=""):
        self.id = id
        self.user_id = user_id  # the owner of this transaction
        self.type = type  # "income" or "expense"
        self.amount = amount
        self.category = category
        self.date = date  # text in the format YYYY-MM-DD
        self.note = note

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["user_id"],
            data["type"],
            data["amount"],
            data["category"],
            data["date"],
            data.get("note", ""),
        )

    def matches(self, keyword):
        """True if the keyword appears in the note, category or type (ignores case)."""
        keyword = keyword.lower()
        return (
            keyword in self.note.lower()
            or keyword in self.category.lower()
            or keyword in self.type.lower()
        )

    # ---- validation: each one returns the clean value or raises ValueError ----
    @staticmethod
    def validate_type(text):
        text = str(text).strip().lower()
        if text not in TYPES:
            raise ValueError("Type must be 'income' or 'expense'.")
        return text

    @staticmethod
    def validate_amount(text):
        try:
            amount = float(str(text).replace(",", "").strip())
        except ValueError:
            raise ValueError("Amount must be a number, for example 12.50.")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be greater than 0.")
        return round(amount, 2)

    @staticmethod
    def validate_date(text):
        try:
            return datetime.strptime(str(text).strip(), "%d-%m-%Y").date().strftime("%d-%m-%Y")
        except ValueError:
            raise ValueError("Date must be a real date in the format DD-MM-YYYY.")

    @staticmethod
    def validate_note(text):
        text = str(text).strip()
        if len(text) > MAX_NOTE_LENGTH:
            raise ValueError(f"Note must be at most {MAX_NOTE_LENGTH} characters.")
        return text
    