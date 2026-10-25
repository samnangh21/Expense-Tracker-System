"""Category class."""

import re


class Category:
    MAX_LENGTH = 15
    TYPES = ("income", "expense")

    def __init__(self, name, type):
        self.name = name
        self.type = type  # "income" or "expense"

    def __str__(self):
        return self.name

    @staticmethod
    def validate_name(text):
        """Return the cleaned name or raise ValueError."""
        name = " ".join(str(text).split())
        if not name:
            raise ValueError("Category name cannot be empty.")
        if len(name) > Category.MAX_LENGTH:
            raise ValueError(f"Category name must be at most {Category.MAX_LENGTH} characters.")
        if not re.fullmatch(r"[A-Za-z0-9 ]+", name):
            raise ValueError("Category name can only contain letters, numbers and spaces.")
        return name

    @staticmethod
    def validate_type(text):
        text = str(text).strip().lower()
        if text not in Category.TYPES:
            raise ValueError("Category type must be 'income' or 'expense'.")
        return text