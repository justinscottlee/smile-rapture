from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from app.services.auth import bcrypt, auth_required
from app.models import User, Experiment
from app.services.db import user_collection

# Create a Blueprint for auth-related routes
bp = Blueprint('auth', __name__)


@bp.route('/account', methods=['GET'])
@auth_required
def account(user: User):
    return render_template("account.html", user=user,
                           exps=Experiment.get_mul_by_id(user.experiment_ids))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Attempt to find the user in the database
        user = User.get_by_id(str(request.form['username']))

        # If account exists and password is correct
        if user and bcrypt.check_password_hash(user.password, str(request.form["password"])):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = user.name_id
            # session['email'] = user.email

            # Redirect to the page the user originally requested or to the account page
            next_page = session.pop('next', url_for('auth.account'))  # Use 'account' as the default
            return redirect(next_page)

        else:
            # Invalid login attempt
            flash('Error: Invalid username or password')

    # Show the login form with message (if any)
    return render_template('login.html')


@bp.route('/create_account', methods=['GET', 'POST'])
def create_account():
    # Check if user is already logged in
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if (request.method == 'POST' and 'username' in request.form
            and 'email' in request.form and 'password' in request.form):
        name_id = str(request.form['username'])
        email = str(request.form['email'])

        # Check if username exists
        if not User.get_by_id(name_id):
            # Hash the password with bcrypt
            hashed_password = str(bcrypt.generate_password_hash(str(request.form['password'])).decode('utf-8'))

            # Create user object and push to DB
            user_collection.insert_one(User(name_id=name_id, email=email,
                                            password=hashed_password).json())

            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = name_id
            # session['email'] = email

            # Redirect to the page the user originally requested or to the account page
            flash(f"Success: Account created successfully")
            return redirect(session.pop('next', url_for('auth.account')))

        else:
            # Invalid login attempt
            flash(f"Error: Account with username '{name_id}' already exists")

    # Show the creation form with message (if any)
    return render_template('create_account.html')


@bp.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('next', None)
    session.pop('name_id', None)

    # Redirect to login page
    return redirect(url_for('main.index'))
