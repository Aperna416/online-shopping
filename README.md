# Common Goods Online Shop

A small online shopping application built with Flask, MySQL, HTML, CSS, and JavaScript. It includes a searchable product list, a session-based shopping cart, registration and login, and a basic checkout that saves orders to MySQL.

## Requirements

- Python 3.10 or later
- MySQL Server
- VS Code with the Python extension

## Run in VS Code

1. Open this project folder in VS Code.
2. Open the integrated terminal and create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install the Python packages:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create the database in MySQL:

   ```sql
   CREATE DATABASE online_shop;
   ```

5. Copy `.env.example` to `.env` and set your MySQL username, password, and a private `SECRET_KEY`. The app loads this file when it starts. In PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

6. Start the application:

   ```powershell
   py app.py
   ```

   The app creates its tables and inserts starter products the first time it connects. Open `http://127.0.0.1:5000` in your browser.

## Project files

- `app.py` contains the Flask routes, MySQL access, login, cart, and checkout logic.
- `templates/` contains the HTML pages.
- `static/css/style.css` contains the page styling.
- `static/js/app.js` handles the add-to-cart interaction without reloading the product page.
- `requirements.txt` lists the Python dependencies.

Product photos are loaded from Unsplash, so an internet connection is needed to display them. This is a learning project; before deploying publicly, add CSRF protection, secure production configuration, and order/payment processing appropriate to your use case.