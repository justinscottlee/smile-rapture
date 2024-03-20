from flask import render_template, flash, Blueprint

from app.models import KubernetesNode
from app.services.auth import admin_required
from app.models import User, Experiment

# Create a Blueprint for auth-related routes
bp = Blueprint('admin', __name__)


@bp.route('/admin')
@admin_required
def admin(user: User):
    experiments = Experiment.get_all()

    for experiment in experiments:
        try:
            experiment.update()
        except Exception as E:
            flash(f"Error: Experiment update failed '{experiment.experiment_uuid}' {str(E)}")

    return render_template('admin.html', user=user,
                           experiments=experiments, users=User.get_all())


@bp.route('/nodes', methods=['GET'])
@admin_required
def show_all_nodes(_):
    try:
        nodes = KubernetesNode.get_all()
    except Exception as E:
        flash(f"Error: Could not get node list {str(E)}")
        nodes = []

    return render_template("nodes.html", nodes=nodes)
