from flask import current_app

from app.models import KubernetesNode, NodeType
from app.services.kube import core_v1
from app.services.db import config_collection

kube_nodes: list[KubernetesNode] = []


def load_nodes_from_db():
    global kube_nodes
    print("Loading nodes from database...")

    for node in config_collection.find_one({"_id": "kube_nodes"})['nodes']:
        node = KubernetesNode.from_json(node)
        print(f"Loaded node '{node.hostname}' <{node.type}>")
        kube_nodes.append(node)

    print(f"Loaded {len(kube_nodes)} nodes from database")


def get_raw_nodes(alive=False):
    try:
        nodes = core_v1.list_node()
    except Exception as E:
        print(f"Failed to get raw nodes: {E}")
        return []

    if alive:
        return [node for node in nodes.items if node.status.conditions[3].status == 'True']

    return [node for node in nodes.items]


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
