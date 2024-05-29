from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_socketio import emit, join_room, leave_room

from app.utils.kube import deploy_experiment
from app.services.experiments import admin_experiment_queue
from app.services.node import get_latest_nodes, kube_nodes
from app.services.db import config_collection
from app.models import User, Experiment, NodeType, KubernetesNode, Node
from app.routes.api import bp as api

from app import socketio


@api.route('/exp/deploy/', methods=['POST'])
def exp_deploy():
    experiment_uuid = str(request.json['uuid'])
    experiment = Experiment.get_by_id(experiment_uuid)

    if experiment is None:
        return jsonify({"status": "failed", "message": "Experiment not found"})

    if experiment.admin_required():
        return jsonify({"status": "failed", "message": "Admin required"})

    emit('deploy_event', {'msg': 'Deploy Event Received', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
    deploy_experiment(experiment)

    return jsonify({"status": "success"})


# Route for the request to delete an experiment
@api.route('/exp/delete/', methods=['POST'])
def exp_delete():
    experiment_uuid = str(request.json['uuid'])
    experiment = Experiment.get_by_id(experiment_uuid)

    if experiment is None:
        return jsonify({"status": "failed", "message": "Experiment not found"})

    deleted = experiment.delete()

    if deleted:
        print(f"Experiment '{experiment_uuid}' deleted")
        return jsonify({"status": "success"})

    return jsonify({"status": "failed"})


@api.route('/exp/file_upload/', methods=['POST'])
def exp_file_upload():
    experiment_uuid = str(request.json['uuid'])
    experiment = Experiment.get_by_id(experiment_uuid)

    if experiment is None:
        return jsonify({"status": "failed", "message": "Experiment not found"})

    file = request.files['file']
    if file is None or file.filename == '':
        return jsonify({"status": "failed", "message": "No file selected"})

    experiment.files.append(file)

    return jsonify({"status": "failed"})


@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    join_room(room)
    # Fetch previous messages or events
    messages = fetch_messages_for_room(room)  # Implement this function based on your application's needs

    for message in messages:
        emit('deploy_event', message, room=request.sid)  # Emit only to the user who just joined


def fetch_messages_for_room(room):
    # Dummy implementation, replace with actual data fetching logic
    return [
        {'msg': 'Previous message 1', 'color': 'green'},
        {'msg': 'Previous message 2', 'color': 'red'}
    ]
