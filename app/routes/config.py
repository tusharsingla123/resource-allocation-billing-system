"""Configuration and admin routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime

from app import db
from app.models import AllotmentRate, PortArea, TaxRate, Material, Stock
from app.utils.decorators import nocache

bp = Blueprint('config', __name__, url_prefix='')

@bp.route('/all_info')
@login_required
@nocache
def all_info():
    """View all configuration settings"""
    rates = AllotmentRate.query.all()
    ports = PortArea.query.all()
    tax_rates = TaxRate.query.all()
    materials = Material.query.all()
    Stocks = Stock.query.all()   

    return render_template(
        'all_info.html',
        rates=rates,
        ports=ports,
        tax_rates=tax_rates,
        materials=materials,
        Stocks=Stocks             
    )


@bp.route('/add-material', methods=['GET', 'POST'])
@login_required
@nocache
def add_material():
    """Add a new material"""
    if request.method == 'POST':
        material_name = request.form['material_name']
        material_type = request.form['material_type'] 

        if material_name and material_type is not None:
            new_material = Material(
                material_name=material_name,
                material_type=material_type 
            )
            db.session.add(new_material)
            db.session.commit()
            flash("Material added successfully!", "success")
            return redirect(url_for('config.all_info'))
    return render_template('add_material.html')


@bp.route('/edit-allotment-rate/<int:rate_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_allotment_rate(rate_id):
    """Edit allotment rate"""
    rate = AllotmentRate.query.get_or_404(rate_id)
    if request.method == 'POST':
        rate.kacha_rate = request.form['kacha_rate']
        rate.paka_rate = request.form['paka_rate']
        rate.kacha_penalty = request.form['kacha_penalty']
        rate.paka_penalty = request.form['paka_penalty']

        # Fix: Convert string to date
        from_date_str = request.form['from_date']
        if from_date_str:
            rate.from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()

        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('edit_allotment_rate.html', rate=rate)


@bp.route('/edit-tax-rate/<int:tax_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_tax_rate(tax_id):
    """Edit tax rate"""
    tax = TaxRate.query.get_or_404(tax_id)
    if request.method == 'POST':
        tax.gst = request.form['gst']
        tax.cgst = request.form['cgst']
        tax.from_date = request.form['from_date']
        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('edit_tax_rate.html', tax=tax)


@bp.route('/edit_material/<int:material_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_material(material_id):
    """Edit material"""
    material = Material.query.get_or_404(material_id)
    if request.method == 'POST':
        material.material_id = request.form['material_id']
        material.material_name = request.form['material_name']
        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('edit_material.html', material=material)


@bp.route('/edit-port-area/<int:port_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_port_area(port_id):
    """Edit port area"""
    port = PortArea.query.get_or_404(port_id)
    if request.method == 'POST':
        port.area = float(request.form['area'])  # Make sure this is float
        port.kacha = request.form['kacha'] == '1'  # Converts '1' → True, '0' → False
        from_date_str = request.form['from_date']
        if from_date_str:
            port.from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('edit_port_area.html', port=port)


@bp.route('/delete-allotment-rate/<int:rate_id>', methods=['POST'])
@login_required
@nocache
def delete_allotment_rate(rate_id):
    """Delete allotment rate"""
    rate = AllotmentRate.query.get_or_404(rate_id)
    db.session.delete(rate)
    db.session.commit()
    return redirect(url_for('config.all_info'))


@bp.route('/delete-tax-rate/<int:tax_id>', methods=['POST'])
@login_required
@nocache
def delete_tax_rate(tax_id):
    """Delete tax rate"""
    tax = TaxRate.query.get_or_404(tax_id)
    db.session.delete(tax)
    db.session.commit()
    return redirect(url_for('config.all_info'))


@bp.route('/delete_material/<int:material_id>', methods=['POST'])
@login_required
@nocache
def delete_material(material_id):
    """Delete material"""
    material = Material.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('config.all_info'))


@bp.route('/delete-port-area/<int:port_id>', methods=['POST'])
@login_required
@nocache
def delete_port_area(port_id):
    """Delete port area"""
    port = PortArea.query.get_or_404(port_id)
    db.session.delete(port)
    db.session.commit()
    return redirect(url_for('config.all_info'))


@bp.route('/add-allotment-rate', methods=['GET', 'POST'])
@login_required
@nocache
def add_allotment_rate():
    """Add new allotment rate"""
    if request.method == 'POST':
        from_date = datetime.strptime(request.form['from_date'], '%Y-%m-%d').date()
        base_kacha = float(request.form['kacha_rate'])
        base_paka = float(request.form['paka_rate'])

        allotment_data = []

        for i in range(1, 5):  # 1st to 4th allotment
            multiplier = [1.0, 1.25, 1.5, 2.0][i - 1]
            kacha_rate = round(base_kacha * multiplier, 4)
            paka_rate = round(base_paka * multiplier, 4)

            if i == 1:
                kacha_penalty = 0
                paka_penalty = 0
            else:
                kacha_penalty = round((kacha_rate * i) / 30, 4)
                paka_penalty = round((paka_rate * i) / 30, 4)

            allotment_data.append(AllotmentRate(
                allotment_number=i,
                kacha_rate=kacha_rate,
                paka_rate=paka_rate,
                kacha_penalty=kacha_penalty,
                paka_penalty=paka_penalty,
                from_date=from_date
            ))

        db.session.add_all(allotment_data)
        db.session.commit()
        return redirect(url_for('config.all_info'))

    return render_template('add_allotment_rate.html')


@bp.route('/add-port-area', methods=['GET', 'POST'])
@login_required
@nocache
def add_port_area():
    """Add new port area"""
    if request.method == 'POST':
        new_port = PortArea(
            port_number=request.form['port_number'],
            area=request.form['area'],
            kacha=True if request.form['kacha'] == '1' else False
        )
        db.session.add(new_port)
        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('add_port_area.html')


@bp.route('/add-stock', methods=['GET','POST'])
@login_required
@nocache
def add_stock():
    """Add stock data"""
    if request.method == 'POST':
        new_stock = Stock(
            Month=request.form.get('month'),   # lowercase from form
            Stock=request.form.get('stock')
        )
        db.session.add(new_stock)
        db.session.commit()
        return redirect(url_for('config.all_info'))
        
    return render_template('add_stock_data.html')


@bp.route('/edit-stock-rate/<int:stock_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_stock_rate(stock_id):
    """Edit stock data"""
    stock = Stock.query.get_or_404(stock_id)   
    if request.method == 'POST':
        stock.Month = request.form.get('month')   
        stock.Stock = request.form.get('stock')
        db.session.commit()
        return redirect(url_for('config.all_info'))
    return render_template('edit_stock_data.html', stock=stock)


@bp.route('/delete_stock/<int:stock_id>', methods=['POST'])
@login_required
@nocache
def delete_stock_rate(stock_id):
    """Delete stock data"""
    stock = Stock.query.get_or_404(stock_id)  
    db.session.delete(stock)                   
    db.session.commit()
    return redirect(url_for('config.all_info'))
