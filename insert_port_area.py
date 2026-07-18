from app2 import db, app
from app2 import Material  # Make sure Material is imported from the correct location

# Define the material names to insert
material_names = [
    "Indo Coal 4800", "SA Coal", "Indo Coal 4100", "Tanzania Coal",
    "Coulambian Coal", "SA 4800", "SA 5500", "Kazak Coal",
    "Limestone", "Coal", "Salt"
]

# Insert materials into the database
with app.app_context():
    for name in material_names:
        material = Material(material_name=name)
        db.session.add(material)

    db.session.commit()

print("✅ All Material data inserted successfully.")
