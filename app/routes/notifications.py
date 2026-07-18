"""Notifications routes"""
from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date, timedelta

from app.models import Port
from app.utils.decorators import nocache

bp = Blueprint('notifications', __name__, url_prefix='')

def get_ports_nearing_end(days_notice=3):
    """Get ports that are nearing their end date"""
    today = date.today()
    notice_date = today + timedelta(days=days_notice)
    # Find ports where end date is within the next X days
    ports_due = Port.query.filter(
        Port.end_date <= notice_date,
        Port.end_date >= today
    ).all()

    return ports_due


@bp.route('/notifications')
@login_required
@nocache
def notifications():
    """View notifications for ports nearing end"""
    due_ports = get_ports_nearing_end()
    return render_template('notifications.html', ports=due_ports)


def inject_due_ports():
    """Context processor to inject due ports into all templates"""
    today = date.today()
    upcoming = today + timedelta(days=5)
    due_ports = Port.query.filter(
        Port.end_date <= upcoming,
        Port.end_date >= today
    ).all()
    return dict(due_ports=due_ports)
