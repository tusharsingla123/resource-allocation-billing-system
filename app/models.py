from app import db
from flask_login import UserMixin
from datetime import datetime

# -------------- Database Models -----------------

class Item(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.String())
    vessel_name = db.Column(db.String())
    purchase_order = db.Column(db.Integer())
    volume_demo_port = db.Column(db.Float())
    volume_bl = db.Column(db.Float())
    ports = db.relationship('Port', backref='vessel', lazy=True)

class Port(db.Model):  
    id = db.Column(db.Integer, primary_key=True)
    port_number = db.Column(db.String())
    sqm_covered = db.Column(db.Float())
    allotment_number = db.Column(db.Integer())  # 1, 2, 3, or 4+
    days_allocated = db.Column(db.Integer())
    penalty_per_day = db.Column(db.Float())
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    handover=db.Column(db.Boolean(),default=False)
    total_amount = db.Column(db.Float())
    adv_penalty_note = db.Column(db.Date(), nullable=True)
    adv_base_note = db.Column(db.Date(), nullable=True)
    vessel_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)

class PortArea(db.Model):  # Static table for port number → area
    id = db.Column(db.Integer, primary_key=True)
    port_number = db.Column(db.String(), unique=True)
    area = db.Column(db.Float())
    kacha = db.Column(db.Boolean(), default=False)
    from_date = db.Column(db.Date)  # Effective date

class AllotmentRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    allotment_number = db.Column(db.Integer()) 
    kacha_rate = db.Column(db.Float())    
    paka_rate = db.Column(db.Float())          
    kacha_penalty = db.Column(db.Float())      
    paka_penalty = db.Column(db.Float())   
    from_date = db.Column(db.Date)  # Effective date
       
class TaxRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gst = db.Column(db.Float())     
    cgst = db.Column(db.Float())   
    from_date = db.Column(db.Date)  # Effective date 
    
class MonthlyStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String())          
    year = db.Column(db.Integer())
    total_tonnage = db.Column(db.Float())
    cost_per_ton=db.Column(db.Float())

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer)
    material_type = db.Column(db.String(20))
    material_name = db.Column(db.String(20))

class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    approved = db.Column(db.Boolean, default=False)

class Admin(db.Model, UserMixin):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class MaterialRecord(db.Model):
    __tablename__ = 'monthly_handover_totals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    port_number = db.Column(db.String(20))
    month = db.Column(db.String(7), nullable=False)
    material = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Link to Port with cascading delete
    port_id = db.Column(db.Integer, db.ForeignKey('port.id', ondelete='CASCADE'))
    port = db.relationship('Port', backref=db.backref('monthly_records', passive_deletes=True))


class Stock(db.Model):
    __tablename__ = 'stock_info'
    id = db.Column(db.Integer, primary_key=True)
    Month = db.Column(db.String(7), nullable=False)   
    Stock = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Stock id={self.id}, Month='{self.Month}', Stock={self.Stock}>"
