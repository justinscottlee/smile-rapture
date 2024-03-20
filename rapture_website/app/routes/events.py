from flask import session
from flask_socketio import emit

from app import socketio
from app.services.node import kube_nodes
from app.models import NodeType


@socketio.on('update_node_type')
def update_node_type(json):
    try:
        kube_nodes[int(json['index'])].type = NodeType[str(json['value']).upper()]
    except Exception as E:
        print(f"Failed to update node type: {E}")

    # You can access json['index'] and json['value'] here to update the node.
    # After updating, emit a success message back to the client.
    emit('update_success_' + str(json['index']), {'success': True})
