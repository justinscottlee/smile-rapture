from flask import render_template, flash, Blueprint

from app.services.node import get_latest_nodes, kube_nodes
from app.services.auth import admin_required
from app.services.experiments import admin_experiment_queue
from app.models import User, Experiment

# Create a Blueprint for auth-related routes
bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@admin_required
def admin_view(admin_user: User):
    experiments = Experiment.get_all()

    for experiment in experiments:
        try:
            experiment.update()
        except Exception as E:
            flash(f"Error: Experiment update failed '{experiment.experiment_uuid}' {str(E)}")

    return render_template('admin.html', user=admin_user, nodes=kube_nodes,
                           experiments=experiments, admin_exp=admin_experiment_queue, users=User.get_all())


@bp.route('/nodes', methods=['GET'])
@admin_required
def node_config_view(user: User):
    try:
        get_latest_nodes()
    except Exception as E:
        flash(f"Error: Could not get node list {str(E)}")

    return render_template("nodes.html", nodes=kube_nodes)
