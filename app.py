from flask import Flask, render_template, request, redirect, session, url_for,flash
from flask_mysqldb import MySQL
import os
import uuid
import json
import MySQLdb.cursors
import re
from datetime import date
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'ROOT'
app.config['MYSQL_DB'] = 'artist_manager'
mysql = MySQL(app)

# Upload Config
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home route redirects to login
@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # -------- Email validation --------
        if not email:
            flash("Email is required.", "error")
            return redirect('/signup')

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Invalid email format.", "error")
            return redirect('/signup')

        if "@" in email:
            domain = email.split("@")[1]
            if domain in ["gmial.com", "gmaill.com"]:  # Example suspicious domains
                flash("Email domain looks suspicious. Did you mean gmail.com?", "error")
                return redirect('/signup')

        # -------- Username validation --------
        if not username:
            flash("Username is required.", "error")
            return redirect('/signup')

        if not (3 <= len(username) <= 20):
            flash("Username must be between 3 and 20 characters.", "error")
            return redirect('/signup')

        if not re.match(r"^[A-Za-z0-9_]+$", username):
            flash("Username can only contain letters, numbers, and underscores.", "error")
            return redirect('/signup')

        if username.lower() in ["admin", "root"]:
            flash("Username is reserved. Choose another.", "error")
            return redirect('/signup')

        # -------- Password validation --------
        if not password:
            flash("Password is required.", "error")
            return redirect('/signup')

        if not (8 <= len(password) <= 64):
            flash("Password must be between 8 and 64 characters.", "error")
            return redirect('/signup')

        if not re.search(r"[A-Z]", password):
            flash("Password must contain at least one uppercase letter.", "error")
            return redirect('/signup')

        if not re.search(r"[a-z]", password):
            flash("Password must contain at least one lowercase letter.", "error")
            return redirect('/signup')

        if not re.search(r"\d", password):
            flash("Password must contain at least one digit.", "error")
            return redirect('/signup')

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            flash("Password must contain at least one special character.", "error")
            return redirect('/signup')

        if password.strip() != password:
            flash("Password must not have leading or trailing spaces.", "error")
            return redirect('/signup')

        # -------- Confirm password --------
        if confirm_password != password:
            flash("Passwords do not match.", "error")
            return redirect('/signup')

        # -------- Check existing user --------
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing = cur.fetchone()
        if existing:
            flash("Username or email already exists.", "error")
            cur.close()
            return redirect('/signup')

        # -------- Save new user --------
        hashed_password = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash("Signup successful. Please login.", "success")
        return redirect('/login')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password_input = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, password FROM users WHERE username = %s", [username])
        user = cur.fetchone()
        cur.close()

        if not user or not check_password_hash(user[1], password_input):
            flash("Invalid username or password.", "error")
            return redirect('/login')

        session['username'] = username
        session['user_id'] = user[0]

        return redirect('/dashboard')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['username'])

@app.route('/add_artwork', methods=['GET', 'POST'])
def add_artwork():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        medium = request.form['medium']
        description = request.form['description']
        created_on = request.form['created_on']
        user_id = session['user_id']

        image_file = request.files.get('image_file')
        image_path = None

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename).replace("\\", "/")
            image_file.save(image_path)
            image_path = os.path.join('uploads', unique_filename).replace("\\", "/")  # path saved in DB

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO artworks (user_id, title, medium, image_path, description, created_on)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, medium, image_path, description, created_on))
        mysql.connection.commit()
        cur.close()
        return redirect('/portfolio')

    return render_template('add_artwork.html')

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    username = session['username']

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT title, medium, image_path, description, created_on 
        FROM artworks 
        WHERE user_id=%s
    """, (user_id,))
    artworks = cur.fetchall()
    cur.close()

    return render_template('portfolio.html', username=username, artworks=artworks)


@app.route('/add_supply', methods=['GET', 'POST'])
def add_supply():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        quantity = request.form['quantity']
        purchase_date = request.form['purchase_date']
        category = request.form['category']
        user_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO supplies (user_id, name, cost, quantity, purchase_date, category)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, name, cost, quantity, purchase_date, category))
        mysql.connection.commit()
        cur.close()
        return redirect('/view_supplies')

    return render_template('add_supply.html', current_date=date.today().isoformat())

@app.route('/view_supplies')
def view_supplies():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    username = session['username']

    # Filters
    selected_category = request.args.get('category', '')
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')

    # Dynamic query
    query = "SELECT name, cost, quantity, purchase_date, category FROM supplies WHERE user_id = %s"
    filters = [user_id]
    if selected_category:
        query += " AND category = %s"
        filters.append(selected_category)
    if from_date:
        query += " AND purchase_date >= %s"
        filters.append(from_date)
    if to_date:
        query += " AND purchase_date <= %s"
        filters.append(to_date)

    cur = mysql.connection.cursor()
    cur.execute(query, filters)
    rows = cur.fetchall()
    cur.close()

    # Data processing
    supply_data = []
    chart_names, chart_costs, chart_quantities = [], [], []
    category_totals = defaultdict(float)

    for name, cost, quantity, date, category in rows:
        supply_data.append({
            'name': name,
            'cost': float(cost),
            'quantity': int(quantity),
            'purchase_date': date.strftime("%Y-%m-%d"),
            'category': category
        })
        chart_names.append(name)
        chart_costs.append(float(cost))
        chart_quantities.append(int(quantity))
        category_totals[category] += float(cost)

    top5 = sorted(rows, key=lambda x: float(x[1]), reverse=True)[:5]
    top5_names = [x[0] for x in top5]
    top5_costs = [float(x[1]) for x in top5]
    category_list = sorted({s['category'] for s in supply_data})

    return render_template("view_supplies.html",
                           username=username,
                           supplies=supply_data,
                           supply_data=supply_data,
                           chart_names=chart_names,
                           chart_costs=chart_costs,
                           chart_quantities=chart_quantities,
                           category_labels=list(category_totals.keys()),
                           category_values=list(category_totals.values()),
                           top5_names=top5_names,
                           top5_costs=top5_costs,
                           categories=category_list,
                           selected_category=selected_category,
                           from_date=from_date,
                           to_date=to_date)
if __name__ == '__main__':
    app.run(debug=True)
