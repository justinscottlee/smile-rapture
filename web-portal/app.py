import os
from functools import wraps
import subprocess
import zipfile
import smile_kube_utils
import time
from uuid import UUID, uuid4
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from models import User, Experiment, ResultEntry
from app.web_utils import create_unique_filename

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

id_0, id_1 = uuid4().hex, uuid4().hex

config_db: dict = {"valid_images": ["python:latest", "python:3.10-bullseye", "python:3.12-bookworm", "python:3.11-bookworm"],
                   "node_types": ["drone-arm64", "node-arm64", "node-amd64"]}
user_db: list[User] = [User("admin", "admin@admin.net", "admin", [id_0, id_1], admin=True)]
experiment_db: dict[UUID.hex, Experiment] = {id_0: Experiment(), id_1: Experiment()}


def get_user_experiments(user: User) -> list[tuple[UUID.hex, Experiment or None]]:
    exp_list = []

    for exp_id in user.experiment_ids:
        exp_list.append((exp_id, experiment_db[exp_id]))

    return exp_list


@app.context_processor
def utility_processor():
    def ts_formatted(ts):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))

    return dict(ts_formatted=ts_formatted)


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Redirect if session not logged in
        if 'loggedin' not in session:
            return redirect(url_for('login'))

        # Find user account object
        user = next((u for u in user_db if u.name_id == session['name_id']), None)

        # If account object is not found, show error page.
        if not user:
            return render_template('error.html', err='Invalid session name_id!')

        return f(user, *args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        # Check if account exists
        acc = next((u for u in user_db if u.name_id == username), None)

        # Check if password is correct
        if acc and (acc.password != password):
            acc = None

        # If account exists and password is correct in accounts
        if acc:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = acc.name_id
            session['email'] = acc.email

            # Redirect to home page
            return redirect(url_for('account'))

        else:
            # Account doesnt exist or username/password incorrect
            flash('Invalid username/password')
            return render_template('login.html')

    if 'loggedin' in session:
        return redirect(url_for('account'))

    # Show the login form with message (if any)
    return render_template('login.html')


@app.route('/api/upload/<experiment_id>', methods=['POST'])
def api_upload(experiment_id: str):
    experiment = experiment_db[experiment_id]

    if experiment is None:
        return 'FAILED', 404

    experiment.results.append(ResultEntry(str(request.json)))
    print(request.json)

    return 'OK', 200


@app.route('/status')
@auth_required
def status(user: User):
    return render_template('status.html', user=user, exps=get_user_experiments(user))


@app.route('/admin')
@auth_required
def admin(user: User):
    if not user.admin:
        flash('Error: Account does not have admin permissions')
        return redirect(url_for('account'))

    return render_template('admin.html', user=user, experiments=experiment_db, users=user_db)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)

    # Redirect to login page
    return redirect(url_for('index'))


@app.route('/new')
@auth_required
def new(user: User):
    return render_template('new.html', user=user, node_types=config_db["node_types"], valid_images=config_db["valid_images"])


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/account', methods=['GET'])
@auth_required
def account(user: User):
    return render_template("account.html", user=user, exps=get_user_experiments(user))


@app.route('/upload_file', methods=['POST'])
@auth_required
def upload_file(user: User):
    email = user.email
    username = user.name_id

    python_versions = request.form.getlist('container-image[]')
    code_files_list = request.files.getlist('code-files[]')
    req_file_list = request.files.getlist('req-files[]')
    ports_list = request.form.getlist('ports-open[]')

    print(python_versions)
    print(code_files_list)
    print(req_file_list)

    kube_apps = []

    for i, req_file in enumerate(req_file_list):
        app_directory = os.path.join(app.config['UPLOAD_FOLDER'], f"app{i}")

        if not os.path.exists(app_directory):
            os.mkdir(app_directory)

        src_directory = os.path.join(app_directory, "src/")
        if not os.path.exists(src_directory):
            os.mkdir(src_directory)

        req_file_path = os.path.join(app_directory, "requirements.txt")
        req_file.save(req_file_path)

        src_archive_path = os.path.join(src_directory, "src.zip")
        code_files_list[i].save(src_archive_path)
        with zipfile.ZipFile(src_archive_path, 'r') as zip_ref:
            zip_ref.extractall(src_directory)
        os.remove(src_archive_path)

        ports_list[i].replace(" ", "")
        split_ports = ports_list[i].split(',')
        kube_ports = []
        for port in split_ports:
            kube_ports.append(smile_kube_utils.Port(int(port), int(port) + 26000))

        kube_apps.append(smile_kube_utils.Application(
            src_dir=src_directory,
            requirements=req_file_path,
            registry_tag=f"app{i}",
            ports=kube_ports
        ))

    smile_kube_utils.generate_images(kube_apps)
    smile_kube_utils.create_yaml(username, kube_apps)

    os.system("sudo k3s kubectl create -f generated.yaml")

    return redirect(url_for('index', uploaded="true"))


if __name__ == '__main__':
    app.run(debug=False, port=5001)
