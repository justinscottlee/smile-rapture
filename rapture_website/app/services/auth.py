from functools import wraps

from flask import session, redirect, url_for, flash, request
from flask_bcrypt import Bcrypt

from app.services.db import user_collection
from app.models import User

bcrypt = Bcrypt()


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Redirect if session not logged in
        if 'loggedin' not in session or 'name_id' not in session:
            # Store the original target URL where the user wanted to go
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        # Find user account object
        user = User.get_by_id(session['name_id'])

        # If account object is not found, show error page.
        if not user:
            # Invalid login attempt
            session.clear()
            flash(f"Error: Invalid session state, please login again")

            # return render_template('error.html', err='Invalid session name_id!')
            return redirect(url_for('auth.login'))

        return f(user, *args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Redirect if session not logged in
        if 'loggedin' not in session or 'name_id' not in session:
            # Store the original target URL where the user wanted to go
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        # Find user account object
        user = User.get_by_id(session['name_id'])

        # If account object is not found, show error page.
        if not user:
            # Invalid login attempt
            session.clear()
            flash(f"Error: Invalid session state, please try again")

            # return render_template('error.html', err='Invalid session name_id!')
            return redirect(url_for('auth.login'))

        if not user.admin:
            # Invalid login attempt
            flash(f"Error: Invalid permissions for this route")

            # return render_template('error.html', err='Invalid session name_id!')
            return redirect(url_for('main.index'))

        return f(user, *args, **kwargs)

    return decorated_function


def check_and_create_admin():
    # create admin user if admin does not exist
    admin_user = user_collection.find_one({"name_id": "admin"})

    if not admin_user:
        # Hash the password with bcrypt
        a_pass = str(bcrypt.generate_password_hash('admin').decode('utf-8'))

        # Create user object and push to DB
        user_collection.insert_one(User(name_id="admin", email="admin@admin.com", password=a_pass, admin=True).json())

        del a_pass
    else:
        # If admin user exists but the 'admin' flag is not True, update it
        if not admin_user.get('admin'):
            user_collection.update_one(
                {"name_id": "admin"},
                {"$set": {"admin": True}}
            )
