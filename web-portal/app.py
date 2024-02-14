import os
from functools import wraps
import zipfile
import smile_kube_utils
from flask_bcrypt import Bcrypt
import time
from pymongo import MongoClient
from flask_htmx import HTMX, make_response
from uuid import UUID, uuid4
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import User, Experiment, ResultEntry, Node, Container, ContainerStatus, NodeType

# Flask
app = Flask(__name__)
htmx = HTMX(app)
bcrypt = Bcrypt(app)

# DB
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["user_db"]

config_collection = db["config"]
user_collection = db["users"]
experiment_collection = db["experiments"]

# del all users, for testing!
# user_collection.delete_many({})

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads/")
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['REGISTRY_URI'] = '130.191.161.13:5000'

config_db: dict = {
    "valid_images": ["python:latest", "python:3.10-bullseye", "python:3.12-bookworm", "python:3.11-bookworm"],
    "node_types": ["drone-arm64", "node-arm64", "node-amd64"]}


# TODO this may be redundant, email is not unique
def get_user_by_email(email: str) -> User or None:
    user_data = user_collection.find_one({"email": email})
    if user_data:
        # Convert the MongoDB document to the User dataclass instance
        return User.from_json(user_data)
    return None


def get_user_by_id(name_id: str) -> User or None:
    user_data = user_collection.find_one({"name_id": name_id})
    if user_data:
        # Convert the MongoDB document to the User dataclass instance
        return User.from_json(user_data)
    return None


def get_experiment_by_id(experiment_id: UUID.hex) -> Experiment or None:
    exp_data = user_collection.find_one({"_id": experiment_id})

    if exp_data:
        # Convert the MongoDB document to the User dataclass instance
        return Experiment.from_json(exp_data)

    return None


def get_experiments(exp_ids: list[UUID.hex]) -> list[Experiment]:
    exp_list = []

    # Fetch experiments from MongoDB
    cursor = experiment_collection.find({"_id": {"$in": exp_ids}})

    # Convert each document into an Experiment instance
    for doc in cursor:
        exp_list.append(Experiment.from_json(doc))

    return exp_list


def get_all_users() -> list[User]:
    user_list = []

    cursor = user_collection.find({})
    for doc in cursor:
        user_list.append(User.from_json(doc))

    return user_list


def get_all_experiments() -> list[Experiment]:
    exp_list = []

    cursor = experiment_collection.find({})
    for doc in cursor:
        exp_list.append(Experiment.from_json(doc))

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
        if 'loggedin' not in session or 'name_id' not in session:
            # Store the original target URL where the user wanted to go
            session['next'] = request.url
            return redirect(url_for('login'))

        # Find user account object
        user = get_user_by_id(session['name_id'])

        # If account object is not found, show error page.
        if not user:
            # Invalid login attempt
            session.clear()
            flash(f"Error: Invalid session state, please login again")

            # return render_template('error.html', err='Invalid session name_id!')
            return redirect(url_for('login'))

        return f(user, *args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Attempt to find the user in the database
        user = get_user_by_id(str(request.form['username']))

        # If account exists and password is correct
        if user and bcrypt.check_password_hash(user.password, str(request.form["password"])):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = user.name_id
            # session['email'] = user.email

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
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if (request.method == 'POST' and 'username' in request.form
            and 'email' in request.form and 'password' in request.form):
        name_id = str(request.form['username'])
        email = str(request.form['email'])

        # Check if username exists
        if not get_user_by_id(name_id):
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
            return redirect(session.pop('next', url_for('account')))

        else:
            # Invalid login attempt
            flash(f"Error: Account with username '{name_id}' already exists")

    # Show the creation form with message (if any)
    return render_template('create_account.html')


@app.route('/api/upload/<experiment_id>', methods=['POST'])
def api_upload(experiment_id: UUID.hex):
    # TODO add auth so randoms cant upload results
    experiment = get_experiment_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    # Associate experiment with user
    experiment_collection.update_one({'_id': experiment_id},
                                     {'$push': {"results": ResultEntry(str(request.json)).json()}})

    return jsonify({'message': 'OK'}), 200


@app.route('/status')
@auth_required
def status(user: User):
    experiments = get_experiments(user.experiment_ids)

    for experiment in experiments:
        smile_kube_utils.update_experiment_status(experiment)
        experiment_collection.update_one({'_id': experiment.experiment_uuid},
                                         {'$set': {"status": experiment.status.value}})

    return render_template('status.html', user=user, experiments=experiments)


# Route to update experiment status dynamically
@app.route('/experiment/<experiment_id>/status/')
@auth_required
def get_experiment_status(user: User, experiment_id: UUID.hex):
    experiment = get_experiment_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    if experiment.created_by != user.name_id or not user.admin:
        return jsonify({'error': f"Invalid permissions for experiment '{experiment_id}'"}), 403

    smile_kube_utils.update_experiment_status(experiment)
    experiment_collection.update_one({'_id': experiment_id}, {'$set': {"status": experiment.status.value}})

    # Render only the status part of the experiment
    fragment = render_template('partial/experiment_status_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


# Route to update experiment results dynamically
@app.route('/experiment/<experiment_id>/results/')
@auth_required
def get_experiment_results(user: User, experiment_id: UUID.hex):
    experiment = get_experiment_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    if experiment.created_by != user.name_id or not user.admin:
        return jsonify({'error': f"Invalid permissions for experiment '{experiment_id}'"}), 403

    smile_kube_utils.update_experiment_status(experiment)
    experiment_collection.update_one({'_id': experiment_id}, {'$set': {"status": experiment.status.value}})

    # Render only the results part of the experiment
    fragment = render_template('partial/experiment_results_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


@app.route('/admin')
@auth_required
def admin(user: User):
    if not user.admin:
        flash('Error: Invalid permissions for this route')
        return redirect(url_for('index'))

    return render_template('admin.html', user=user,
                           experiments=get_all_experiments(), users=get_all_users())


@app.route('/experiment/<experiment_id>')
@auth_required
def show_experiment(user: User, experiment_id: str):
    experiment = get_experiment_by_id(experiment_id)

    if experiment is None:
        flash(f"Error: Experiment '{experiment_id}' not found")
        return redirect(url_for('index'))

    if experiment.created_by != user.name_id or not user.admin:
        flash(f"Error: Invalid permissions for experiment '{experiment_id}'")
        return redirect(url_for('index'))

    smile_kube_utils.update_experiment_status(experiment)
    experiment_collection.update_one({'_id': experiment_id}, {'$set': {"status": experiment.status.value}})

    return render_template('experiment.html', experiment=experiment)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('next', None)
    session.pop('name_id', None)

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
    return render_template("account.html", user=user, exps=get_experiments(user.experiment_ids))


@app.route('/upload_file', methods=['POST'])
@auth_required
def upload_file(user: User):
    node_count = int(request.form.get('nodeCount'))
    experiment_name = str(request.form.get('experiment-name'))

    if node_count <= 0:
        flash('Error: No nodes specified')
        return redirect(url_for('new'))

    if experiment_name is None:
        flash('Error: No experiment name specified')
        return redirect(url_for('new'))

    experiment = Experiment(experiment_uuid=str(uuid4()), created_by=user.name_id, created_at=time.time(),
                            name=experiment_name)
    experiment_base_path = str(os.path.join(app.config['UPLOAD_FOLDER'], experiment.experiment_uuid + "/"))

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

        curr_node = Node(NodeType(node_type))

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

            cont = Container(src_dir=str(src_path), python_requirements=req_file_path, registry_tag=reg_tag,
                             ports=port_list, status=ContainerStatus.PENDING, name=name)  # TODO add name

            curr_node.containers.append(cont)

        experiment.nodes.append(curr_node)  # TODO verify this isnt broken

    # Upload experiment
    experiment_collection.insert_one(experiment.json())

    # Associate experiment with user
    user_collection.update_one({'name_id': user.name_id},
                               {'$push': {"experiment_ids": experiment.experiment_uuid}})

    # deploy exp
    smile_kube_utils.deploy_experiment(experiment)

    flash(f'Success: Experiment uploaded successfully')
    return redirect(url_for('show_experiment', experiment_id=experiment.experiment_uuid))


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=5001)
