import os
import time
import zipfile
from uuid import UUID, uuid4

from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_htmx import make_response

from app.models import User, Experiment, ResultEntry, Node, NodeType, Container, ContainerStatus
from app.services.auth import auth_required, admin_required
from app.services.db import experiment_collection, user_collection
from app.utils.kube import get_nodes, deploy_experiment

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template("index.html")


@bp.route('/api/upload/<experiment_id>', methods=['POST'])
def api_upload(experiment_id: UUID.hex):
    experiment = Experiment.get_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    # Associate experiment with user
    experiment_collection.update_one({'_id': experiment_id},
                                     {'$push': {"results": ResultEntry(str(request.json)).json()}})

    return jsonify({'message': 'OK'}), 200


@bp.route('/api/upload/<experiment_id>/<reg_tag>/stdout', methods=['POST'])
def stdout_upload(experiment_id: UUID.hex, reg_tag: UUID.hex):
    # Define the query to find the specific experiment and container
    query = {
        "_id": experiment_id,
        "nodes.containers.registry_tag": reg_tag
    }

    # Define the update to append the log message to the stdout_log
    update = {
        "$push": {
            "nodes.$[].containers.$[container].stdout_log": str(request.json['stdout'])
        }
    }
    # Execute the update operation
    result = experiment_collection.update_one(query, update, array_filters=[{"container.registry_tag": reg_tag}])

    # Check if the document was found and updated
    if result.modified_count == 0:
        return jsonify({'error': 'Experiment or container not updated'}), 404

    return jsonify({'message': 'OK'}), 200


@bp.route('/status')
@auth_required
def status(user: User):
    experiments = Experiment.get_mul_by_id(user.experiment_ids)

    for experiment in experiments:
        try:
            experiment.update()
        except Exception as E:
            return jsonify({'error': f"Experiment '{experiment.experiment_uuid}' update failed: {str(E)}"}), 404

    return render_template('status.html', user=user, experiments=experiments)


# Route to update experiment status dynamically
@bp.route('/experiment/<experiment_id>/status/')
@auth_required
def get_experiment_status(user: User, experiment_id: UUID.hex):
    experiment = Experiment.get_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    if experiment.created_by != user.name_id and not user.admin:
        return jsonify({'error': f"Invalid permissions for experiment '{experiment_id}'"}), 403

    try:
        experiment.update()
    except Exception as E:
        return jsonify({'error': f"Experiment '{experiment_id}' update failed: {str(E)}"}), 404

    # Render only the status part of the experiment
    fragment = render_template('partial/experiment_status_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


# Route to update experiment results dynamically
@bp.route('/experiment/<experiment_id>/results/')
@auth_required
def get_experiment_results(user: User, experiment_id: UUID.hex):
    experiment = Experiment.get_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    if experiment.created_by != user.name_id and not user.admin:
        return jsonify({'error': f"Invalid permissions for experiment '{experiment_id}'"}), 403

    try:
        experiment.update()
    except Exception as E:
        return jsonify({'error': f"Experiment '{experiment_id}' update failed"}), 404

    # Render only the results part of the experiment
    fragment = render_template('partial/experiment_results_fragment.html', experiment=experiment)
    return make_response(fragment, push_url=False)


@bp.route('/experiment/<experiment_id>/<reg_tag>/stdout/')
@auth_required
def get_container_stdout(user: User, experiment_id: UUID.hex, reg_tag: UUID.hex):
    experiment = Experiment.get_by_id(experiment_id)

    if experiment is None:
        # If the experiment_id is not found, return a 404 error
        return jsonify({'error': f"Experiment '{experiment_id}' not found"}), 404

    if experiment.created_by != user.name_id and not user.admin:
        return jsonify({'error': f"Invalid permissions for experiment '{experiment_id}'"}), 403

    container = None

    for n in experiment.nodes:
        for c in n.containers:
            if reg_tag == c.registry_tag:
                container = c

    if container is None:
        return jsonify({'error': f"Container '{reg_tag}' not found"}), 404

    try:
        experiment.update()
    except Exception as E:
        return jsonify({'error': f"Experiment '{experiment_id}' update failed"}), 404

    container = None
    for n in experiment.nodes:
        for c in n.containers:
            if reg_tag == c.registry_tag:
                container = c

    if container is None:
        return jsonify({'error': f"Container '{reg_tag}' not found"}), 404

    # Render only the results part of the experiment
    fragment = render_template('partial/container_stdout_fragment.html', container=container)
    return make_response(fragment, push_url=False)


# @socketio.on('message')
# def handle_button_press(data):
#     print('received message: ' + data)
#     # You can also emit a response back to the client
#     socketio.emit('start_response', {'message': 'Starting experiment...'})


@bp.route('/experiment/<experiment_id>')
@auth_required
def show_experiment(user: User, experiment_id: str):
    experiment = Experiment.get_by_id(experiment_id)

    if experiment is None:
        flash(f"Error: Experiment '{experiment_id}' not found")
        return redirect(url_for('main.index'))

    if experiment.created_by != user.name_id and not user.admin:
        flash(f"Error: Invalid permissions for experiment '{experiment_id}'")
        return redirect(url_for('main.index'))

    try:
        experiment.update()
    except Exception as E:
        flash(f"Error: Experiment update failed '{experiment_id}'")
        flash(f'Error: {str(E)}')

    return render_template('experiment.html', experiment=experiment)


@bp.route('/new')
@auth_required
def new(user: User):
    return render_template('new.html', user=user, node_types=current_app.config["NODE_TYPES"],
                           valid_images=current_app.config["VALID_IMAGES"])


@bp.route('/upload_file', methods=['POST'])
@auth_required
def upload_file(user: User):
    node_count = int(request.form.get('nodeCount'))
    experiment_name = str(request.form.get('experiment-name'))

    if node_count <= 0:
        flash('Error: No nodes specified')
        return redirect(url_for('main.new'))

    if experiment_name is None:
        flash('Error: No experiment name specified')
        return redirect(url_for('main.new'))

    experiment = Experiment(created_by=user.name_id, created_at=time.time(), name=experiment_name)
    experiment_base_path = str(os.path.join(current_app.config['UPLOAD_FOLDER'], experiment.experiment_uuid + "/"))

    if not os.path.exists(experiment_base_path):
        os.makedirs(experiment_base_path)
    else:
        flash(f'Error: Experiment UUID dir already exists')
        return redirect(url_for('main.new'))

    for node_id in range(1, node_count + 1):
        container_count = int(request.form.get(f'containerCountNode{node_id}'))
        node_type = str(request.form.get(f'node-type-{node_id}'))

        if container_count <= 0:
            flash(f'Error: Container count wrongly specified in node{node_id}')
            return redirect(url_for('main.new'))

        try:
            curr_node = Node(NodeType[node_type])
            print(curr_node)
        except ValueError as e:
            print(e)
            flash(f'Error: Node type wrongly specified in node{node_id}')
            return redirect(url_for('main.new'))

        for container_id in range(1, container_count + 1):
            name = str(request.form.getlist(f'container-name-{node_id}')[container_id - 1]).strip()
            container_image = str(request.form.getlist(f'container-image-{node_id}')[container_id - 1]).strip()
            ports_open = str(request.form.getlist(f'ports-open-{node_id}')[container_id - 1]).strip().replace(" ", "")

            source_zip_file = request.files.getlist(f'code-files-{node_id}')[container_id - 1]
            req_file = request.files.getlist(f'req-files-{node_id}')[container_id - 1]

            if container_image is None or ports_open is None or source_zip_file is None or req_file is None:
                flash(
                    f'Error: Form upload failed. Types - container_image: {type(container_image)},'
                    f' ports_open: {type(ports_open)}, source_zip_file: {type(source_zip_file)},'
                    f' req_file: {type(req_file)}')
                return redirect(url_for('main.new'))

            reg_tag = str(uuid4().hex)
            container_base_path = os.path.join(experiment_base_path, reg_tag + "/")
            src_path = os.path.join(container_base_path, "src/")
            src_zip_path = os.path.join(src_path, "src.zip")
            req_file_path = os.path.join(container_base_path, "requirements.txt")

            if not os.path.exists(container_base_path) or not os.path.exists(src_path):
                os.makedirs(container_base_path)
                os.makedirs(src_path)
            else:
                flash(f'Error: Container UUID dir already exists')
                return redirect(url_for('main.new'))

            try:
                req_file.save(req_file_path)
                source_zip_file.save(src_zip_path)
                with zipfile.ZipFile(src_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(src_path)
                os.remove(src_zip_path)
            except Exception as e:
                flash(f'Error: {str(e)}')
                return redirect(url_for('main.new'))

            port_list = [int(port) for port in ports_open.split(',') if port]

            cont = Container(src_dir=str(src_path), python_requirements=req_file_path, registry_tag=reg_tag,
                             ports=port_list, status=ContainerStatus.PENDING, name=name)  # TODO add name

            curr_node.containers.append(cont)

        experiment.nodes.append(curr_node)  # TODO verify this isn't broken

    # deploy exp
    deploy_experiment(experiment)

    # Add experiment
    experiment_collection.insert_one(experiment.json())

    # Associate experiment with user
    user_collection.update_one({'name_id': user.name_id},
                               {'$push': {"experiment_ids": experiment.experiment_uuid}})

    flash(f'Success: Experiment uploaded successfully')
    return redirect(url_for('main.show_experiment', experiment_id=experiment.experiment_uuid))
