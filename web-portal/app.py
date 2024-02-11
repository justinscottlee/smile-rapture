import os
from functools import wraps
import subprocess
import zipfile
import smile_kube_utils
import time
from uuid import UUID, uuid4
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from models import User, Experiment, ResultEntry, Node, Container, ContainerStatus

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

id_0, id_1 = uuid4().hex, uuid4().hex

config_db: dict = {
    "valid_images": ["python:latest", "python:3.10-bullseye", "python:3.12-bookworm", "python:3.11-bookworm"],
    "node_types": ["drone-arm64", "node-arm64", "node-amd64"]}
user_db: list[User] = [User("admin", "admin@admin.net", "admin", [id_0, id_1], admin=True)]
experiment_db: dict[UUID.hex, Experiment] = {id_0: Experiment(experiment_uuid=id_0, created_by="admin"),
                                             id_1: Experiment(experiment_uuid=id_1, created_by="admin")}


def get_user_experiments(user: User) -> list[Experiment]:
    exp_list = []

    for exp_id in user.experiment_ids:
        exp_list.append(experiment_db[exp_id])

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
    return render_template('new.html', user=user, node_types=config_db["node_types"],
                           valid_images=config_db["valid_images"])


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
    print(request.form)

    node_count = int(request.form.get('nodeCount'))

    if node_count <= 0:
        flash('Error: No nodes specified')
        return redirect(url_for('new'))

    exp = Experiment(experiment_uuid=str(uuid4()), created_by=user.name_id, created_at=time.time())
    experiment_base_path = os.path.join(app.config['UPLOAD_FOLDER'], exp.experiment_uuid + "/")

    if not os.path.exists(experiment_base_path):
        os.makedirs(experiment_base_path)
    else:
        flash(f'Error: Experiment UUID dir already exists')
        return redirect(url_for('new'))

    for node_id in range(1, node_count + 1):
        container_count = int(request.form.get(f'containerCountNode{node_id}'))
        node_type = str(request.form.get(f'node-type-{node_id}'))

        if container_count <= 0:
            flash(f'Error: Container count wrongly specified in node{node_id}')
            return redirect(url_for('new'))

        exp.nodes.append(Node(node_type))

        for container_id in range(1, container_count + 1):
            name = str(request.form.getlist(f'container-name-{node_id}')[container_id - 1]).strip()
            container_image = str(request.form.getlist(f'container-image-{node_id}')[container_id - 1]).strip()
            ports_open = str(request.form.getlist(f'ports-open-{node_id}')[container_id - 1]).strip().replace(" ", "")

            source_zip_file = request.files.getlist(f'code-files-{node_id}')[container_id - 1]
            req_file = request.files.getlist(f'req-files-{node_id}')[container_id - 1]

            if container_image is None or ports_open is None or source_zip_file is None or req_file is None:
                flash(
                    f'Error: Form upload failed. Types - container_image: {type(container_image)}, ports_open: {type(ports_open)}, source_zip_file: {type(source_zip_file)}, req_file: {type(req_file)}')
                return redirect(url_for('new'))

            reg_tag = str(uuid4())
            container_base_path = os.path.join(experiment_base_path, reg_tag + "/")
            src_path = os.path.join(container_base_path, "src/")
            src_zip_path = os.path.join(src_path, "src.zip")
            req_file_path = os.path.join(container_base_path, "requirements.txt")

            if not os.path.exists(container_base_path) or not os.path.exists(src_path):
                os.makedirs(container_base_path)
                os.makedirs(src_path)
            else:
                flash(f'Error: Container UUID dir already exists')
                return redirect(url_for('new'))

            try:
                req_file.save(req_file_path)
                source_zip_file.save(src_zip_path)
                with zipfile.ZipFile(src_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(src_path)
                os.remove(src_zip_path)
            except Exception as e:
                flash(f'Error: {str(e)}')
                return redirect(url_for('new'))

            port_list = [int(port) for port in ports_open.split(',') if port]

            cont = Container(src_dir=src_path, python_requirements=req_file_path, registry_tag=reg_tag,
                             ports=port_list, status=ContainerStatus.PENDING, name=name)  # TODO add name

            exp.nodes[node_id - 1].containers.append(cont)

    # Upload experiment and associate with user
    experiment_db[exp.experiment_uuid] = exp
    user.experiment_ids.append(exp.experiment_uuid)

    flash(f'Success: Experiment uploaded successfully')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=5001)
