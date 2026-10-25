"""AuthService: register, login, logout, password rules and user management."""

import re
import time

from models import User, Admin, user_from_dict

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin123"
MAX_ATTEMPTS = 3
LOCK_SECONDS = 30


class AuthService:
    def __init__(self, storage):
        self.storage = storage
        rows = storage.load("users.json", [])
        self.users = [user_from_dict(row) for row in rows]
        self.current_user = None  # nobody is logged in at the start
        self.failed_attempts = {}  # username -> number of wrong passwords
        self.locked_until = {}  # username -> time when login is allowed again
        self.default_admin_created = False
        self._ensure_default_admin()

    # ---- setup -----------------------------------------------------------
    def _ensure_default_admin(self):
        """First run: create the admin account so someone can log in."""
        if not self.users:
            admin = Admin.create(1, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
            self.users.append(admin)
            self.save()
            self.default_admin_created = True

    def save(self):
        self.storage.save("users.json", [user.to_dict() for user in self.users])

    # ---- finding users ---------------------------------------------------
    def find_by_username(self, username):
        wanted = username.strip().lower()
        for user in self.users:
            if user.username.lower() == wanted:
                return user
        return None

    def find_by_id(self, user_id):
        for user in self.users:
            if user.user_id == user_id:
                return user
        return None

    def get_username(self, user_id):
        user = self.find_by_id(user_id)
        return user.username if user else "(deleted)"

    def _next_id(self):
        return max((user.user_id for user in self.users), default=0) + 1

    # ---- validation (each returns a list of problems, empty list = OK) ---
    def validate_username(self, username):
        errors = []
        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
            errors.append("Username must be 3-20 characters: letters, numbers or underscore.")
        elif self.find_by_username(username) is not None:
            errors.append("That username is already taken.")
        return errors

    @staticmethod
    def validate_password(password, username=""):
        errors = []
        if len(password) < 4:
            errors.append("Password must have at least 4 characters.")
        if username and password.lower() == username.lower():
            errors.append("Password must not be the same as the username.")
        return errors

    @staticmethod
    def _raise_if_errors(errors):
        if errors:
            raise ValueError("\n".join("  - " + error for error in errors))

    # ---- register / login / logout ----------------------------------------
    def register(self, username, password, confirm, role="user"):
        username = username.strip()
        errors = self.validate_username(username)
        errors += self.validate_password(password, username)
        if password != confirm:
            errors.append("Passwords do not match.")
        self._raise_if_errors(errors)

        user_class = Admin if role == "admin" else User
        user = user_class.create(self._next_id(), username, password)
        self.users.append(user)
        self.save()
        return user

    def login(self, username, password):
        key = username.strip().lower()
        now = time.time()

        if self.locked_until.get(key, 0) > now:
            seconds = int(self.locked_until[key] - now) + 1
            raise ValueError(f"Too many failed attempts. Try again in {seconds} seconds.")

        user = self.find_by_username(username)
        if user is not None and user.check_password(password):
            self.failed_attempts.pop(key, None)
            self.locked_until.pop(key, None)
            self.current_user = user
            return user

        # Wrong username or password: the message never says which one was wrong.
        count = self.failed_attempts.get(key, 0) + 1
        if count >= MAX_ATTEMPTS:
            self.failed_attempts.pop(key, None)
            self.locked_until[key] = now + LOCK_SECONDS
            raise ValueError(f"Too many failed attempts. Login is locked for {LOCK_SECONDS} seconds.")
        self.failed_attempts[key] = count
        raise ValueError("Invalid username or password.")

    def logout(self):
        self.current_user = None

    def uses_default_password(self, user):
        return user.check_password(DEFAULT_ADMIN_PASSWORD)

    # ---- password changes --------------------------------------------------
    def change_password(self, user, old_password, new_password, confirm):
        if not user.check_password(old_password):
            raise ValueError("Current password is incorrect.")
        errors = self.validate_password(new_password, user.username)
        if new_password == old_password:
            errors.append("New password must be different from the current one.")
        if new_password != confirm:
            errors.append("Passwords do not match.")
        self._raise_if_errors(errors)
        user.set_password(new_password)
        self.save()

    # ---- admin-only actions ------------------------------------------------
    def _require_admin(self, admin):
        if not admin.can_manage_users():
            raise ValueError("Only an admin can do this.")

    def reset_password(self, admin, user_id, new_password, confirm):
        self._require_admin(admin)
        target = self.find_by_id(user_id)
        if target is None:
            raise ValueError("User not found.")
        errors = self.validate_password(new_password, target.username)
        if new_password != confirm:
            errors.append("Passwords do not match.")
        self._raise_if_errors(errors)
        target.set_password(new_password)
        self.save()
        return target

    def delete_user(self, admin, user_id):
        self._require_admin(admin)
        target = self.find_by_id(user_id)
        if target is None:
            raise ValueError("User not found.")
        if target.user_id == admin.user_id:
            raise ValueError("You cannot delete your own account.")
        self.users.remove(target)
        self.save()
        return target