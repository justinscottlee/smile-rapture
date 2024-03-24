from flask import render_template, flash, Blueprint
from flask_socketio import emit

from app.services.node import get_latest_nodes, kube_nodes
from app.models import User, Experiment, NodeType
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
