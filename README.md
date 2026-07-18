# Resource Allocation Billing System

**Project Description**

The Resource Allocation Billing System is a web application designed to manage the allocation of resources such as plots, yard spaces, or operational areas. It helps users assign resources, track allocation periods, calculate rent, apply penalties, manage tax rates, and generate total payable costs. The system also includes dashboards, charts, notifications, user approval, and Excel export features to support efficient operational and billing management.

**Technical Decisions and Overview**

**Frontend**
- Framework: HTML, CSS, Bootstrap, and Jinja2 templates for server-rendered pages.
- Responsive Design: Bootstrap layout and custom CSS are used to support desktop and smaller screen views.
- User Interface: Provides pages for login, registration, dashboards, resource allocation, billing details, statistics, and admin approval.
- Charts and Analytics: Chart.js is used to display cost-per-ton, turnaround time, monthly cost, stock, and material-based visualizations.
- Form Handling: HTML forms are used for creating, updating, and deleting vessels, plots, rates, materials, tax data, and stock entries.

**Backend**
- Framework: Flask for routing, request handling, authentication flow, and server-side rendering.
- Database ORM: Flask-SQLAlchemy is used to define and manage database models.
- Authentication: Flask-Login and Flask-Bcrypt are used for login sessions and password hashing.
- Database Migration: Flask-Migrate and Alembic are used to manage database schema changes.
- API Endpoints: Includes JSON endpoints for login, registration, session checking, admin user approval, and CRUD operations.
- Error Handling: Uses validation checks, redirects, flash messages, and HTTP error responses for restricted admin access.

**Data Management**
- Database: SQLite is used for local data storage.
- CRUD Operations: Supports creating, reading, updating, and deleting resources, vessels, allotment rates, tax rates, materials, stock records, and port/plot data.
- Billing Calculation: Calculates base rent, penalties, GST, CGST, and total payable cost for each allocated resource.
- Allocation Tracking: Tracks start date, end date, allotment number, handover status, and advance note dates.
- Reporting: Supports Excel export for vessel-wise and complete allocation data.

**Setup Instructions**

**Prerequisites**
- Python 3.10 or higher
- pip
- SQLite

**Installation**
- Clone the Repository
  ```bash
  git clone https://github.com/your-username/resource-allocation-billing-system.git
  cd resource-allocation-billing-system
  ```

- Go to the Flask project folder
  ```bash
  cd tushar
  ```

- Create and activate a virtual environment
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```

- Install dependencies
  ```bash
  pip install -r requirements.txt
  ```

- Configure environment variables
  ```bash
  set FLASK_APP=run.py
  set FLASK_ENV=development
  ```

- Run database migrations, if needed
  ```bash
  flask db upgrade
  ```

- Run the application
  ```bash
  python run.py
  ```

- Open the application
  ```bash
  http://localhost:5000
  ```

**Project Structure**

**Backend**
- `tushar/run.py`: Main application entry point.
- `tushar/app/__init__.py`: Flask application factory and extension setup.
- `tushar/app/config.py`: Application configuration.
- `tushar/app/models.py`: SQLAlchemy database models.
- `tushar/app/routes/`: Blueprint-based route modules.
- `tushar/app/utils/`: Utility functions for calculations, helpers, and decorators.
- `tushar/migrations/`: Alembic migration files.

**Frontend**
- `tushar/templates/base.html`: Main layout and navigation.
- `tushar/templates/login.html`: Login and registration page.
- `tushar/templates/home.html`: Dashboard with charts and vessel/resource list.
- `tushar/templates/more_info.html`: Detailed allocation and billing view.
- `tushar/templates/all_info.html`: Master data management for rates, plots, materials, tax, and stock.
- `tushar/templates/statistics.html`: Monthly financial statistics.
- `tushar/templates/port_status.html`: Visual resource status overview.
- `tushar/static/`: Images and JavaScript assets.

**Running Tests**
- Manual testing can be done through the browser by adding, editing, deleting, and handing over allocated resources.
- API and form endpoints can be tested using Postman, Thunder Client, or browser developer tools.
- Recommended flows to test:
  - User registration and login.
  - Admin approval toggle.
  - Add vessel/resource allocation.
  - Add next allotment.
  - Handover resource.
  - Verify rent, penalty, tax, and total cost calculations.
  - Export data to Excel.

**Features**
- User Registration: Users can register and wait for admin approval.
- Admin Approval: Admin can activate or deactivate user accounts.
- Resource Allocation: Assign one or more resources/plots to a vessel or operational entry.
- Billing Calculation: Calculates base rent, penalty, GST, CGST, and total payable amount.
- Allotment Management: Handles multiple allotment periods and penalty-based extensions.
- Handover Tracking: Tracks resource handover date and updates monthly cost records.
- Master Data Management: Manage resource areas, surface type, materials, tax rates, and allotment rates.
- Notifications: Shows resources nearing allocation end date.
- Dashboard Analytics: Displays charts for cost, vessel turnaround time, material volumes, monthly cost, and stock comparison.
- Excel Export: Export individual and complete allocation data.
- Responsive UI: Uses Bootstrap and custom styling for a clean web interface.
