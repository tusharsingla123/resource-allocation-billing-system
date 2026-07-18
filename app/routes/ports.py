"""Port-related routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from collections import defaultdict

from app import db
from app.models import Port, PortArea, AllotmentRate, Item, TaxRate
from app.utils.decorators import nocache
from app.utils.calculations import calculate_port_amounts, update_monthly_material_cost

bp = Blueprint('ports', __name__, url_prefix='')

@bp.route('/add-port/<int:item_id>', methods=['GET', 'POST'])
@login_required
@nocache
def add_port(item_id):
    """Add a port to a vessel"""
    item = Item.query.get_or_404(item_id)
    # Get only ports that are not already allotted (no active, non-handover entries)
    assigned_port_numbers = [p.port_number for p in Port.query.with_entities(Port.port_number).filter_by(vessel_id=item.id).all()]
    port_areas = PortArea.query.filter(~PortArea.port_number.in_(assigned_port_numbers)).all()

    if request.method == 'POST':
        selected_ports = request.form.getlist('port_numbers')
        start_date_str = request.form['f-date']
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=29)
        allotment_number = 1
        days_allocated = 30

        for port_number in selected_ports:
            port_area_entry = PortArea.query.filter_by(port_number=port_number).first()
            sqm_covered = port_area_entry.area if port_area_entry else 0
            kacha = port_area_entry.kacha if port_area_entry else 0

            rate_entry = AllotmentRate.query.filter_by(allotment_number=allotment_number).first()
            penalty = rate_entry.kacha_penalty if kacha == 0 else rate_entry.paka_penalty

            new_port = Port(
                port_number=port_number,
                sqm_covered=sqm_covered,
                allotment_number=allotment_number,
                days_allocated=days_allocated,
                penalty_per_day=penalty,
                start_date=start_date,
                end_date=end_date,
                vessel_id=item.id
            )
            db.session.add(new_port)

        db.session.commit()
        return redirect(url_for('vessels.more_info', item_id=item.id))
    return render_template('add_port.html', item=item, port_areas=port_areas)


@bp.route('/next-allotment-port/<int:port_id>/<int:item_id>')
@login_required
@nocache
def next_allotment_port(port_id, item_id):
    """Create next allotment for a port"""
    port = Port.query.get_or_404(port_id)
    new_allotment_number = port.allotment_number + 1 if port.allotment_number < 4 else 4
    rate_entry = AllotmentRate.query.filter_by(allotment_number=new_allotment_number).first()
    port_area = PortArea.query.filter_by(port_number=port.port_number).first()
    kacha = port_area.kacha if port_area else 0

    # Calculate new penalty
    if kacha == 0:
        penalty_per_day = rate_entry.kacha_penalty if rate_entry else 0
        rate_per_sqm = rate_entry.kacha_rate if rate_entry else 0
    else:
        penalty_per_day = rate_entry.paka_penalty if rate_entry else 0
        rate_per_sqm = rate_entry.paka_rate if rate_entry else 0
        
    start_date = port.end_date + timedelta(days=1)
    end_date = start_date + timedelta(days=29)
    
    # Create new Port row
    new_port = Port(
        port_number=port.port_number,
        sqm_covered=port.sqm_covered,
        allotment_number=new_allotment_number,
        days_allocated=port.days_allocated,
        penalty_per_day=port.penalty_per_day,
        start_date=start_date,
        end_date=end_date,
        vessel_id=port.vessel_id
    )

    db.session.add(new_port)
    db.session.commit()
    return redirect(url_for('vessels.more_info', item_id=item_id))


@bp.route('/update-adv-note/<int:port_id>', methods=['POST'])
@login_required
@nocache
def update_adv_note(port_id):
    """Update advance note dates for a port"""
    port = Port.query.get_or_404(port_id)
    adv_penalty = request.form.get('adv_penalty')
    adv_base = request.form.get('adv_base')

    port.adv_penalty_note = datetime.strptime(adv_penalty, '%Y-%m-%d').date() if adv_penalty else None
    port.adv_base_note = datetime.strptime(adv_base, '%Y-%m-%d').date() if adv_base else None
    db.session.commit()
    return redirect(request.referrer or url_for('vessels.home_page'))


@bp.route('/handover-port/<port_number>/<int:item_id>', methods=['POST'])
@login_required
@nocache
def handover_port(port_number, item_id):
    """Handle port handover"""
    print("------------------handover logic 1-------------------------")

    handover_date_str = request.form.get("handover_date")
    try:
        handover_date = datetime.strptime(handover_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        flash("Invalid handover date format", "danger")
        return redirect(url_for('vessels.more_info', item_id=item_id))

    latest_port = (
        Port.query
        .filter_by(port_number=port_number, vessel_id=item_id)
        .order_by(Port.id.desc())
        .first()
    )

    if latest_port:
        latest_port.end_date = handover_date
        latest_port.handover = True

        ports = Port.query.filter_by(vessel_id=item_id, port_number=port_number).all()
        for port in ports:
            port.handover = True
        db.session.commit()   

        calculate_port_amounts(item_id)
        update_monthly_material_cost(latest_port, port_number, item_id, handover_date)

    return redirect(url_for('vessels.more_info', item_id=item_id))


@bp.route('/edit-port/<int:port_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_port(port_id):
    """Edit port details"""
    port = Port.query.get_or_404(port_id)
    if request.method == 'POST':
        port.port_number = request.form['port_number']  # Now editable
        port.allotment_number = request.form['allotment_number']
        port.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        port.end_date = port.start_date + timedelta(30)
        port.days_allocated = 30
        db.session.commit()
        return redirect(url_for('vessels.more_info', item_id=port.vessel_id))

    return render_template('edit_port.html', port=port)


@bp.route('/port-status')
@login_required
@nocache
def port_status():
    """View status of all ports"""
    all_ports = PortArea.query.all()
    port_entries = Port.query.all()
    port_stats = defaultdict(lambda: {
        'area': 0,
        'surface': 'Kacha',
        'status': 'Available',
        'days_passed': 0,
        'allotments': 0,
        'vessel_name': '',
        'material': ''
    })

    first_allotment_map = {}
    latest_port_map = {}

    for entry in port_entries:
        port_number = entry.port_number
        port_stats[port_number]['status'] = "Allotted" if not entry.handover else "Available"
        port_stats[port_number]['allotments'] += 1

        # Track the earliest start date per port
        if port_number not in first_allotment_map or entry.start_date < first_allotment_map[port_number]:
            first_allotment_map[port_number] = entry.start_date

        # Track latest entry per port for material/vessel
        if port_number not in latest_port_map or entry.start_date > latest_port_map[port_number].start_date:
            latest_port_map[port_number] = entry

    for port in all_ports:
        port_number = port.port_number
        port_stats[port_number]['area'] = port.area
        port_stats[port_number]['surface'] = "Platform" if port.kacha else "Kacha"

        # Get the days passed from first allotment to today
        if port_number in first_allotment_map:
            delta_days = (date.today() - first_allotment_map[port_number]).days
            port_stats[port_number]['days_passed'] = max(0, delta_days)

        if port_number in latest_port_map:
            latest_entry = latest_port_map[port_number]
            port_stats[port_number]['vessel_name'] = latest_entry.vessel.vessel_name
            port_stats[port_number]['material'] = latest_entry.vessel.material

    ports_list = [{
        'port_number': p,
        'area': data['area'],
        'surface': data['surface'],
        'status': data['status'],
        'days_passed': data['days_passed'],
        'allotments': data['allotments'],
        'vessel_name': data['vessel_name'],
        'material': data['material']
    } for p, data in port_stats.items()]

    # Normalize for gradient coloring
    max_days = max([p['days_passed'] for p in ports_list], default=1)
    min_days = min([p['days_passed'] for p in ports_list], default=0)

    def calculate_color(days):
        ratio = (days - min_days) / (max_days - min_days + 1e-5)
        r = int(255 * ratio) - 50
        g = int(255 * (1 - ratio) - 30)
        return f'rgb({r}, {g}, 50)'

    for port in ports_list:
        port['color'] = calculate_color(port['days_passed'])

    ports_list.sort(key=lambda x: x['days_passed'], reverse=True)
    return render_template("port_status.html", ports=ports_list)


@bp.route('/delete-port/<int:port_id>/<int:item_id>', methods=['POST'])
@login_required
@nocache
def delete_port(port_id, item_id):
    """Delete a port"""
    port = Port.query.get_or_404(port_id)
    db.session.delete(port)
    deleted_port_number = port.port_number
    handover_reset = Port.query.filter_by(port_number=deleted_port_number, vessel_id=item_id).all()
    for port in handover_reset:
        port.handover = False
    db.session.commit()
    return redirect(url_for('vessels.more_info', item_id=item_id))
