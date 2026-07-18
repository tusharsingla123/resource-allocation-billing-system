from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, timedelta
from flask_migrate import Migrate
from sqlalchemy.sql import func
from collections import defaultdict
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from functools import wraps
from sqlalchemy import select, event, Engine

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///port2.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
app.secret_key = 'ysecret-key-12'
#######

app.permanent_session_lifetime = timedelta(minutes=10)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'
login_manager.session_protection = 'strong'


# -------------- Database Models -----------------

class Item(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.String())
    vessel_name = db.Column(db.String())
    purchase_order = db.Column(db.Integer())
    volume_port = db.Column(db.Float())  # Port volume field
    volume_bl = db.Column(db.Float())
    ports = db.relationship('Port', backref='vessel', lazy=True)

class Port(db.Model):  
    id = db.Column(db.Integer, primary_key=True)
    port_number = db.Column(db.String())
    sqm_covered = db.Column(db.Float())
    allotment_number = db.Column(db.Integer())  # 1, 2, 3, or 4+
    days_allocated = db.Column(db.Integer())
    penalty_per_day = db.Column(db.Float())
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date())
    handover = db.Column(db.Boolean(), default=False)
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

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError("Username already exists. Please choose a different one.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                                       render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                                       render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class Stock(db.Model):
    __tablename__ = 'stock_info'
    id = db.Column(db.Integer, primary_key=True)
    Month = db.Column(db.String(7), nullable=False)   
    Stock = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Stock id={self.id}, Month='{self.Month}', Stock={self.Stock}>"





# -------------- Routes -----------------
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        resp = make_response(view(*args, **kwargs))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return no_cache


# -------- LOGIN MANAGER -------- #
@login_manager.user_loader
def load_user(user_id):
    # First try normal users
    user = User.query.get(int(user_id))
    if user:
        return user
    # Then try admins
    admin = Admin.query.get(int(user_id))
    if admin:
        return admin
    return None


# -------- ROUTES -------- #
@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_page'))

    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "No JSON received"}), 400

    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    # Check Admin first
    admin = Admin.query.filter_by(username=email).first()
    if admin and check_password_hash(admin.password_hash, password):
        login_user(admin)
        return jsonify({"success": True, "redirect": url_for("admin_dashboard")}), 200

    # Check normal user
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if not user.approved:
        return jsonify({"success": False, "message": "Account pending approval"}), 403
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Incorrect password"}), 401

    login_user(user)
    return jsonify({"success": True, "redirect": url_for("home_page")}), 200



@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Only allow Admin users
    if not isinstance(current_user, Admin):
        abort(403, description="Unauthorized: Admins only")
    return render_template('admin.html')



@app.route("/admin/get_users")
@login_required
def get_users():
    # Only admins can access
    if not isinstance(current_user, Admin):
        return jsonify({"error": "Unauthorized: Admins only"}), 403

    users = User.query.all()
    user_list = [
        {
            "id": u.id,
            "email": u.email,
            "approved": bool(u.approved)
        }
        for u in users
    ]
    return jsonify(user_list)


@app.route("/admin/toggle_approval/<int:user_id>", methods=["POST"])
@login_required
def toggle_approval(user_id):
    # Only admins can access
    if not isinstance(current_user, Admin):
        return jsonify({"error": "Unauthorized: Admins only"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Toggle approval
    user.approved = not user.approved
    db.session.commit()

    return jsonify({"success": True, "approved": user.approved})

@app.route('/session_check')
def session_check():
    return jsonify({"authenticated": current_user.is_authenticated})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "No data"}), 400

    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 400

    # Hash password
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create user with approved = False
    user = User(
        email=email,
        password=hashed_pw,
        approved=False       
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Registration successful! Wait for Admin Approval to login."
    }), 200




# ------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    session.clear()
    resp = redirect(url_for('login'))
    resp.headers['Cache-Control'] = 'no-store'
    return resp



@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


####### business logic##########
@app.route('/home')
@login_required
@nocache
def home_page():
    import statistics
    if current_user.is_authenticated:
        pass
    elif session.get("admin_id"):
        pass
    else:
        return redirect(url_for("login")) 
    
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


    ## total cost (ls + coal)
    # total_amount=[]
    # total_month = []


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
    
    ## fetch from stock_info table match the month append the month 
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

    # Example: print
    # for row in merged_data:
    #     print(f"Month: {row['month']}, Stock: {row['stock']}, Total Amount: {row['total_amount']}")

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


@app.route('/add-vessel', methods=['GET', 'POST'])
@login_required
@nocache
def add_vessel():
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
        volume_port = float(request.form.get('volume-port') or 0)
        volume_bl = float(request.form.get('volume_bl') or 0)
        port_numbers = request.form.getlist('port_numbers')
        start_date = request.form.get('start_date')
        purchase_order = request.form.get('purchase_order')


        new_item = Item(
            material=material,
            vessel_name=vessel_name,
            purchase_order=purchase_order,
            volume_port=volume_port,
            volume_bl=volume_bl
        )
        db.session.add(new_item)
        db.session.commit()

        from datetime import datetime, timedelta
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
        return redirect(url_for('home_page'))
    return render_template('add_vessel.html', port_areas=port_areas,materials=materials)

@app.route('/edit_vessel/<int:item_id>', methods=['GET','POST'])
@login_required
@nocache
def edit_vessel(item_id):
    vessel = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        vessel.material = request.form.get('material_name')
        vessel.volume_port = float(request.form.get('volume-port') or 0)
        vessel.volume_bl = float(request.form.get('volume-bl') or 0)
        vessel.purchase_order = request.form.get('purchase_order')

        db.session.commit()
        flash('Vessel details updated successfully!', 'success')
        return redirect(url_for('more_info', item_id=item_id))

    return render_template('edit_vessel.html', item=vessel)

@app.template_filter('format_date')
def format_date(value):
    if value is None:
        return ''
    return value.strftime('%d-%m-%Y')

@app.template_filter('currency')
def currency_format(value):
    return "₹ {:,.0f}".format(value)

@app.template_filter('currency_new')
def currency_format(value):
    return "₹ {:,.2f}".format(value)



def compute_totals(ports, filter_handover):
    base = penalty = total = 0
    for port in ports:
        if filter_handover and port.handover:
            continue
        if port.total_amount:
            total += port.total_amount
    return total  # base and penalty not needed in this version


def calculate_port_amounts(item_id):
    item = Item.query.get(item_id)
    gst_rate = TaxRate.query.first().gst / 100
    cgst_rate = TaxRate.query.first().cgst / 100

    new_date = date(2025, 8, 31)
    for port in item.ports:
        port_area = PortArea.query.filter_by(port_number=port.port_number).first()
        print(port_area)
        area = port_area.area if port_area else 0
        print(area)
        kacha = port_area.kacha if port_area else 0
        print(kacha)

        first_start_date = (
            db.session.query(func.min(Port.start_date))
            .filter(Port.allotment_number == port.allotment_number)
            .scalar()
        )


        rate = (
            AllotmentRate.query
            .filter(AllotmentRate.allotment_number == port.allotment_number)
            .filter(AllotmentRate.from_date <= first_start_date)
            .order_by(AllotmentRate.from_date.desc())
            .first()
        )


        if kacha == 0:
            rate_per_sqm = rate.kacha_rate if rate else 0
            print(rate_per_sqm)
            penalty_per_day = rate.kacha_penalty if rate else 0
            print(penalty_per_day)
        else:
            rate_per_sqm = rate.paka_rate if rate else 0
            print(rate_per_sqm)
            penalty_per_day = rate.paka_penalty if rate else 0
            print(penalty_per_day)

        # Decide end reference (handover or ongoing)
        end_reference = port.end_date if port.handover else min(date.today(), port.end_date)

        # === YOUR BUSINESS LOGIC ===
        if port.start_date > new_date and rate.allotment_number != 1:
            base_rate = 0
            print(base_rate)
            # print({base_rate},"> august")
        else:
            # print(area * rate_per_sqm)
            # base_rate = (area * rate_per_sqm) / 10
            base_rate = (area * rate_per_sqm)
            print(base_rate)
            # print(base_rate,"< august")

        days_passed = (end_reference - port.start_date).days + 1
        if days_passed < 0:
            days_passed = 0

        capped_days = min(days_passed, 30)
        # area_10 = round(area / 10, 0)
        area_10 = round(area)
        print(area_10, "area_10")

        print(penalty_per_day,capped_days,area_10,"penalty debugging")

        total_penalty = penalty_per_day * capped_days * area_10
        print(f"{total_penalty} ----> total penalty *****************")
        base_gst = base_rate * gst_rate
        print(base_gst)
        base_cgst = base_rate * cgst_rate
        print(base_cgst)
        penalty_gst = total_penalty * gst_rate
        print(penalty_gst)
        penalty_cgst = total_penalty * cgst_rate
        print(penalty_cgst)
        print("******************************************")
        total_amount = round(
            base_rate + base_gst + base_cgst +
            total_penalty + penalty_gst + penalty_cgst,
            0
        )
        print(total_amount)
        print(f"{total_amount} debugging -->f{base_rate}--> base rate,f{base_gst} --> base gst,f{total_penalty} --> total_penatly,f{penalty_gst} ---> penalty_gst",
              f"{penalty_cgst}----> penalty cgst")

        port.total_amount = total_amount
    db.session.commit()





@app.route('/more-info/<int:item_id>')
@login_required
@nocache
def more_info(item_id):
    item = Item.query.get_or_404(item_id)
    # Always ensure amounts are freshly calculated before displaying
    # Totals
    calculate_port_amounts(item_id)
    grand_total = compute_totals(item.ports, filter_handover=True)
    total_amount_all = compute_totals(item.ports, filter_handover=False)

    tax = TaxRate.query.first()
    gst_rate = tax.gst / 100 if tax else 0.09
    cgst_rate = tax.cgst / 100 if tax else 0.09

    ports = Port.query.filter_by(vessel_id=item_id).all()

    port_data = []
    table_base = 0
    table_penalty = 0
    table_total = 0

    # Recompute display data only (NOT price logic)

    """
    FETCH DATA WRT TO VESSEL ID FROM PORT TABLE 
    PORT TABLE :- 1)HOLD THE START_DATE OF THE FIRST ALLOMENT AND ITS ALLOMENT NUMBER 
                  2)FOR NEXT ALLOTMENT NUMBER SEE THE VESSEL ID & EXTRACT THE ALLOTMENT NUMBER 
                    & REFER THE FIRST START DATE AND EXTRACT THAT RATE FROM THE ALLOTMENT TABLE 
                    KEEPING THE DATE OF FIRST ALLOMENT BUT RATES WRT RESPECT TO ALLOMENT NUMBER 

    """

    for port in ports:
        port_area = PortArea.query.filter_by(port_number=port.port_number).first()
        area = port_area.area if port_area else 0
        kacha = port_area.kacha if port_area else 0

        first_start_date = (
            db.session.query(func.min(Port.start_date))
            .filter(Port.allotment_number == port.allotment_number)
            .scalar()
        )

        rate = (
            AllotmentRate.query
            .filter(AllotmentRate.allotment_number == port.allotment_number)
            .filter(AllotmentRate.from_date <= first_start_date)
            .order_by(AllotmentRate.from_date.desc())
            .first()
        )

        ### CHANGE HERE IN RATE
        # print(rate)

        if kacha == 0:
            rate_per_sqm = rate.kacha_rate if rate else 0
            print(rate_per_sqm)
            penalty_per_day = rate.kacha_penalty if rate else 0
            print(penalty_per_day)
        else:
            rate_per_sqm = rate.paka_rate if rate else 0
            penalty_per_day = rate.paka_penalty if rate else 0
            print(penalty_per_day)

        # Base rate was already calculated inside calculate_port_amounts()
        new_date = date(2025, 8, 31)
        if port.start_date > new_date and rate.allotment_number != 1:
            base_rate = 0
        else:
           # base_rate = (area * rate_per_sqm) / 10
           base_rate = (area * rate_per_sqm)

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
            'total_amount': port.total_amount  
        })

        table_base += base_rate
        table_penalty += total_penalty
        table_total += port.total_amount
    print(port_data)

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


@app.route('/add-port/<int:item_id>', methods=['GET', 'POST'])
@login_required
@nocache
def add_port(item_id):
    item = Item.query.get_or_404(item_id)
    # Get only ports that are not already allotted (no active, non-handover entries)
    assigned_port_numbers = [p.port_number for p in Port.query.with_entities(Port.port_number).filter_by(vessel_id=item.id).all()]
    port_areas = PortArea.query.filter(~PortArea.port_number.in_(assigned_port_numbers)).all()

    if request.method == 'POST':
        selected_ports = request.form.getlist('port_numbers')
        start_date_str = request.form['f-date']
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=29)
        allotment_number = 1
        days_allocated = 30

        for port_number in selected_ports:
            port_area_entry = PortArea.query.filter_by(port_number=port_number).first()
            sqm_covered = port_area_entry.area if port_area_entry else 0
            kacha = port_area_entry.kacha if port_area_entry else 0

            rate_entry = AllotmentRate.query.filter_by(allotment_number=allotment_number).first()
            penalty = rate_entry.kacha_penalty if kacha == 0 else rate_entry.paka_penalty

            new_port = Port(
                port_number=port_number,
                sqm_covered=sqm_covered,
                allotment_number=allotment_number,
                days_allocated=days_allocated,
                penalty_per_day=penalty,
                start_date=start_date,
                end_date=end_date,
                vessel_id=item.id
            )
            db.session.add(new_port)

        db.session.commit()
        return redirect(url_for('more_info', item_id=item.id))
    return render_template('add_port.html', item=item, port_areas=port_areas)



@app.route('/next-allotment-port/<int:port_id>/<int:item_id>')
@login_required
@nocache
#### new logic
def next_allotment_port(port_id, item_id):
    port = Port.query.get_or_404(port_id)
    new_allotment_number = port.allotment_number + 1 if port.allotment_number < 4 else 4
    rate_entry = AllotmentRate.query.filter_by(allotment_number=new_allotment_number).first()
    port_area = PortArea.query.filter_by(port_number=port.port_number).first()
    kacha = port_area.kacha if port_area else 0

    # Calculate new penalty
    if kacha == 0:
        penalty_per_day = rate_entry.kacha_penalty if rate_entry else 0
        rate_per_sqm = rate_entry.kacha_rate if rate_entry else 0
    else:
        penalty_per_day = rate_entry.paka_penalty if rate_entry else 0
        rate_per_sqm = rate_entry.paka_rate if rate_entry else 0
        
    start_date = port.end_date + timedelta(days=1)
    end_date = start_date + timedelta(days=29)
    
    # Create new Port row
    new_port = Port(
        port_number=port.port_number,
        sqm_covered=port.sqm_covered,
        allotment_number=new_allotment_number,
        days_allocated=port.days_allocated,
        penalty_per_day=port.penalty_per_day,
        start_date = start_date,
        end_date = end_date,
        vessel_id=port.vessel_id
    )

    db.session.add(new_port)
    db.session.commit()
    return redirect(url_for('more_info', item_id=item_id))



@app.route('/all_info')
@login_required
@nocache
def all_info():
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


@app.route('/add-material', methods=['GET', 'POST'])
@login_required
@nocache
def add_material():
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
            return redirect(url_for('all_info'))
    return render_template('add_material.html')



@app.route('/statistics', methods=['GET', 'POST'])
@login_required
@nocache
def statistics():
    selected_year = request.args.get('year', date.today().year, type=int)
    selected_fy_start = request.args.get('year', date.today().year, type=int)

    # Define financial year range
    start_date = date(selected_fy_start, 4, 1)  # April 1, 2025
    end_date = date(selected_fy_start + 1, 3, 31)  # March 31, 2026

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
        return redirect(url_for('statistics', year=selected_fy_start))

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


@app.route('/update-adv-note/<int:port_id>', methods=['POST'])
@login_required
@nocache
def update_adv_note(port_id):
    port = Port.query.get_or_404(port_id)
    adv_penalty = request.form.get('adv_penalty')
    adv_base = request.form.get('adv_base')

    port.adv_penalty_note = datetime.strptime(adv_penalty, '%Y-%m-%d').date() if adv_penalty else None
    port.adv_base_note = datetime.strptime(adv_base, '%Y-%m-%d').date() if adv_base else None
    db.session.commit()
    return redirect(request.referrer or url_for('home_page'))



## utility for handover
def to_month_string(d):
    return f"{d.year:04d}-{d.month:02d}"


def update_monthly_material_cost(latest_port, port_number, item_id, handover_date):
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

    # ---------------------------------------------------------
    # STEP 3 — Insert/update database
    # ---------------------------------------------------------
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


@app.route('/handover-port/<port_number>/<int:item_id>', methods=['POST'])
@login_required
@nocache
def handover_port(port_number, item_id):
    print("------------------handover logic 1-------------------------")

    handover_date_str = request.form.get("handover_date")
    try:
        handover_date = datetime.strptime(handover_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        flash("Invalid handover date format", "danger")
        return redirect(url_for('more_info', item_id=item_id))

    latest_port = (
        Port.query
        .filter_by(port_number=port_number, vessel_id=item_id)
        .order_by(Port.id.desc())
        .first()
    )

    if latest_port:
        latest_port.end_date = handover_date
        latest_port.handover = True

        ports = Port.query.filter_by(vessel_id=item_id, port_number=port_number).all()
        for port in ports:
            port.handover = True
        db.session.commit()   

        calculate_port_amounts(item_id)
        update_monthly_material_cost(latest_port, port_number, item_id, handover_date)

    return redirect(url_for('more_info', item_id=item_id))


@app.route('/edit-allotment-rate/<int:rate_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_allotment_rate(rate_id):
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
        return redirect(url_for('all_info'))
    return render_template('edit_allotment_rate.html', rate=rate)


@app.route('/edit-tax-rate/<int:tax_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_tax_rate(tax_id):
    tax = TaxRate.query.get_or_404(tax_id)
    if request.method == 'POST':
        tax.gst = request.form['gst']
        tax.cgst = request.form['cgst']
        tax.from_date = request.form['from_date']
        db.session.commit()
        return redirect(url_for('all_info'))
    return render_template('edit_tax_rate.html', tax=tax)



@app.route('/edit_material/<int:material_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    if request.method == 'POST':
        material.material_id = request.form['material_id']
        material.material = request.form['material_name']
        db.session.commit()
        return redirect(url_for('all_info'))
    return render_template('edit_material.html', material=material)


@app.route('/edit-port-area/<int:port_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_port_area(port_id):
    port = PortArea.query.get_or_404(port_id)
    if request.method == 'POST':
        port.area = float(request.form['area'])  # Make sure this is float
        port.kacha = request.form['kacha'] == '1'  # Converts '1' → True, '0' → False
        from_date_str = request.form['from_date']
        if from_date_str:
            port.from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        db.session.commit()
        return redirect(url_for('all_info'))
    return render_template('edit_port_area.html', port=port)




@app.route('/edit-port/<int:port_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_port(port_id):
    port = Port.query.get_or_404(port_id)
    if request.method == 'POST':
        from datetime import datetime
        port.port_number = request.form['port_number']  # Now editable
        port.allotment_number = request.form['allotment_number']
        port.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        port.end_date = port.start_date+timedelta(29)
        port.days_allocated = 30
        db.session.commit()
        return redirect(url_for('more_info', item_id=port.vessel_id))

    return render_template('edit_port.html', port=port)



@app.route('/port-status')
@login_required
@nocache
def port_status():
    all_ports = PortArea.query.all()
    port_entries = Port.query.all()
    port_stats = defaultdict(lambda: {
        'area': 0,
        'surface': 'Kacha',
        'status': 'Available',
        'days_passed': 0,
        'allotments': 0,
        'vessel_name': '',
        'material': ''
    })

    first_allotment_map = {}
    latest_port_map = {}

    for entry in port_entries:
        port_number = entry.port_number
        port_stats[port_number]['status'] = "Allotted" if not entry.handover else "Available"
        port_stats[port_number]['allotments'] += 1

        # Track the earliest start date per port
        if port_number not in first_allotment_map or entry.start_date < first_allotment_map[port_number]:
            first_allotment_map[port_number] = entry.start_date

        # Track latest entry per port for material/vessel
        if port_number not in latest_port_map or entry.start_date > latest_port_map[port_number].start_date:
            latest_port_map[port_number] = entry

    for port in all_ports:
        port_number = port.port_number
        port_stats[port_number]['area'] = port.area
        port_stats[port_number]['surface'] = "Platform" if port.kacha else "Kacha"

        # Get the days passed from first allotment to today
        if port_number in first_allotment_map:
            delta_days = (date.today() - first_allotment_map[port_number]).days
            port_stats[port_number]['days_passed'] = max(0, delta_days)

        if port_number in latest_port_map:
            latest_entry = latest_port_map[port_number]
            port_stats[port_number]['vessel_name'] = latest_entry.vessel.vessel_name
            port_stats[port_number]['material'] = latest_entry.vessel.material

    ports_list = [{
        'port_number': p,
        'area': data['area'],
        'surface': data['surface'],
        'status': data['status'],
        'days_passed': data['days_passed'],
        'allotments': data['allotments'],
        'vessel_name': data['vessel_name'],
        'material': data['material']
    } for p, data in port_stats.items()]

    # Normalize for gradient coloring
    max_days = max([p['days_passed'] for p in ports_list], default=1)
    min_days = min([p['days_passed'] for p in ports_list], default=0)

    def calculate_color(days):
        ratio = (days - min_days) / (max_days - min_days + 1e-5)
        r = int(255 * ratio) - 50
        g = int(255 * (1 - ratio) - 30)
        return f'rgb({r}, {g}, 50)'

    for port in ports_list:
        port['color'] = calculate_color(port['days_passed'])

    ports_list.sort(key=lambda x: x['days_passed'], reverse=True)
    return render_template("port_status.html", ports=ports_list)

def get_ports_nearing_end(days_notice=3):
    today = date.today()
    notice_date = today + timedelta(days=days_notice)
    # Find ports where end date is within the next X days
    ports_due = Port.query.filter(
        Port.end_date <= notice_date,
        Port.end_date >= today
    ).all()

    return ports_due

@app.route('/notifications')
@login_required
@nocache
def notifications():
    due_ports = get_ports_nearing_end()
    return render_template('notifications.html', ports=due_ports)

@app.context_processor
def inject_due_ports():
    today = date.today()
    upcoming = today + timedelta(days=5)
    due_ports = Port.query.filter(
        Port.end_date <= upcoming,
        Port.end_date >= today
    ).all()
    return dict(due_ports=due_ports)

@app.route('/export-vessel/<int:item_id>')
@login_required
@nocache
def export_vessel(item_id):
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

@app.route('/export-all-vessels')
@login_required
@nocache
def export_all_vessels():
    items = Item.query.all()

    vessel_data = []
    port_data = []

    for item in items:
        vessel_data.append({
            'Vessel ID': item.id,
            'Material': item.material,
            'Vessel Name': item.vessel_name,
            'Purchase Order': item.purchase_order,
            'Volume Port (tons)': item.volume_port,
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
    return send_file(output, download_name="vessels_info.xlsx", as_attachment=True)



@app.route('/delete-vessel/<int:item_id>', methods=['POST'])
@login_required
@nocache
def delete_vessel(item_id):
    vessel = Item.query.get_or_404(item_id)
    # Delete associated ports first
    for port in vessel.ports:
        db.session.delete(port)
    db.session.delete(vessel)
    db.session.commit()
    return redirect(url_for('home_page'))


#port_number
@app.route('/delete-port/<int:port_id>/<int:item_id>', methods=['POST'])
@login_required
@nocache
def delete_port(port_id,item_id):
    port = Port.query.get_or_404(port_id)
    db.session.delete(port)
    deleted_port_number = port.port_number
    # print(deleted_port_number)
    handover_reset = Port.query.filter_by(port_number=deleted_port_number,vessel_id=item_id).all()
    # print(handover_reset)
    # print(port_id)
    for port in handover_reset:
        port.handover = False   # or whatever field you want
    db.session.commit()
    return redirect(url_for('more_info', item_id=item_id))


@app.route('/delete-allotment-rate/<int:rate_id>', methods=['POST'])
@login_required
@nocache
def delete_allotment_rate(rate_id):
    rate = AllotmentRate.query.get_or_404(rate_id)
    db.session.delete(rate)
    db.session.commit()
    return redirect(url_for('all_info'))

@app.route('/delete-tax-rate/<int:tax_id>', methods=['POST'])
@login_required
@nocache
def delete_tax_rate(tax_id):
    tax = TaxRate.query.get_or_404(tax_id)
    db.session.delete(tax)
    db.session.commit()
    return redirect(url_for('all_info'))

@app.route('/delete_material/<int:material_id>', methods=['POST'])
@login_required
@nocache
def delete_material(material_id):
    material =  Material.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('all_info'))

@app.route('/delete-port-area/<int:port_id>', methods=['POST'])
@login_required
@nocache
def delete_port_area(port_id):
    port = PortArea.query.get_or_404(port_id)
    db.session.delete(port)
    db.session.commit()
    return redirect(url_for('all_info'))

@app.route('/add-allotment-rate', methods=['GET', 'POST'])
@login_required
@nocache
def add_allotment_rate():
    if request.method == 'POST':
        from datetime import datetime
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
        return redirect(url_for('all_info'))

    return render_template('add_allotment_rate.html')

@app.route('/add-port-area', methods=['GET', 'POST'])
@login_required
@nocache
def add_port_area():
    if request.method == 'POST':
        new_port = PortArea(
            port_number=request.form['port_number'],
            area=request.form['area'],
            kacha=True if request.form['kacha'] == '1' else False
        )
        db.session.add(new_port)
        db.session.commit()
        return redirect(url_for('all_info'))
    return render_template('add_port_area.html')


@app.route('/add-stock', methods=['GET','POST'])
@login_required
@nocache
def add_stock():
    if request.method == 'POST':
        new_stock = Stock(
            Month = request.form.get('month'),   # lowercase from form
            Stock = request.form.get('stock')
        )
        db.session.add(new_stock)
        db.session.commit()
        return redirect(url_for('all_info'))
        
    return render_template('add_stock_data.html')


@app.route('/edit-stock-rate/<int:stock_id>', methods=['GET', 'POST'])
@login_required
@nocache
def edit_stock_rate(stock_id):
    stock = Stock.query.get_or_404(stock_id)   
    if request.method == 'POST':
        stock.Month = request.form.get('month')   
        stock.Stock = request.form.get('stock')
        db.session.commit()
        return redirect(url_for('all_info'))
    return render_template('edit_stock_data.html', stock=stock)


@app.route('/delete_stock/<int:stock_id>', methods=['POST'])
@login_required
@nocache
def delete_stock_rate(stock_id):
    stock = Stock.query.get_or_404(stock_id)  
    db.session.delete(stock)                   
    db.session.commit()
    return redirect(url_for('all_info'))



########### STOCK ADD & EDIT & DELETE #######

if __name__ == '__main__':
    app.run(debug=True)
