# Resource Allocation Billing System

**Project Description**

Resource Allocation Billing System is a full-stack Python Flask web application designed to streamline port logistics, vessel scheduling, and billing allotments for maritime cargo. It allows administrators to register and manage vessels, assign and track plot (port yard) rentals, compute active and historic rental fees (incorporating penalty tariffs and tax rates), and visualize volume metrics. The application provides complete CRUD (Create, Read, Update, Delete) capabilities, data exports to Excel, and interactive analytics dashboards.

---

**Technical Decisions and Overview**

### **Frontend**
* **Template Engine**: Jinja2 templates (extending a unified base layout) integrated with Bootstrap 4.5 and custom CSS for a highly responsive, clean dashboard UI.
* **Modern Typography**: Integrated **Inter** Google Font globally for a sleek, premium, enterprise-ready look.
* **Data Visualization**: Uses **Chart.js** to generate interactive charts detailing Cost per Ton, Vessel Turnaround Times, Material Volumes, and Monthly Rent Overviews.
* **Micro-Animations**: Custom `@keyframes fadeInUp` transition animations added globally for fluid entrance animations of dashboard elements.
* **Aesthetics**: Glassmorphism login panel overlaying abstract gradient waves with matching brand-themed badge styles.

### **Backend**
* **Framework**: Python 3.14+ with **Flask** using the **Application Factory Pattern** and modular Flask **Blueprints** (Auth, Vessels, Ports, Config, Statistics, Notifications) for clean separation of concerns.
* **ORM**: **Flask-SQLAlchemy** for mapping Python object models to database tables and managing relations cleanly.
* **Security & Authentication**: **Flask-Login** for user session tracking, password hashing using **Flask-Bcrypt**, and registration validation limited to valid corporate domains (e.g., `@demochemicals.com`).
* **Migrations**: **Flask-Migrate** (based on Alembic) to manage schema updates and track database modifications.

### **Data Management**
* **Database**: SQLite database stored locally at `instance/port2.db` with auto-calculating schemas for base allotment rates and penalty timelines.
* **Business Logic**: Automated tariff pricing utility that calculates base rent and calculates dynamic penalty fees when a vessel exceeds its allotted 30-day plot rental threshold.
* **Excel Reports**: **Pandas** paired with the **XlsxWriter** engine to compile and export custom Excel worksheets (`vessels_info.xlsx` and individual vessel allotment spreadsheets) directly from SQL query dataframes.

---

**Setup Instructions**

### **Prerequisites**
* Python 3.12 or newer
* pip (Python package installer)

### **Installation & Configuration**

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Tushar/demo-port-plot-management.git
   cd demo-port-plot-management
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize and Seed the Database**
   Runs migrations, creates database tables, seeds initial allotment rates/materials, and prompts to create the administrator account:
   ```bash
   python3 init_db.py
   ```
   * Default admin setup credentials:
     * **Email**: `admin@demochemicals.com`
     * **Password**: `SCM1233@`

5. **Start the Development Server**
   ```bash
   python3 run.py
   ```
   * The application runs locally at: **[http://127.0.0.1:5001](http://127.0.0.1:5001)**

---

**Project Structure**

```text
├── app/
│   ├── routes/              # Modular Blueprints (Controllers)
│   │   ├── auth.py          # User registration, login, and dashboard approvals
│   │   ├── vessels.py       # Vessel registration, editing, deleting, and exports
│   │   ├── ports.py         # Plot allotments, handovers, next allotment triggers
│   │   ├── config.py        # Allotment rates, surface area, and tax configurations
│   │   ├── statistics.py    # Monthly statistics updates
│   │   └── notifications.py # Deadline calculations and warnings
│   ├── utils/               # Business logic helpers
│   │   ├── calculations.py  # Pricing and penalty engine
│   │   ├── decorators.py    # Cache blocking and security decorators
│   │   └── helpers.py       # Helper functions
│   ├── templates/           # Application-specific layouts (see note below)
│   ├── config.py            # Development and Production Flask configurations
│   ├── forms.py             # Form definitions & validation rules
│   ├── models.py            # SQLAlchemy Database Schemas (Item, Port, User, etc.)
│   └── __init__.py          # Application Factory Setup
├── static/                  # Shared CSS, JavaScript, and company branding images
├── templates/               # Jinja2 templates (Login, Dashboard, Vessels, Stats)
├── instance/                # SQLite local DB file (port2.db)
├── init_db.py               # Database seeding and admin creator script
├── run.py                   # Main Flask launcher
└── requirements.txt         # Package dependencies file
```

---

**Running Tests**

* API endpoints can be tested manually using tools like **Postman** or **Thunder Client**.
* Database integrity and query outputs can be verified by running the local data utility tool:
  ```bash
  python3 data.py
  ```

---

**Features**

* **User Registration & Security**: Corporate validation for `@demochemicals.com` email handles and security pattern checks on password creation.
* **KPI Analytics Dashboard**: Top-level real-time indicators tracking total cargo vessels, active plots, and completed cargo handovers.
* **Dynamic Charting Carousel**: Slide-navigable analytics detailing vessel cost-per-ton ratios, turnaround durations, and monthly billing totals.
* **Visual Status Indicators**: Color-coded badges and pills mapping out materials, plot listings, and current handover stages.
* **Calculations Engine**: Dynamic rate and penalty updates utilizing allotment time bounds.
* **Interactive Grid Operations**: Full CRUD functionalities on vessels, active yards, allotment rates, materials, and tax rates.
* **Excel Reports Generation**: Fast binary file downloads matching the current layout of the tables.

---

**Future Enhancements**

* **Email & SMS Notifications**: Send alerts to shipping operators when plot occupancy is nearing its 30-day billing limit.
* **Role-Based Access Control (RBAC)**: Expand permissions levels to distinguish between guest viewers, port operators, and financial auditing managers.
* **Geo-location Plot Map**: Interactive interactive SVG or Leaflet map showing real-time yard status visually.
* **Multi-Currency Converter**: Support billing reports in USD, EUR, and other global currencies for international clients.
* **Archival System**: Automatic soft-deletes and backups of historical databases.
