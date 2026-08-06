# FacuTrack

**Faculty Evaluation and Performance Monitoring System**

FacuTrack is a modern, web-based faculty evaluation system built with Django. It enables anonymous faculty evaluations, generates real-time analytics, rankings, and professional reports for academic institutions.

---

## Features

### Public Features
- **Landing Page** - Beautiful editorial-style landing with animated statistics
- **Anonymous Evaluation** - Students can rate faculty without creating accounts
- **Auto-Save** - Evaluation progress saves automatically via email
- **Receipt Generation** - Unique receipt code (FT-NNNNNN) for tracking submissions

### Admin Dashboard
- **KPI Cards** - Total faculty, departments, rating percentage, daily visitors
- **User Management** - Create, edit, delete users with email credential delivery
- **Department Management** - Organize faculty into departments
- **Questionnaire Management** - Create and manage evaluation questions
- **Faculty Rankings** - Percentage-based rankings with department filters
- **Report Generation** - Export to PDF, Excel, CSV, and Word formats
- **System Logs** - Real-time activity monitoring with search and filters
- **Analytics Hub** - AI insights, department comparison, predictive analytics

### Faculty Dashboard
- **Personal Dashboard** - Rank, rating percentage, total evaluations
- **Performance Status** - Pass/Fail indicator (≥60% = Passed)
- **Feedback History** - View all received evaluations
- **Trend Analysis** - 6-month historical data with forecasting
- **Settings** - Profile editing and password management

### Advanced Analytics
- **AI Performance Insights** - Strengths, weaknesses, recommendations per faculty
- **Department Comparison** - Radar, bar, and pie charts with rankings
- **Predictive Analytics** - 3-month ahead forecasting using linear regression

---

## Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Django 5.2 |
| **Database** | SQLite |
| **Frontend** | HTML5, CSS3, Bootstrap 5 |
| **Charts** | Chart.js |
| **Animations** | AOS (Animate on Scroll) |
| **Icons** | Bootstrap Icons |
| **Fonts** | Fraunces (serif), Inter (sans-serif) |
| **PDF Reports** | ReportLab |
| **Excel Reports** | OpenPyXL |
| **Word Reports** | python-docx |
| **Email** | Django SMTP |

---

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Step 1: Clone or Download
```bash
git clone https://github.com/jose012324/facutrack.git
cd facutrack
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```
### if you want pre example data
```bash
python seed.py
```

### Step 5: Create Superuser (Admin) THIS IS FOR MANUAL ONLY
```bash
python manage.py createsuperuser
```
Follow the prompts to create an admin account.

### Step 6: Run Development Server
```bash
python manage.py runserver
```

Access the application at: **http://127.0.0.1:8000/**

---

## Usage Guide

### For Administrators

1. **Login** at `/login/` with your admin credentials
2. **Dashboard** - View KPIs, charts, and recent activities
3. **User Management** - Create faculty accounts (credentials emailed automatically)
4. **Departments** - Organize users into departments
5. **Questionnaires** - Add evaluation questions (5-point Likert scale)
6. **Rankings** - View faculty performance rankings
7. **Reports** - Generate and download reports in PDF/Excel/CSV/Word
8. **Analytics** - Access AI insights, department comparisons, and predictions

### For Faculty/Staff

1. **Login** at `/login/` with credentials provided by admin
2. **Dashboard** - View your rank, rating, and performance status
3. **Feedback** - Browse all evaluations you've received
4. **Settings** - Update profile information and change password

### For Students (Public)

1. **Visit** the landing page at `/`
2. **Click** "Evaluate Now" or navigate to `/rate/`
3. **Select** department and faculty
4. **Answer** all questionnaire questions (1-5 scale)
5. **Submit** and receive your receipt code

---

## Project Structure

```
facutrack/
├── facutrack/                    # Django project settings
│   ├── __init__.py
│   ├── settings.py              # Main configuration
│   ├── urls.py                  # Root URL configuration
│   ├── asgi.py                  # ASGI entry point
│   └── wsgi.py                  # WSGI entry point
│
├── facutrack_app/               # Main application
│   ├── __init__.py
│   ├── models.py                # Database models (10 tables)
│   ├── views.py                 # All view functions
│   ├── urls.py                  # App URL patterns
│   ├── forms.py                 # Django forms
│   ├── admin.py                 # Django admin configuration
│   ├── analytics.py             # Analytics engine
│   ├── ai_insights.py           # AI insights and predictions
│   ├── reports.py               # Report generation (PDF/Excel/CSV/Word)
│   ├── security.py              # Security middleware and throttling
│   ├── middleware.py             # Visitor tracking middleware
│   ├── decorators.py            # Role-based access decorators
│   ├── context_processors.py    # Global template context
│   ├── apps.py                  # App configuration
│   ├── tests.py                 # Test cases
│   └── migrations/              # Database migrations
│
├── templates/                   # HTML templates
│   ├── base.html                # Master layout
│   ├── ADMIN/                   # Admin templates
│   │   ├── admin_base.html      # Admin shell (sidebar + main)
│   │   ├── _sidebar.html        # Sidebar navigation
│   │   ├── dashboard.html       # Admin dashboard
│   │   ├── user_management.html
│   │   ├── department_management.html
│   │   ├── questionnaire_management.html
│   │   ├── faculty_rankings.html
│   │   ├── reports.html
│   │   ├── logs.html
│   │   ├── analytics_hub.html
│   │   ├── ai_insights.html
│   │   ├── ai_faculty_report.html
│   │   ├── department_comparison.html
│   │   └── predictive_analytics.html
│   ├── PUBLIC/                  # Public templates
│   │   ├── landing.html
│   │   ├── login.html
│   │   ├── ratepage.html
│   │   └── receipt.html
│   └── STAFF/                   # Faculty templates
│       ├── staff_base.html
│       ├── faculty_dashboard.html
│       ├── faculty_feedback.html
│       ├── faculty_feedback_detail.html
│       └── faculty_settings.html
│
├── db.sqlite3                   # SQLite database
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── plan.txt                     # Development roadmap
└── README.md                    # This file
```

---

## Configuration

### Email Setup (SMTP)

Configure in `facutrack/settings.py` or via environment variables:

```python
# Gmail Example
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'FacuTrack <no-reply@facutrack.app>'
```

**For Gmail**: Enable 2FA and generate an App Password at https://myaccount.google.com/apppasswords

### Environment Variables (Optional)

```bash
# Windows PowerShell
$env:EMAIL_HOST_USER = "your-email@gmail.com"
$env:EMAIL_HOST_PASSWORD = "your-app-password"

# macOS/Linux
export EMAIL_HOST_USER="your-email@gmail.com"
export EMAIL_HOST_PASSWORD="your-app-password"
```

---

## Design System

### Themes

FacuTrack includes two themes:

1. **Editorial Dark** (Default)
   - Black background (#0a0a0a)
   - Gray cards (#16161a)
   - White text (#f5f5f5)
   - Gold accent (#d4af7f)

2. **Editorial White**
   - White background (#fafafa)
   - Dark text (#111114)
   - Brown accent (#8a5a2b)

Toggle themes using the moon/sun icon in the navbar. Preference is saved to localStorage.

### CSS Variables

```css
:root {
  --bg: #0a0a0a;
  --surface: #16161a;
  --text: #f5f5f5;
  --accent: #d4af7f;
  --radius: 18px;
  --transition: 300ms cubic-bezier(.4,0,.2,1);
  --serif: 'Fraunces', Georgia, serif;
  --sans: 'Inter', system-ui, sans-serif;
}
```

---

## Database Models

### Core Tables

| Model | Purpose |
|-------|---------|
| `UserProfile` | Extends Django User with role, department, gender |
| `Department` | Academic departments |
| `Questionnaire` | Evaluation questions |
| `Evaluation` | Submitted evaluation headers |
| `EvaluationAnswer` | Individual question answers (1-5 rating) |
| `DraftEvaluation` | Auto-saved incomplete evaluations |
| `ActivityLog` | Server-side audit trail |
| `VisitorLog` | Anonymous page-view tracking |
| `RecentActivity` | Human-readable activity feed |
| `LoginAttempt` | Failed login tracker |

### User Roles

- **Admin** - Full system access
- **Staff** - Faculty dashboard access
- **Superuser** - Django admin access

---

## Performance Bands

Faculty performance is classified into 5 bands:

| Band | Percentage | Description |
|------|------------|-------------|
| Excellent | 95-100% | Outstanding performance |
| Very Good | 85-94% | Above average |
| Good | 75-84% | Satisfactory |
| Fair | 60-74% | Needs improvement |
| Poor | Below 60% | Requires attention |

**Pass/Fail Threshold**: 60% (Faculty with ≥60% are marked as "Passed")

---

## Ranking Formula

```
Percentage = (Average Rating / Maximum Rating) × 100
Percentage = (Average Rating / 5) × 100
```

---

## Report Types

### Evaluation Summary Report
- Total evaluations per department
- Total answers
- Average rating
- Satisfaction percentage

### Faculty Ranking Report
- Faculty name
- Department
- Rating percentage
- Total evaluations
- Performance band

**Export Formats**: PDF, Excel (.xlsx), CSV, Word (.docx)

---

## Security Features

- **CSRF Protection** - Django built-in
- **Password Hashing** - PBKDF2 algorithm
- **Brute-Force Protection** - 5 attempts, 15-minute lockout
- **Security Headers** - CSP, X-Frame-Options, HSTS
- **Login Throttling** - IP + username tracking
- **Audit Logging** - All actions recorded
- **XSS Protection** - Template auto-escaping
- **SQL Injection Protection** - Django ORM parameter binding

---

## API Endpoints

### Public
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/rate/` | GET/POST | Evaluation form |
| `/rate/autosave/` | POST | Auto-save draft |
| `/rate/api/faculty/` | GET | Faculty by department (AJAX) |
| `/receipt/<code>/` | GET | Evaluation receipt |
| `/login/` | GET/POST | Login page |
| `/logout/` | GET/POST | Logout |

### Admin (Requires admin role)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/dashboard/` | GET | Admin dashboard |
| `/admin/users/` | GET | User management |
| `/admin/users/new/` | GET/POST | Create user |
| `/admin/users/<id>/edit/` | GET/POST | Edit user |
| `/admin/users/<id>/delete/` | POST | Delete user |
| `/admin/departments/` | GET | Department management |
| `/admin/questionnaire/` | GET | Questionnaire management |
| `/admin/rankings/` | GET | Faculty rankings |
| `/admin/reports/` | GET | Reports page |
| `/admin/reports/download/` | GET | Download report |
| `/admin/logs/` | GET | System logs |
| `/admin/analytics/` | GET | Analytics hub |
| `/admin/analytics/insights/` | GET | AI insights |
| `/admin/analytics/departments/` | GET | Department comparison |
| `/admin/analytics/predictive/` | GET | Predictive analytics |

### Faculty (Requires staff role)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/faculty/dashboard/` | GET | Faculty dashboard |
| `/faculty/feedback/` | GET | Feedback list |
| `/faculty/feedback/<id>/` | GET | Feedback detail |
| `/faculty/settings/` | GET/POST | Profile settings |

---

## Development Roadmap

FacuTrack is built in 17 phases:

| Phase | Module | Status |
|-------|--------|--------|
| 0 | Planning & Database Design | Complete |
| 1 | Landing Page | Complete |
| 2 | Authentication | Complete |
| 3 | Admin Dashboard | Complete |
| 4 | User Management | Complete |
| 5 | Departments | Complete |
| 6 | Questionnaire | Complete |
| 7 | Rankings | Complete |
| 8 | Reports | Complete |
| 9 | Logs | Complete |
| 10 | Admin Logout | Complete |
| 11 | Faculty Dashboard | Complete |
| 12 | Faculty Settings | Complete |
| 13 | Faculty Logout | Complete |
| 14 | Public Evaluation | Complete |
| 15 | Evaluation Receipt | Complete |
| 16 | Advanced Analytics | Complete |
| 17 | Certification & Recognition | Planned |

---

## Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'django'**
```bash
pip install django
```

**2. OperationalError: no such table**
```bash
python manage.py migrate
```

**3. SMTP Authentication Error**
- Enable 2FA on Gmail
- Generate App Password
- Use App Password in settings

**4. Static Files Not Loading**
```bash
python manage.py collectstatic
```

**5. Permission Denied on Database**
```bash
# Ensure db.sqlite3 has write permissions
chmod 664 db.sqlite3  # macOS/Linux
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Support

For support, email hello@facutrack.app or create an issue in the repository.

---

## Acknowledgments

- Django - Web framework
- Bootstrap - CSS framework
- Chart.js - Charting library
- AOS - Scroll animations
- Bootstrap Icons - Icon set

---

**Built with Django and modern web technologies.**
