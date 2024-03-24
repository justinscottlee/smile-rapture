from app.models import Experiment, Node, NodeType
from app.services.db import experiment_collection, config_collection

admin_experiment_queue: list[Experiment] = []


def load_experiment_queue_from_db():
    global admin_experiment_queue

    # Load the experiment queue from the database:
    exp_uuids = config_collection.find_one({"_id": "admin_experiment_queue"})['queue']
    admin_experiment_queue = [Experiment.get_by_id(exp_uuid) for exp_uuid in exp_uuids]
