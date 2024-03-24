from flask import current_app

from app.models import KubernetesNode, NodeType
from app.services.kube import core_v1
from app.services.db import config_collection

kube_nodes: list[KubernetesNode] = []


def load_nodes_from_db():
    global kube_nodes
    kube_nodes = [KubernetesNode.from_json(node) for node in config_collection.find_one({"_id": "kube_nodes"})['nodes']]


def get_latest_nodes():
    global kube_nodes
    if current_app.config['FAKE_MODE']:
        kube_nodes.clear()
        kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname='fake-rpi.local'))
        kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname='fake-bot.local'))
        return

    nodes = core_v1.list_node()

    for node in nodes.items:
        known = False
        for kube_node in kube_nodes:
            if kube_node.hostname == node.metadata.name:
                known = True
                break
        if not known:
            kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname=node.metadata.name))
