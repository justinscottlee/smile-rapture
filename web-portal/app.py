import os
from functools import wraps
import zipfile
import smile_kube_utils
import time
from pymongo import MongoClient
from flask_htmx import HTMX, make_response
from uuid import UUID, uuid4
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Markup
from models import User, Experiment, ResultEntry, Node, Container, ContainerStatus

# Flask
app = Flask(__name__)
htmx = HTMX(app)

# DB
client = MongoClient('localhost', 27017)
db = client.flask_db

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

config_db: dict = {
    "valid_images": ["python:latest", "python:3.10-bullseye", "python:3.12-bookworm", "python:3.11-bookworm"],
    "node_types": ["drone-arm64", "node-arm64", "node-amd64"]}
user_db: list[User] = [User("admin", "admin@admin.net", "admin", [], admin=True)]
experiment_db: dict[UUID.hex, Experiment] = {}


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
            # Store the original target URL where the user wanted to go
            session['next'] = request.url
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
    # Check if user is already logged in
    if 'loggedin' in session:
        return redirect(url_for('account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        # Attempt to find the user in the database
        acc = next((u for u in user_db if u.name_id == username), None)

        # If account exists and password is correct
        if acc and acc.password == password:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = acc.name_id
            session['email'] = acc.email

            # Redirect to the page the user originally requested or to the account page
            next_page = session.pop('next', url_for('account'))  # Use 'account' as the default
            return redirect(next_page)

        else:
            # Invalid login attempt
            flash('Error: Invalid username or password')

    # Show the login form with message (if any)
    return render_template('login.html')


@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    # Check if user is already logged in
    if 'loggedin' in session:
        return redirect(url_for('account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'email' in request.form and 'password' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if username exists
        acc = next((u for u in user_db if u.name_id == username), None)

        # If account exists and password is correct
        if not acc:
            user = User(username, email, password)
            user_db.append(user)

            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = username
            session['email'] = email

            # Redirect to the page the user originally requested or to the account page
            next_page = session.pop('next', url_for('account'))  # Use 'account' as the default
            return redirect(next_page)

        else:
            # Invalid login attempt
            msg = Markup(f'Error: Account with username <strong>{username}</strong> already exists')
            flash(msg)

    # Show the creation form with message (if any)
    return render_template('create_account.html')


@app.route('/api/upload/<experiment_id>', methods=['POST'])
def api_upload(experiment_id: UUID.hex):
    # Use get() to avoid KeyError, returning None if not found
    exp = experiment_db.get(experiment_id)

    if exp is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': 'Experiment not found'}), 404

    exp.results.append(ResultEntry(str(request.json)))

    return jsonify({'message': 'OK'}), 200


@app.route('/status')
@auth_required
def status(user: User):
    experiments = get_user_experiments(user)

    for experiment in experiments:
        smile_kube_utils.update_experiment_status(experiment)

    return render_template('status.html', user=user, experiments=experiments)


# Route to update experiment status dynamically
@app.route('/experiment/<experiment_id>/status/')
@auth_required
def get_experiment_status(user: User, experiment_id: UUID.hex):
    experiment = experiment_db.get(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': 'Experiment not found'}), 404

    smile_kube_utils.update_experiment_status(experiment)

    # Render only the status part of the experiment
    fragment = render_template('partial/experiment_status_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


# Route to update experiment results dynamically
@app.route('/experiment/<experiment_id>/results/')
@auth_required
def get_experiment_results(user: User, experiment_id: UUID.hex):
    experiment = experiment_db.get(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': 'Experiment not found'}), 404

    smile_kube_utils.update_experiment_status(experiment)

    # Render only the results part of the experiment
    fragment = render_template('partial/experiment_results_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


@app.route('/admin')
@auth_required
def admin(user: User):
    if not user.admin:
        flash('Error: Account does not have admin permissions')
        return redirect(url_for('account'))

    return render_template('admin.html', user=user, experiments=experiment_db, users=user_db)


@app.route('/experiment/<experiment_id>')
# @auth_required
def show_experiment(experiment_id: str):
    # TODO Verify user owns the experiment or is admin
    # if not user.admin:
    #     flash('Error: Account does not have admin permissions')
    #     return redirect(url_for('account'))

    exp = experiment_db.get(experiment_id)

    if exp is None:
        flash('Error: Experiment not found')
        return redirect(url_for('index'))

    smile_kube_utils.update_experiment_status(exp)

    return render_template('experiment.html', experiment=exp)


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
    smile_kube_utils.deploy_experiment(exp)

    flash(f'Success: Experiment uploaded successfully')
    return redirect(url_for('show_experiment', experiment_id=exp.experiment_uuid))


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=5001)
