# alphatex — Premium Luxury eCommerce

**alphatex** is a modern, responsive, and secure eCommerce platform designed for premium retail. It is built using Python, Flask, SQLite, and Vanilla CSS with rich, bespoke, and responsive dark/light visual designs.

---

## ✨ Features

### 👤 Customer Experience
*   **Google OAuth Login**: Fast, secure login with Google accounts using Authlib.
*   **Customer Profiles**: Comprehensive dashboard for customers to manage:
    *   Full Name, Gender, DOB, and profile avatar uploads.
    *   Primary mobile number registration (with duplicate checks and Bangladesh mobile number formatting).
*   **Delivery Address Book**:
    *   Multiple saved shipping addresses with custom tags (`Home`, `Office`, `Other`) and Default flags.
    *   Bangladesh-specific cascading location dropdowns (Division ➔ District ➔ Upazila/Thana) powered by `bd_locations.js`.
    *   Google Maps pins integration.
*   **Order History & Tracking**: Overview of past order statuses (`Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`), payment details, and tracking IDs.
*   **Wishlist**: Save favorite items to a curated wishlist.
*   **IP-Based Personalized Homepage**: Automatically tracks browsing patterns per client IP to prioritize category recommendations on the homepage (with random fallbacks).
*   **Legal & Support Hubs**: Beautifully styled, animated pages including Contact Us (interactive AJAX form), searchable FAQ accordion, Shipping & Returns (visual flowchart), Size Guide (interactive CM/IN unit converter), and complete Privacy, Terms, and Cookie Policy pages.

### 🛒 Shopping Flow
*   **Dynamic Cart Drawer**: Live slider cart showing subtotal, item counters, free shipping progress bars, and custom cross-sell recommendations.
*   **Bespoke Checkout**: Responsive one-page checkout automatically selecting default delivery address, with options to choose other addresses or add a new address via AJAX without leaving checkout.
*   **Rich Product Showcase**: Grid-based layouts, parallax images, search filters, and infinite scroll for categories.

### 🛡️ Admin Management Panel
*   **Logistics & Fulfillment**: Detailed customer order views showing complete delivery details, Google Maps links, and text shipping logs. Admins can:
    *   Edit customer delivery address before shipment.
    *   Log courier details (courier name, tracking numbers, tracking URLs).
    *   Update order fulfillment statuses.
    *   Record internal order notes.
*   **Inventory & Categories**: Manage categories, slides, and products directly from the interface.
*   **TOTP 2-Factor Authentication (2FA)**: High-security setup for admin users with manual keys and QR codes.
*   **Brute-Force & Session Protection**: Account lockouts after failed login attempts and secure IP whitelisting.
*   **Communications Center**: Review, update, and manage all Customer Contact Queries and Newsletter email subscriptions from the dashboard.
*   **Data Export for ML**: Download client browsing log streams directly to CSV under settings to train recommendations ML models.
*   **Security Threat Monitor**: View live suspicious IP logs, permanently block or unblock IPs, and monitor all active security layers.

### 🚀 Speed & Protection Middlewares
*   **Custom Gzip Compression**: Middleware compressing all text/JSON/CSS/JS payloads >500B on the fly, saving 70-80% bandwidth.
*   **Aggressive Caching**: Sets Cache-Control public cache headers (1 year max-age) for static assets.
*   **7-Layer Bot Shield**: Active filters for bad user-agents, CMS scanning probes (SQLi, LFI), rate limiters, honeypots, and custom animated error pages (403, 429, 404).

---

## 🛠️ Tech Stack
*   **Backend**: Flask (Python 3.13)
*   **ORM / Database**: Flask-SQLAlchemy (SQLite)
*   **Authentication & Security**: Flask-Login, Authlib (Google OAuth), PyOTP (TOTP 2FA), Flask-Limiter, CSRFProtect, Cloudflare Turnstile
*   **Frontend**: HTML5, Vanilla CSS, JS (ES6)

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.8+ installed.

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/pythonicshariful/alphatex
cd alphatex
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///shop.db

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Twilio SMS (Optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

### 4. Database Migrations
Run the migration script to configure database columns:
```bash
python migrate_db.py
```

### 5. Running the Application
Start the Flask server:
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## 👥 Seed Credentials (Local Testing)

Upon first run, the database seeds the following super administrator:
*   **Email**: `test@gmail.com`
*   **Password**: `12345678`
