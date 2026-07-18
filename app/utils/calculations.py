"""Business logic and calculation functions"""
from app import db
from app.models import Item, Port, PortArea, AllotmentRate, TaxRate, Material, MaterialRecord
from datetime import date
from collections import defaultdict

def compute_totals(ports, filter_handover):
    """Compute total amounts for ports, optionally filtering handover ports"""
    total = 0
    for port in ports:
        if filter_handover and port.handover:
            continue
        if port.total_amount:
            total += port.total_amount
    return total


def calculate_port_amounts(item_id):
    """Calculate total amounts for all ports of a vessel"""
    item = Item.query.get(item_id)
    tax_rate = TaxRate.query.first()
    if not tax_rate:
        gst_rate = 0.09
        cgst_rate = 0.09
    else:
        gst_rate = tax_rate.gst / 100
        cgst_rate = tax_rate.cgst / 100

    new_date = date(2025, 8, 31)
    for port in item.ports:
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

        # Decide end reference (handover or ongoing)
        end_reference = port.end_date if port.handover else min(date.today(), port.end_date)

        # Business logic
        if port.start_date > new_date and rate and rate.allotment_number != 1:
            base_rate = 0
        else:
            base_rate = (area * rate_per_sqm) / 10 if rate else 0

        days_passed = (end_reference - port.start_date).days + 1
        if days_passed < 0:
            days_passed = 0

        capped_days = min(days_passed, 30)
        area_10 = round(area / 10, 0)

        total_penalty = penalty_per_day * capped_days * area_10
        base_gst = base_rate * gst_rate
        base_cgst = base_rate * cgst_rate
        penalty_gst = total_penalty * gst_rate
        penalty_cgst = total_penalty * cgst_rate

        total_amount = round(
            base_rate + base_gst + base_cgst +
            total_penalty + penalty_gst + penalty_cgst,
            0
        )

        port.total_amount = total_amount
    db.session.commit()


def to_month_string(d):
    """Convert date to month string format YYYY-MM"""
    return f"{d.year:04d}-{d.month:02d}"


def update_monthly_material_cost(latest_port, port_number, item_id, handover_date):
    """Update monthly material cost records after handover"""
    from datetime import datetime
    
    # Fetch all port/material rows for this vessel + port
    records = (
        db.session.query(
            Port.port_number,
            Port.total_amount,
            Item.material,
            Port.start_date,
            Material.material_type
        )
        .join(Item, Port.vessel_id == Item.id)
        .join(Material, Item.material == Material.material_name)
        .filter(
            Port.vessel_id == item_id,
            Port.port_number == port_number
        )
        .all()
    )

    if not records:
        return

    print("--------------- MONTHLY COST (RAW RECORDS) ----------------")
    print(records)

    earliest_start_date = min(record[3] for record in records)
    print("EARLIEST DATE USED FOR ALL:", earliest_start_date)

    aggregated = defaultdict(float)

    for pn, amount, material_name, start_date, material_type in records:
        # Every item forced to use earliest date (fully dynamic)
        key = (pn, material_type, earliest_start_date)
        aggregated[key] += amount

    print("AGGREGATED:", aggregated)

    # Insert/update database
    for key, total_amount in aggregated.items():
        pn, material_type, fixed_start_date = key
        month_key = to_month_string(fixed_start_date)

        existing = MaterialRecord.query.filter_by(
            port_id=latest_port.id,
            port_number=pn,
            month=month_key,
            material=material_type
        ).first()

        if existing:
            existing.total_amount = total_amount
        else:
            new_record = MaterialRecord(
                port_id=latest_port.id,
                port_number=pn,
                month=month_key,
                material=material_type,
                total_amount=total_amount
            )
            db.session.add(new_record)
    db.session.commit()
