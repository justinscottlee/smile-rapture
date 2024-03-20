from app.models import KubernetesNode, NodeType
from app.services.kube import core_v1

kube_nodes: list[KubernetesNode] = []
latest_nodes: list[KubernetesNode] = []


def get_latest_nodes():
    nodes = core_v1.list_node()

    for node in nodes.items:
        latest_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname=node.metadata.name))

    return latest_nodes
