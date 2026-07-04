# ⚜️ alphatex — Premium Luxury eCommerce Platform

[![Python Version](https://img.shields.io/badge/python-3.8%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-gold.svg)](LICENSE)
[![Security Status](https://img.shields.io/badge/security-7--Layer%20Shield-red.svg)](#-multi-layer-bot-shield--security)

**alphatex** is an enterprise-grade, responsive, and secure eCommerce platform crafted specifically for premium retail brands. Built on top of Python, Flask, and SQLite, it offers bespoke light/dark UI themes, modern page transitions, tactile card interactions, and robust security filters designed to handle production-scale environments.

---

## 📖 Table of Contents
1. [✨ Key Features](#-key-features)
2. [🛡️ Multi-Layer Bot Shield & Security](#%EF%B8%8F-multi-layer-bot-shield--security)
3. [⚡ Performance & Speed Optimizations](#-performance--speed-optimizations)
4. [📂 Directory Structure](#-directory-structure)
5. [🗄️ Database Schema & Models](#%EF%B8%8F-database-schema--models)
6. [🔌 API Reference](#-api-reference)
7. [🚀 Getting Started](#-getting-started)
8. [👥 Seed Credentials](#-seed-credentials)

---

## ✨ Key Features

### 👤 Customer Experience & Personalization
*   **Secure Authentication**: Integrated Google OAuth 2.0 (via `Authlib`) alongside secure local account registrations.
*   **Rich Customer Profiles**: Dashboards allowing users to manage details, upload custom avatars, and secure account states.
*   **Cascading Delivery Address Book**:
    *   Cascading location dropdowns (Division ➔ District ➔ Upazila/Thana) tailored for Bangladesh logistics, powered by `bd_locations.js`.
    *   Google Maps link integrations for delivery personnel.
    *   Default billing/shipping address selectors.
*   **IP-Based Personalized Homepage**: Tracks category browsing history per client IP using custom logs, dynamically prioritizing relevant collections on subsequent visits while preserving randomized discovery slots.
*   **Full Support & Policy Hubs**:
    *   **Contact Us**: Multi-subject AJAX contact form protected by Cloudflare Turnstile and honeypots.
    *   **FAQ**: Interactive, filterable, and searchable accordions.
    *   **Size Guide**: Responsive size charts (Men, Women, Kids) with an interactive **CM to Inch** conversion toggle.
    *   **Shipping & Returns**: Clear 3-step delivery and 4-step returns flow chart.
    *   **Cookie Policy**: Granular consent settings (Analytics & Personalization toggles) backed by `localStorage` persistence.

### 🛒 Shopping Flow
*   **Slide-Out Cart Drawer**: Live slider showing subtotal, remaining amount for free shipping (৳2000 threshold), and dynamic cross-sell recommendations.
*   **Bespoke One-Page Checkout**: Sleek checkout interface displaying items, order notes, and allowing guest checkouts or default address selections with inline additions.
*   **Tactile Visuals**: Custom keyframed entry animations, theme toggles, and CSS transitions on all product listing layouts.

### 🛡️ Admin Management Panel
*   **Fulfillment Control**: Track orders by state (`Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`). Assign courier details (courier name, tracking numbers, tracking URLs) and log internal notes.
*   **Settings & Maintenance**: Enable site-wide Maintenance Mode instantly (hides catalog) and customize active social media handles.
*   **Threat Monitor**: Real-time overview of suspicious IP requests, blocked IPs, and active shield layers.
*   **Data Export for ML**: Download client category-browsing logs in a structured CSV format to train recommendation engines.
*   **TOTP Two-Factor Authentication (2FA)**: High-security enrollment with visual QR codes (powered by `qrcode` and `pyotp`) for administrator accounts.

---

## 🛡️ Multi-Layer Bot Shield & Security

The platform utilizes a multi-layered middleware architecture in [bot_protection.py](file:///g:/Personal/Illyen/bot_protection.py) configured at the global request handler to protect endpoints from malicious automation and automated scans:

1.  **User-Agent Filtering**: Checks and drops requests matching 15+ scanner signatures (e.g. `sqlmap`, `nikto`, `scrapy`, `BurpSuite`, `nmap`).
2.  **Path Scan Blocker**: Inspects request paths and queries against Local File Inclusion (LFI), SQL injection (SQLi), and cross-site scripting (XSS) payloads. Drops common CMS scan probes (like `wp-admin`, `.env`, `.git`).
3.  **Autonomous Temporary Bans**: Track failed security probes per IP address. If an IP triggers 20+ violations within 5 minutes, it is automatically throttled for 10 minutes (returns HTTP 429).
4.  **IP Blocklists**: Admins can permanently block malicious IPs from the Security Monitor dashboard.
5.  **Honeypot Fields**: Transparent, CSS-hidden form inputs added to contact and subscription forms to trap bots that auto-fill inputs.
6.  **Cloudflare Turnstile Verification**: Cryptographic challenge validation protecting authentication (register/login) and message submission endpoints.
7.  **Flask-WTF CSRF Protection**: Enforces token exchange on all POST requests.

---

## ⚡ Performance & Speed Optimizations

*   **Custom Gzip Compression**: A built-in Flask response optimizer dynamically compresses all text, CSS, JS, JSON, and SVG payloads exceeding 500 bytes on the fly, reducing payload size by up to **75%**.
*   **Aggressive Static Asset Caching**: Sets the HTTP `Cache-Control` header to `public, max-age=31536000, immutable` for static files (CSS, JS, images, icons, and web fonts).
*   **Cache-Busting Assets**: Handles static asset updates automatically via URL version parameters (`?v=`), ensuring browser cache invalidation only when assets are changed.

---

## 📂 Directory Structure

```text
alphatex/
│
├── admin/                  # Admin blueprints and panel controllers
│   └── routes.py           # Admin routes, auth, security logs & team roles
│
├── auth/                   # Authentication blueprints
│   └── routes.py           # Login, registration, OTP checks, Google OAuth
│
├── shop/                   # Core storefront blueprints
│   └── routes.py           # Categories, product details, support, checkouts
│
├── user/                   # Customer dashboard blueprints
│   └── routes.py           # Profile management, address book, order lists
│
├── static/                 # Static asset folders
│   ├── css/                # CSS styling (styles.css, ui.css, profile.css, admin.css)
│   ├── js/                 # Javascript files (main.js, ui.js, bd_locations.js)
│   └── images/             # Product photography and logo media
│
├── templates/              # HTML layout templates
│   ├── admin/              # Admin view layouts
│   ├── auth/               # Login & Register layouts
│   ├── errors/             # Error pages (403, 404, 429)
│   └── base.html           # Master base layout template
│
├── app.py                  # Main Flask application factory & database seeds
├── config.py               # Settings, Twilio configurations, OAuth credentials
├── extensions.py           # Flask plugins (SQLAlchemy, Limiter, CSRF, LoginManager)
├── models.py               # Core database relational model schemas
└── bot_protection.py       # Security middleware and request checkers
```

---

## 🗄️ Database Schema & Models

Below is a breakdown of the primary relational database tables:

*   **`User`**: Handles both guest accounts (`is_guest=True`) and registered customers. Includes standard credentials, profile details, and avatars.
*   **`AdminUser`**: Stores administrator accounts, roles (`super_admin`, `editor`, `viewer`), and secret keys for TOTP 2FA.
*   **`Product`**: Holds inventory details, prices, comparisons, categories, and references to image slots.
*   **`Order` & `OrderItem`**: Maps orders to customer profiles, shipping details, prices, quantities, tracking IDs, and courier details.
*   **`ProductViewLog`**: Logs IP addresses and browsed category IDs to power the personalized product recommendation feed.
*   **`NewsletterSubscriber`**: Stores emails of users who signed up for newsletter updates.
*   **`ContactMessage`**: Stores submitted messages from the Contact Us form, including name, email, subject, body, and read/unread status.

---

## 🔌 API Reference

### Storefront APIs
*   `GET /api/products` (Rate Limit: 60/min): Fetches paginated lists of products with category filters.
*   `GET /api/search` (Rate Limit: 30/min): Search products by query string.
*   `POST /subscribe-newsletter` (Rate Limit: 5/min): Register an email to the newsletter database.

### Admin APIs
*   `POST /admin/orders/bulk` (Rate Limit: 10/min): Batch actions to transition order states.
*   `GET /admin/export-view-logs`: Downloads client category view logs to CSV.

---

## 🚀 Getting Started

### 1. Installation
Clone the repository:
```bash
git clone https://github.com/pythonicshariful/alphatex.git
cd alphatex
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory:
```env
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///shop.db

# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_secret

# Cloudflare Turnstile keys
TURNSTILE_SITE_KEY=your_site_key
TURNSTILE_SECRET_KEY=your_secret_key
```

### 3. Database Initialization
Run the database migrations to prepare tables:
```bash
python migrate_db.py
```

### 4. Run Server
Launch the Flask development server:
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## 👥 Seed Credentials

On startup, the system seeds a default super-administrator account for local testing:
*   **Email**: `test@gmail.com`
*   **Password**: `12345678`
