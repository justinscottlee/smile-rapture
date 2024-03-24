from flask import render_template, flash, Blueprint
from flask_socketio import emit

from app.utils.kube import deploy_experiment
from app.services.experiments import admin_experiment_queue
from app.services.node import get_latest_nodes, kube_nodes
from app.services.db import config_collection
from app.models import User, Experiment, NodeType, KubernetesNode, Node
from app.routes.api import bp as api

from app import socketio


@socketio.on('update_node_type')
def update_node_type(json):
    try:
        kube_nodes[int(json['index'])].type = NodeType[str(json['value']).upper()]
        emit('update_node_type_status_' + str(json['index']), {'success': True})
    except Exception as E:
        print(f"Failed to update node type: {E}")
        emit('update_node_type_status_' + str(json['index']), {'success': False})

    # Update the kube nodes list in the database, by overwriting the existing kube nodes entry
    config_collection.update_one({"_id": "kube_nodes"},
                                 {"$set": {"nodes": [kube_node.json() for kube_node in kube_nodes]}}, upsert=True)


@socketio.on('start_exp_press')
def start_exp_press(json):
    experiment = Experiment.get_by_id(str(json['id']))
    node_assignment = json['node_assignment']  # Node assignment is a list of hostname strings
    print("Node assignment: ", node_assignment)

    # Assign the kubernetes node to the experiment node
    for i, node_hostname in enumerate(node_assignment):
        for kube_node in kube_nodes:
            if kube_node.hostname == node_hostname:
                experiment.nodes[i].kubernetes_node = kube_node
                print(f"Assigned kube node {kube_node.hostname} to node {experiment.nodes[i].nickname}")
                break

    print("Starting experiment: ", experiment.experiment_uuid)
    deploy_experiment(experiment)
    print("Deployed experiment: ", experiment.experiment_uuid)

    # Remove the experiment from the queue by matching the id
    for i, exp in enumerate(admin_experiment_queue):
        if exp.experiment_uuid == experiment.experiment_uuid:
            admin_experiment_queue.pop(i)
            # Remove the experiment id from the config collection as well
            config_collection.update_one({"_id": "admin_experiment_queue"},
                                         {"$set": {"queue": [exp.experiment_uuid for exp in admin_experiment_queue]}},
                                         upsert=True)

            print("Removed experiment from queue: ", experiment.experiment_uuid)
            break

    emit('exp_status_update', {'id': experiment.experiment_uuid, 'status': experiment.status.name})
    print("Emitted experiment status update: ", experiment.experiment_uuid)


@socketio.on('exp_status_request')
def exp_status_request(json):
    experiment = Experiment.get_by_id(str(json['id']))
    experiment.update()
    emit('exp_status_update', {'id': experiment.experiment_uuid, 'status': experiment.status.name})
    print("Emitted experiment status update: ", experiment.experiment_uuid)
