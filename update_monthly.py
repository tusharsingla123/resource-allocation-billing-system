def update_monthly_summary(port_id, handover, end_date, total_amount):
    if handover != 1:
        return

    # Find material from item table
    cursor = db.cursor()
    cursor.execute("SELECT material FROM item WHERE id = %s", (port_id,))
    material = cursor.fetchone()[0]
    year_month = end_date[:7]  # format: YYYY-MM

    # Insert or update monthly summary
    cursor.execute("""
        INSERT INTO monthly_handover_totals (year_month, material, total_amount)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE total_amount = total_amount + VALUES(total_amount)
    """, (year_month, material, total_amount))

    db.commit()


rate = (
        AllotmentRate.query
        .filter(AllotmentRate.allotment_number == port.allotment_number)
        .filter(AllotmentRate.from_date <= port.start_date)
        .order_by(AllotmentRate.from_date.desc())  # latest rate applicable
        .first()
    ) 
print("Monthly summary updated.")