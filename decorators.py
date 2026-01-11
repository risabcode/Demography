from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, login_required

def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if getattr(current_user, 'role', None) != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for("user_dashboard"))
        return func(*args, **kwargs)
    return wrapper
