"""Statistics routes"""
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from datetime import date
from collections import defaultdict

from app import db
from app.models import Port, PortArea, AllotmentRate, TaxRate, Item, MonthlyStats
from sqlalchemy import func
from app.utils.decorators import nocache

bp = Blueprint('statistics', __name__, url_prefix='')

@bp.route('/statistics', methods=['GET', 'POST'])
@login_required
@nocache
def statistics():
    """View statistics page"""
    selected_year = request.args.get('year', date.today().year, type=int)
    selected_fy_start = request.args.get('year', date.today().year, type=int)

    # Define financial year range
    start_date = date(selected_fy_start, 4, 1)  # April 1
    end_date = date(selected_fy_start + 1, 3, 31)  # March 31

    # Financial year months in order
    financial_year_months = ['April', 'May', 'June', 'July', 'August', 'September',
                             'October', 'November', 'December', 'January', 'February', 'March']

    # Filter ports within financial year range
    ports = Port.query.filter(Port.start_date >= start_date, Port.start_date <= end_date).all()

    tax = TaxRate.query.first()
    gst = tax.gst / 100 if tax else 0.09
    cgst = tax.cgst / 100 if tax else 0.09
    monthly_cost = defaultdict(float)

    for port in ports:
        if not port.start_date:
            continue
        month = port.start_date.strftime('%B')
        port_area = PortArea.query.filter_by(port_number=port.port_number).first()
        area = port_area.area if port_area else 0
        kacha = port_area.kacha if port_area else 0

        rate = AllotmentRate.query.filter_by(allotment_number=port.allotment_number).first()
        if not rate:
            continue
        rate_per_sqm = rate.kacha_rate if kacha == 0 else rate.paka_rate
        penalty_rate = rate.kacha_penalty if kacha == 0 else rate.paka_penalty

        base = (area * rate_per_sqm) / 10
        days_late = (date.today() - port.end_date).days
        penalty = penalty_rate * max(days_late, 0)

        total_cost = base + penalty
        taxed_total = total_cost * (1 + gst + cgst)

        monthly_cost[month] += round(taxed_total, 2)

    if request.method == 'POST':
        for key in request.form:
            if key.startswith('tonnage_'):
                month = key.split('_')[1]
                tonnage_val = request.form[key]
                tonnage = float(tonnage_val or 0)
                cost = monthly_cost.get(month, 0)
                cost_per_ton = round(cost / tonnage, 2) if tonnage else 0

                entry = MonthlyStats.query.filter_by(month=month, year=selected_fy_start).first()
                if not entry:
                    entry = MonthlyStats(month=month, year=selected_fy_start)
                    db.session.add(entry)

                entry.total_tonnage = tonnage
                entry.cost_per_ton = cost_per_ton

        db.session.commit()
        return redirect(url_for('statistics.statistics', year=selected_fy_start))

    stats = []
    financial_year_months = ['April', 'May', 'June', 'July', 'August', 'September',
                         'October', 'November', 'December', 'January', 'February', 'March']

    for month in financial_year_months:
        cost = monthly_cost.get(month, 0)
        # Dynamically adjust year for Jan–Mar
        display_year = selected_year if month not in ['January', 'February', 'March'] else selected_year + 1

        stat = MonthlyStats.query.filter_by(month=month, year=display_year).first()
        tonnage = stat.total_tonnage if stat else ''
        cost_per_ton = stat.cost_per_ton if stat else ''
        stats.append({
            'month': month,
            'year': display_year,  
            'total_cost': cost,
            'total_tonnage': tonnage,
            'cost_per_ton': cost_per_ton
        })

    labels = financial_year_months
    cost_values = [monthly_cost.get(m, 0) for m in labels]

    material_totals = db.session.query(Item.material, db.func.sum(Port.total_amount)
                    ).join(Port).group_by(Item.material).all()

    material_labels = [row[0] for row in material_totals]
    material_amounts = [round(row[1], 2) for row in material_totals]

    return render_template('statistics.html',
                           stats=stats,
                           selected_year=selected_fy_start,
                           labels=labels,
                           material_labels=material_labels,
                           material_amounts=material_amounts,
                           costs=cost_values)
