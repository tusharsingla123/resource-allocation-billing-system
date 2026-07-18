from app2 import app, db, Item, Port, PortArea, AllotmentRate,TaxRate

with app.app_context():
    print("\n--- ITEM TABLE ---")
    items = Item.query.all()
    for item in items:
        print(vars(item))
    
    print("\n--- ALLOTMENT RATE TABLE ---")
    rate = AllotmentRate.query.all()
    for rate in rate:
        print(vars(rate))
    
    
    print("\n--- PORT TABLE ---")
    ports = Port.query.filter_by(port_number="P16")
    for port in ports:
        print(vars(port))
        
    print("\n--- TAX TABLE ---")
    taxs = TaxRate.query.all()
    for tax in taxs:
        print(vars(tax))

print("Data viewed successfully.")


