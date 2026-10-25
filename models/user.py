"""User and Admin classes."""

import hashlib
import hmac
import os
from datetime import date


class User:
    """A normal user. The password hash and salt are private (encapsulation)."""

    role = "user"

    def __init__(self, user_id, username, password_hash, salt, created_at=None):
        self._user_id = user_id
        self._username = username
        self.__password_hash = password_hash  # double underscore = private
        self.__salt = salt
        self._created_at = created_at or date.today().isoformat()

    # ---- read-only properties -------------------------------------------
    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @property
    def created_at(self):
        return self._created_at

    # ---- password handling ----------------------------------------------
    @staticmethod
    def hash_password(password, salt):
        """Turn a password + salt into a hash (a one-way scrambled string)."""
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

    @classmethod
    def create(cls, user_id, username, password):
        """Create a brand-new user from a plain password (generates a random salt)."""
        salt = os.urandom(16).hex()
        return cls(user_id, username, cls.hash_password(password, salt), salt)

    def check_password(self, password):
        attempt = self.hash_password(password, self.__salt)
        return hmac.compare_digest(attempt, self.__password_hash)

    def set_password(self, new_password):
        self.__salt = os.urandom(16).hex()
        self.__password_hash = self.hash_password(new_password, self.__salt)

    # ---- role behaviour (Admin overrides these: polymorphism) -----------
    def can_manage_users(self):
        return False

    def get_menu(self):
        """List of (label, action_name). main.py turns action names into functions."""
        return [
            ("Add income", "add_income"),
            ("Add expense", "add_expense"),
            ("View transactions", "view_transactions"),
            ("Edit transaction", "edit_transaction"),
            ("Delete transaction", "delete_transaction"),
            ("Search transactions", "search"),
            ("Balance and report", "report"),
            ("View charts", "charts"),
            ("Change password", "change_password"),
            ("Logout", "logout"),
        ]

    # ---- saving ----------------------------------------------------------
    def to_dict(self):
        return {
            "user_id": self._user_id,
            "username": self._username,
            "password_hash": self.__password_hash,
            "salt": self.__salt,
            "role": self.role,
            "created_at": self._created_at,
        }


class Admin(User):
    """An admin is a User with extra menu items and extra permissions (inheritance)."""

    role = "admin"

    def can_manage_users(self):
        return True

    def get_menu(self):
            return [
                ("Change password", "change_password"),
                ("View transaction", "view_all"),
                ("Analyze users expense", "analyze_users"),
                ("Manage categories", "manage_categories"),
                ("Manage users", "manage_users"),
                ("Logout", "logout"),
            ]


def user_from_dict(data):
    """Build a User or Admin object from a saved dictionary."""
    user_class = Admin if data["role"] == "admin" else User
    return user_class(
        data["user_id"],
        data["username"],
        data["password_hash"],
        data["salt"],
        data.get("created_at"),
    )