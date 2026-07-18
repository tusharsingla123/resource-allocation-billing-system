from app2 import app, db, AllotmentRate

with app.app_context():
    rates = [
        AllotmentRate(allotment_number=1, kacha_rate=33.927, paka_rate=67.857, kacha_penalty=0, paka_penalty=0),
        AllotmentRate(allotment_number=2, kacha_rate=42.40875, paka_rate=84.82125, kacha_penalty=2.827, paka_penalty=5.65475),
        AllotmentRate(allotment_number=3, kacha_rate=50.8905, paka_rate=101.7855, kacha_penalty=5.089, paka_penalty=10.17855),
        AllotmentRate(allotment_number=4, kacha_rate=67.854, paka_rate=135.714, kacha_penalty=9.047, paka_penalty=18.0952),
    ]

    for rate in rates:
        db.session.add(rate)

    db.session.commit()

print("✅ Allotment rates inserted successfully.")
