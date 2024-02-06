import os
from functools import wraps
import subprocess
import zipfile
import smile_kube_utils
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import User, Experiment, ResultEntry
from app.web_utils import create_unique_filename

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

db: list[User] = [User("admin", "admin@admin.net", "admin", [Experiment(0), Experiment(1)])]


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
        user = next((u for u in db if u.name_id == session['name_id']), None)

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
        acc = next((u for u in db if u.name_id == username), None)

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


@app.route('/upload_results/<int:experiment_id>', methods=['POST'])
def upload_results(experiment_id: int):
    experiment = None

    # TODO improve
    # Search for experiment in db
    for user in db:
        for exp in user.experiments:
            if exp.experiment_id == experiment_id:
                experiment = exp

    if experiment is None:
        return 'No Experiment Found', 404

    experiment.results.append(ResultEntry(str(request.json)))

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
@auth_required
def status(user: User):
    return render_template('status.html', user=user)


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
    return render_template('new.html', user=user)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/account', methods=['GET'])
@auth_required
def account(user: User):
    return render_template("account.html", user=user)


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
