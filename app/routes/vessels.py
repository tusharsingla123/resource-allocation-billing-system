"""Vessel-related routes"""
import statistics
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from collections import defaultdict
import pandas as pd
import io

from app import db
from app.models import Item, Port, PortArea, AllotmentRate, Material, MaterialRecord, Stock
from app.utils.decorators import nocache
from app.utils.calculations import calculate_port_amounts, compute_totals

bp = Blueprint('vessels', __name__, url_prefix='')

@bp.route('/home')
@login_required
@nocache
def home_page():
    """Main dashboard page showing all vessels and statistics"""
    if current_user.is_authenticated:
        pass
    elif session.get("admin_id"):
        pass
    else:
        return redirect(url_for("auth.login")) 
    
    items = Item.query.all()
    vessels = []
    chart_labels = []
    chart_values = []
    avg = 0
    turnaround_data = []

    # Coal chart data(BL)
    coal_labels = []
    coal_volumes = []

    # Limestone chart data(BL)
    limestone_labels = []
    limestone_volumes = []

    # MONTHLY (COST)
    coal_month = []
    coal_cost = []
    limestone_month = []
    limestone_cost = []

    monthly_totals = defaultdict(float)
    records = MaterialRecord.query.all()

    for r in records:
        month_date = datetime.strptime(r.month, "%Y-%m")  # parse "YYYY-MM"
        key = (r.material, month_date.year, month_date.month)
        monthly_totals[key] += r.total_amount

    # Print results
    for (material, year, month), total in monthly_totals.items():
        print(material, year, month, total)

    # for monthly calculations
    for (material, year, month), total in monthly_totals.items():
        if material == "Coal":
            coal_month.append(f"{month}/{year}")  # e.g., "12/2025"
            coal_cost.append(total)
        elif material == "Limestone":
            limestone_month.append(f"{month}/{year}")  # e.g., "12/2025"
            limestone_cost.append(total)
    
    # Combine monthly totals (coal + limestone or all materials)
    combined_month_totals = {}
    for (material, year, month), total in monthly_totals.items():
        key = (year, month)
        combined_month_totals[key] = combined_month_totals.get(key, 0) + total

    # Fetch stock records
    stock_records = Stock.query.all()

    # Merge Stock and Total Amount
    merged_data = []

    for stk in stock_records:
        # Convert "YYYY-MM" to (year, month)
        year, month = map(int, stk.Month.split("-"))

        # Get total amount from combined monthly totals
        total_amount = combined_month_totals.get((year, month), 0)

        # Append merged info
        merged_data.append({
            "month": stk.Month,
            "stock": stk.Stock,
            "total_amount": total_amount
        })

    for item in items:
        ports = item.ports
        port_numbers = list(set(p.port_number for p in ports))
        all_handed_over = all(p.handover for p in ports) if ports else False
        # Cost per ton
        total_cost = sum((getattr(p, 'total_amount', 0) or 0) for p in ports)
        cost_per_ton = round(total_cost / item.volume_bl, 2) if item.volume_bl else 0

        # Turnaround time
        if ports:
            start_date = min(p.start_date for p in ports)
            end_date = max(p.end_date for p in ports)
            turnaround_days = (end_date - start_date).days
        else:
            turnaround_days = 0

        chart_labels.append(item.vessel_name)
        chart_values.append(cost_per_ton)
        avg = round(statistics.mean(chart_values), 3)
        turnaround_data.append({'vessel_name': item.vessel_name, 'days': turnaround_days})

        vessels.append({
            'item': item,
            'port_numbers': port_numbers,
            'all_handed_over': all_handed_over
        })

        # Coal data
        if 'Coal' in item.material:
            coal_labels.append(item.vessel_name)
            coal_volumes.append(item.volume_bl if item.volume_bl else 0)

        # Limestone data
        if 'Limestone' in item.material:
            limestone_labels.append(item.vessel_name)
            limestone_volumes.append(item.volume_bl if item.volume_bl else 0)

    return render_template(
        'home.html',
        vessels=vessels,
        items=items,
        chart_labels=chart_labels,
        chart_values=chart_values,
        turnaround_data=turnaround_data,
        coal_labels=coal_labels,
        coal_volumes=coal_volumes,
        limestone_labels=limestone_labels,
        limestone_volumes=limestone_volumes,
        coal_month=coal_month,
        coal_cost=coal_cost,
        limestone_month=limestone_month,
        limestone_cost=limestone_cost,
        merged_data=merged_data,
        avg_value=avg
    )


@bp.route('/add-vessel', methods=['GET', 'POST'])
@login_required
@nocache
def add_vessel():
    """Add a new vessel"""
    # Step 1: Get all active port numbers (not handed over)
    active_ports = db.session.query(Port.port_number).filter(Port.handover == False).distinct().all()

    # Step 2: Extract list of active port numbers
    active_port_numbers = [p.port_number for p in active_ports]

    # Step 3: Get ports from PortArea that are NOT actively assigned
    port_areas = PortArea.query.filter(~PortArea.port_number.in_(active_port_numbers)).all()
    materials = Material.query.all()

    if request.method == 'POST':
        material = request.form.get('material')
        vessel_name = request.form.get('vessel_name')
        volume_demo_port = float(request.form.get('volume_port') or 0)
        volume_bl = float(request.form.get('volume_bl') or 0)
        port_numbers = request.form.getlist('port_numbers')
        start_date = request.form.get('start_date')
        purchase_order = request.form.get('purchase_order')

        new_item = Item(
            material=material,
            vessel_name=vessel_name,
            purchase_order=purchase_order,
            volume_demo_port=volume_demo_port,
            volume_bl=volume_bl
        )
        db.session.add(new_item)
        db.session.commit()

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = start_date_obj + timedelta(days=29)

        for port_number in port_numbers:
            port_area_entry = PortArea.query.filter_by(port_number=port_number).first()
            sqm_covered = port_area_entry.area if port_area_entry else 0
            kacha = port_area_entry.kacha if port_area_entry else 0

            rate_entry = AllotmentRate.query.filter_by(allotment_number=1).first()
            penalty = rate_entry.kacha_penalty if kacha == 0 else rate_entry.paka_penalty

            new_port = Port(
                port_number=port_number,
                sqm_covered=sqm_covered,
                allotment_number=1,
                days_allocated=30,
                penalty_per_day=penalty,
                start_date=start_date_obj,
                end_date=end_date,
                vessel_id=new_item.id
            )
            db.session.add(new_port)

        db.session.commit()
        return redirect(url_for('vessels.home_page'))
    return render_template('add_vessel.html', port_areas=port_areas, materials=materials)


@bp.route('/edit_vessel/<int:item_id>', methods=['GET','POST'])
@login_required
@nocache
def edit_vessel(item_id):
    """Edit vessel details"""
    vessel = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        vessel.material = request.form.get('material')
        vessel.volume_demo_port = float(request.form.get('volume-port') or 0)
        vessel.volume_bl = float(request.form.get('volume-bl') or 0)
        vessel.purchase_order = request.form.get('purchase_order')

        db.session.commit()
        flash('Vessel details updated successfully!', 'success')
        return redirect(url_for('vessels.more_info', item_id=item_id))

    return render_template('edit_vessel.html', item=vessel)


@bp.route('/more-info/<int:item_id>')
@login_required
@nocache
def more_info(item_id):
    """View detailed information about a vessel"""
    item = Item.query.get_or_404(item_id)
    # Always ensure amounts are freshly calculated before displaying
    calculate_port_amounts(item_id)
    grand_total = compute_totals(item.ports, filter_handover=True)
    total_amount_all = compute_totals(item.ports, filter_handover=False)

    from app.models import TaxRate
    tax = TaxRate.query.first()
    gst_rate = tax.gst / 100 if tax else 0.09
    cgst_rate = tax.cgst / 100 if tax else 0.09

    ports = Port.query.filter_by(vessel_id=item_id).all()

    port_data = []
    table_base = 0
    table_penalty = 0
    table_total = 0

    # Recompute display data only (NOT price logic)
    for port in ports:
        port_area = PortArea.query.filter_by(port_number=port.port_number).first()
        area = port_area.area if port_area else 0
        kacha = port_area.kacha if port_area else 0

        rate = (
            AllotmentRate.query
            .filter(AllotmentRate.allotment_number == port.allotment_number)
            .filter(AllotmentRate.from_date <= port.start_date)
            .order_by(AllotmentRate.from_date.desc())
            .first()
        )

        if kacha == 0:
            rate_per_sqm = rate.kacha_rate if rate else 0
            penalty_per_day = rate.kacha_penalty if rate else 0
        else:
            rate_per_sqm = rate.paka_rate if rate else 0
            penalty_per_day = rate.paka_penalty if rate else 0

        # Base rate was already calculated inside calculate_port_amounts()
        new_date = date(2025, 8, 31)
        if port.start_date > new_date and rate and rate.allotment_number != 1:
            base_rate = 0
        else:
            base_rate = (area * rate_per_sqm) / 10 if rate else 0

        # Recompute penalty for display only
        end_reference = port.end_date if port.handover else min(date.today(), port.end_date)

        days_passed = (end_reference - port.start_date).days + 1
        if days_passed < 0:
            days_passed = 0

        capped_days = min(days_passed, 30)
        area_10 = round(area / 10, 0)
        total_penalty = penalty_per_day * capped_days * area_10

        port_data.append({
            'port': port,
            'base_rate': base_rate,
            'penalty_per_day': penalty_per_day,
            'total_penalty': total_penalty,
            'total_amount': port.total_amount  # already computed earlier
        })

        table_base += base_rate
        table_penalty += total_penalty
        table_total += port.total_amount

    # Group by port number for template
    grouped_ports = defaultdict(list)
    for row in port_data:
        grouped_ports[row['port'].port_number].append(row)

    return render_template(
        'more_info.html',
        item=item,
        grouped_ports=grouped_ports,
        current_date=date.today(),
        grand_total=grand_total,
        total_amount_all=total_amount_all,
        table_base=table_base,
        table_penalty=table_penalty,
        table_total=table_total,
        timedelta=timedelta
    )


@bp.route('/delete-vessel/<int:item_id>', methods=['POST'])
@login_required
@nocache
def delete_vessel(item_id):
    """Delete a vessel and its associated ports"""
    vessel = Item.query.get_or_404(item_id)
    # Delete associated ports first
    for port in vessel.ports:
        db.session.delete(port)
    db.session.delete(vessel)
    db.session.commit()
    return redirect(url_for('vessels.home_page'))


@bp.route('/export-vessel/<int:item_id>')
@login_required
@nocache
def export_vessel(item_id):
    """Export vessel data to Excel"""
    item = Item.query.get_or_404(item_id)
    ports = item.ports

    data = []
    for port in ports:
        port_area = PortArea.query.filter_by(port_number=port.port_number).first()
        area = port_area.area if port_area else 0
        kacha = port_area.kacha if port_area else 0

        rate = AllotmentRate.query.filter_by(allotment_number=port.allotment_number).first()
        if kacha == 0:
            rate_per_sqm = rate.kacha_rate if rate else 0
            penalty_per_day = rate.kacha_penalty if rate else 0
        else:
            rate_per_sqm = rate.paka_rate if rate else 0
            penalty_per_day = rate.paka_penalty if rate else 0

        base_rate = (area * rate_per_sqm) / 10
        days_passed = (date.today() - port.start_date).days
        total_penalty = penalty_per_day * (days_passed - 30) if days_passed > 30 else 0

        data.append({
            "Port Number": port.port_number,
            "Allotment Number": port.allotment_number,
            "Start Date": port.start_date,
            "End Date": port.end_date,
            "Area": area,
            "Surface Type": "Platform" if kacha else "Kacha",
            "Base Rate": base_rate,
            "Penalty/Day": penalty_per_day,
            "Total Penalty": total_penalty,
            "Handover": "Yes" if port.handover else "No"
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Port Allotments')

    output.seek(0)
    return send_file(
        output,
        download_name=f"{item.vessel_name.replace(' ', '_')}_ports.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@bp.route('/export-all-vessels')
@login_required
@nocache
def export_all_vessels():
    """Export all vessels data to Excel"""
    items = Item.query.all()

    vessel_data = []
    port_data = []

    for item in items:
        vessel_data.append({
            'Vessel ID': item.id,
            'Material': item.material,
            'Vessel Name': item.vessel_name,
            'Purchase Order': item.purchase_order,
            'Volume Demo Port (tons)': item.volume_demo_port,
            'Volume BL (tons)': item.volume_bl,
        })

        for port in item.ports:
            port_data.append({
                'Vessel ID': item.id,
                'Port Number': port.port_number,
                'Start Date': port.start_date,
                'End Date': port.end_date,
                'Allotment Number': port.allotment_number,
                'Days Allocated': port.days_allocated,
                'Penalty/Day': port.penalty_per_day,
                'Handover': 'Yes' if port.handover else 'No',
                'Total Amount': getattr(port, 'total_amount', 'N/A')
            })

    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(vessel_data).to_excel(writer, sheet_name='Vessels', index=False)
        pd.DataFrame(port_data).to_excel(writer, sheet_name='Associated Plots', index=False)
    output.seek(0)
    return send_file(
        output,
        download_name="vessels_info.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
