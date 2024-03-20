from flask import session
from flask_socketio import emit, join_room, leave_room

from app import socketio
from app.services.node import kube_nodes, latest_nodes
from app.models import NodeType


@socketio.on('update_node_type')
def update_node_type(json):
    index = json['index']
    node_type = json['value']
    print(f"{index} : {node_type}")

    node = latest_nodes[int(index)]
    node.type = NodeType(int(node_type))
    kube_nodes.append(node)

    # You can access json['index'] and json['value'] here to update the node.
    # After updating, emit a success message back to the client.
    emit('update_success_' + str(json['index']), {'success': True})
