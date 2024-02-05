import os
import sqlite3
import uuid

import subprocess
import secrets
import zipfile
import smile_kube_utils
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from db_space import User, Experiment, ExperimentStatus

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

db: list[User] = [User("admin", "admin@admin.net", "admin",
                       [Experiment(0, ExperimentStatus.NOT_READY.value, str(ExperimentStatus.NOT_READY.name),
                                   "app067355", [9834, 9324, 3234]),
                        Experiment(1, ExperimentStatus.NOT_READY.value, str(ExperimentStatus.NOT_READY.name),
                                   "app067355", [9834, 9324, 3234])
                        ])]


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_unique_filename(filename):
    now = datetime.datetime.now()
    return filename + now.strftime("%Y%m%d%H%M%S")


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        # Check if account exists
        acc = next((u for u in db if u.name_id == username), None)

        # Check if password is correct
        if acc and (acc.password != password):
            acc = None

        # If account exists in accounts
        if acc:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = acc.name_id
            session['email'] = acc.email

            # Redirect to home page
            return redirect(url_for('account'))

        else:
            # Account doesnt exist or username/password incorrect
            return render_template('error.html', err='Invalid username/password', back_url=url_for('login'))

    if 'loggedin' in session:
        return redirect(url_for('account'))

    # Show the login form with message (if any)
    return render_template('login.html')


@app.route('/upload_results/<int:experiment_id>', methods=['POST'])
def upload_results(experiment_id: int):
    if request.method == 'POST':
        experiment = None

        # Search for experiment in db TODO improve
        for user in db:
            for exp in user.experiments:
                if exp.experiment_id == experiment_id:
                    experiment = exp

        if experiment is None:
            jsonify({'error': 'no experiment found'}), 404

        print(request.json)
        experiment.results.append(str(request.json))

        return 'OK', 200


# @app.route('/upload_results/<int:experiment_id>', methods=['POST'])
# def upload_results(experiment_id: int):
#     if request.method == 'POST':
#         experiment = None
#
#         # Search for experiment in db TODO improve
#         for user in db:
#             for exp in user.experiments:
#                 if exp.experiment_id == experiment_id:
#                     experiment = exp
#
#         if experiment is None:
#             jsonify({'error': 'no experiment found'}), 404
#
#         # check if the post request has the file part
#         if 'file' not in request.files:
#             return jsonify({'error': 'no file found'}), 404
#
#         file = request.files['file']
#         # If the user does not select a file, the browser submits an
#         # empty file without a filename.
#         if file.filename == '':
#             return jsonify({'error': 'no selected file'}), 404
#
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             return jsonify({'error': 'uploaded successfully'}), 200
#
#         return jsonify({'error': 'unknown error occurred'}), 404
#
#     jsonify({'error': 'post route only '}), 404


@app.route('/status')
def status():
    # Check if user is logged in, otherwise redirect to login
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Find user value with matchin session name_id
    acc = next((u for u in db if u.name_id == session['name_id']), None)

    # If user not found show error value
    if not acc:
        return render_template('error.html', err='Invalid session username/password!')

    # Fets user experiments list
    exps = acc.experiments

    return render_template('status.html', name_id=acc.name_id, exps=exps)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)

    # Redirect to login page
    return redirect(url_for('index'))


@app.route('/new')
def new():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    acc = next((u for u in db if u.name_id == session['name_id']), None)

    if not acc:
        return render_template('error.html', err='Invalid session data!')

    return render_template('new.html', name_id=acc.name_id, email=acc.email)


@app.route('/')
def index():  # put application's code here
    if request.args.get('uploaded') == "true":
        flash("File uploaded successfully")
    elif request.args.get('uploaded') == "false":
        flash("File upload failed")

    return render_template("index.html")


@app.route('/account')
def account():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    acc = next((u for u in db if u.name_id == session['name_id']), None)

    if not acc:
        return render_template('error.html', err='Invalid session username/password!')

    return render_template("account.html", name_id=acc.name_id, email=acc.email, exps=str(len(acc.experiments)))


@app.route('/upload_file', methods=['POST'])
def upload_file():
    acc = next((u for u in db if u.name_id == session['name_id']), None)

    if not acc:
        return render_template('error.html', err='Invalid session username/password!')

    email = acc.email
    username = acc.name_id

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


def build_and_push_docker_image(folder_path):
    # folder_path = os.path.dirname(folder_path)  # TODO What is this?

    full_image_name = f"{app.config['REGISTRY_URI']}/{create_unique_filename('exp')}:{'latest'}"

    # Initialize docker buildx (if not already done)
    print("INIT docker buildx")
    # subprocess.run(['docker', 'buildx', 'create', '--name', 'mybuilder', '--use'], check=True)

    # Build and push the Docker image
    print("RUN docker buildx BUILD AND PUSH")
    try:
        subprocess.run([
            'docker', 'buildx', 'build',
            '--platform', 'linux/arm64,linux/amd64',
            '--tag', full_image_name,
            '.',
            '--output=type=registry,registry.insecure=true'
        ], check=True, cwd=folder_path)
    except Exception as e:
        print(f"Error occurred: {e}")


if __name__ == '__main__':
    app.run(debug=False, port=5001)
