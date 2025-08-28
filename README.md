# E-Commerce API

A simple E-Commerce REST API built with **Flask**, **SQLAlchemy**, **Marshmallow**, and **MySQL**.  
This project was created as part of the Coding Temple assignment.

---

## 🚀 Features
- User management (create, read, update, delete).
- Product management (create, read, update, delete).
- Order management:
  - Create orders for users.
  - Add/remove products from orders (many-to-many).
  - View all products in an order.
  - View all orders for a specific user.
- Marshmallow validation:
  - Valid email format for users.
  - Non-negative price validation for products.
  - Valid user reference when creating orders.
- RESTful JSON responses.

---

## 🛠 Tech Stack
- **Python 3**
- **Flask**
- **Flask-SQLAlchemy**
- **Flask-Marshmallow**
- **MySQL / MySQL Workbench**

---

## ⚙️ Setup & Installation

1. Clone or download this repo.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
