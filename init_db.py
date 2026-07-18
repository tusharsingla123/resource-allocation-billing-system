"""Initialize the local SQLite database with required tables and an admin user."""
from getpass import getpass

from werkzeug.security import generate_password_hash

from app import db
from app.models import Admin, AllotmentRate, Material, PortArea, TaxRate
from run import app


def seed_master_data():
    if not TaxRate.query.first():
        db.session.add(TaxRate(gst=9.0, cgst=9.0))

    if not AllotmentRate.query.first():
        rates = [
            AllotmentRate(allotment_number=1, kacha_rate=33.927, paka_rate=67.857, kacha_penalty=0, paka_penalty=0),
            AllotmentRate(allotment_number=2, kacha_rate=42.40875, paka_rate=84.82125, kacha_penalty=2.82725, paka_penalty=5.65475),
            AllotmentRate(allotment_number=3, kacha_rate=50.8905, paka_rate=101.7855, kacha_penalty=5.08905, paka_penalty=10.17855),
            AllotmentRate(allotment_number=4, kacha_rate=67.854, paka_rate=135.714, kacha_penalty=9.0472, paka_penalty=18.0952),
        ]
        db.session.add_all(rates)

    if not Material.query.first():
        materials = [
            ("Indo Coal 4800", "Coal"),
            ("SA Coal", "Coal"),
            ("Indo Coal 4100", "Coal"),
            ("Tanzania Coal", "Coal"),
            ("Colombian Coal", "Coal"),
            ("SA 4800", "Coal"),
            ("SA 5500", "Coal"),
            ("Kazak Coal", "Coal"),
            ("Limestone", "Limestone"),
            ("Salt", "Salt"),
        ]
        db.session.add_all(Material(material_name=name, material_type=material_type) for name, material_type in materials)

    if not PortArea.query.first():
        db.session.add_all(
            PortArea(port_number=f"P{i}", area=3000, kacha=True)
            for i in range(1, 21)
        )


def create_admin_user():
    username = input("Admin email: ").strip()
    if not username:
        print("Skipped admin creation.")
        return

    existing_admin = Admin.query.filter_by(username=username).first()
    if existing_admin:
        print("Admin already exists.")
        return

    password = getpass("Admin password: ").strip()
    if not password:
        print("Skipped admin creation because password was empty.")
        return

    admin = Admin(username=username, password_hash=generate_password_hash(password))
    db.session.add(admin)
    print("Admin user created.")


with app.app_context():
    db.create_all()
    seed_master_data()
    create_admin_user()
    db.session.commit()
    print("Database initialized successfully.")
