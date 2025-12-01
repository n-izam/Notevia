# 📝 Notevia – Notebook Reselling Website

A Django-based notebook reselling web application built for **learning and study purposes**.

The project includes product management, variants, coupon/offer system, order flow, and a clean Bootstrap-based frontend.

---

## 🚀 Overview

**Notevia** is a simple e-commerce system for selling notebooks.

It supports multiple brands, categories, variants, offers, wallet system, referral, wishlist, and more.

This project helped me learn:

- Django Class-Based Views
- How to structure multi-app Django projects
- PostgreSQL integration
- Working with Bootstrap
- Product & variant management
- Checkout flow and coupon logic
- Basic admin dashboards

---

## 📦 Features

### 🧾 Product Management

- Add, update, delete notebook products
- Supports three brands:
    - **Paper Grid**
    - **Classmates**
    - **Notevia (own brand)**
- Categories:
    - **Short Note**
    - **King Size**
    - **A4 Notebook**

### 🔄 Variant System

Each product **must have at least one variant**.

Additional variants can be added.

Available variants:

- **Ruled**
- **Unruled**
- **Grid Note**

Variant-level details:

- Price
- Stock
- Offer support

### 🎟️ Offers & Coupons

- **Product-level offers**
- **Coupon-level offers**
- Admin can create, activate, or deactivate coupon

### 💳 Cart & Wallet

- Add/remove products from cart
- Wallet feature with credit & debit history

### 🛒 Order Management

- Checkout
- Coupon application
- Address handling
- Order placement
- Order cancellation & returns
- Admin dashboard for order approval & status updates

### ❤️ Wishlist & Referral System

- Users can add/remove wishlist items
- Basic referral system (admin side)

### ⭐ Reviews (Planned)

- The `review` app exists but is not implemented yet.

### 🖥️ Frontend

- HTML + CSS
- Bootstrap
- Mobile friendly UI

---

## 🧑‍💻 Tech Stack

| Component | Technology |
| --- | --- |
| **Backend** | Django (Class-Based Views) |
| **Frontend** | HTML, CSS, Bootstrap |
| **Database** | PostgreSQL |
| **Static Files** | Stored locally (CSS/JS) |
| **Product Images** | Stored on cloud (Cloudinary/AWS/other) |
| **Environment Variables** | `.env` file |
| **Version Control** | Git + GitHub |

---

## 📁 Project Structure

```
notevia/
│
├── accounts/       # User login, signup, profile & address
├── adminpanel/     # Admin dashboard, product/category/variant management
├── cart/           # Cart & wallet management
├── cores/          # Home, Shop, Product detail, Static pages
├── notevia/        # Project settings & URLs
├── offers/         # Coupon & offer management
├── orders/         # Checkout, user orders, admin order management
├── products/       # Referral, wishlist, admin sales reports
├── review/         # (Not implemented yet)
├── templates/      # All HTML templates
├── static/         # CSS, JS, logos (product images on cloud)
│
├── .env            # Secret keys & environment variables
├── .gitignore      # Files to ignore when pushing to GitHub
├── manage.py
├── requirements.txt
└── README.md

```

---

## 🙌 Learning Experience

This project helped me understand:

- Django Class-Based Views (CBV)
- Multi-app Django architecture
- PostgreSQL integration
- User authentication system
- Product & variant modeling
- Creating admin dashboards
- Applying coupons & offers
- Working with cloud image storage
- Using Bootstrap for responsive UI

---

## 🧭 Future Improvements

- Implement product review system
- Improve wishlist & referral features
- Add search & filtering
- Add pagination
- Add user activity log
- Improve admin UI

---

## 📄 License

This project is for **educational and learning purposes only**.

## 🚀 Deployment (Production)

```bash
# 1. Clone the project
git clone <https://github.com/n-izam/Notevia.git>
cd notevia

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-dotenv

# 4. Create .env file (see .env.example below)

# 5. Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# 6. Run with gunicorn (testing)
gunicorn notevia.wsgi:application --bind 0.0.0.0:8000