from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mysqldb import MySQL
import os
import uuid
import re
from datetime import date
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

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

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "error")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Home redirects to login
@app.route('/')
def home():
    return redirect('/login')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Basic validation (email, username, password)
        if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Invalid email.", "error")
            return redirect('/signup')

        if not username or not re.match(r"^[A-Za-z0-9_]{3,20}$", username):
            flash("Invalid username.", "error")
            return redirect('/signup')

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect('/signup')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        if cur.fetchone():
            flash("Username or email already exists.", "error")
            cur.close()
            return redirect('/signup')

        hashed_password = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash("Signup successful. Please login.", "success")
        return redirect('/login')

    return render_template('signup.html')

# Login
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

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect('/login')

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

# Add Artwork
@app.route('/add_artwork', methods=['GET', 'POST'])
@login_required
def add_artwork():
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
            image_path = os.path.join('uploads', unique_filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO artworks (user_id, title, medium, image_path, description, created_on)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, medium, image_path, description, created_on))
        mysql.connection.commit()
        cur.close()
        flash("Artwork added successfully!", "success")
        return redirect('/portfolio')

    return render_template('add_artwork.html')

# Portfolio
@app.route('/portfolio')
@login_required
def portfolio():
    user_id = session['user_id']
    username = session['username']

    cur = mysql.connection.cursor()
    cur.execute("SELECT about_me FROM users WHERE user_id=%s", (user_id,))
    about_me_row = cur.fetchone()
    about_me = about_me_row[0] if about_me_row else ""

    cur.execute("SELECT title, medium, image_path, description, created_on FROM artworks WHERE user_id=%s", (user_id,))
    artworks = cur.fetchall()
    cur.close()
    return render_template('portfolio.html', username=username, about_me=about_me, artworks=artworks, editable=True)

# Update About Me
@app.route('/update_about', methods=['POST'])
@login_required
def update_about():
    user_id = session['user_id']
    about_me = request.form.get('about_me', '')

    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET about_me = %s WHERE user_id = %s", (about_me, user_id))
    mysql.connection.commit()
    cur.close()

    flash("About Me updated successfully!", "success")
    return redirect('/portfolio')


# Add Supply
@app.route('/add_supply', methods=['GET', 'POST'])
@login_required
def add_supply():
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
        flash("Supply added successfully!", "success")
        return redirect('/view_supplies')

    return render_template('add_supply.html', current_date=date.today().isoformat())

# View Supplies
@app.route('/view_supplies')
@login_required
def view_supplies():
    user_id = session['user_id']

    selected_category = request.args.get('category', '')
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')

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

    supply_data = []
    chart_names, chart_costs, chart_quantities = [], [], []
    category_totals = defaultdict(float)

    for name, cost, quantity, purchase_date, category in rows:
        supply_data.append({
            'name': name,
            'cost': float(cost),
            'quantity': int(quantity),
            'purchase_date': purchase_date.strftime("%Y-%m-%d"),
            'category': category
        })
        chart_names.append(name)
        chart_costs.append(float(cost))
        chart_quantities.append(int(quantity))
        category_totals[category] += float(cost)

    top5 = sorted(rows, key=lambda x: float(x[1]), reverse=True)[:5]
    top5_names = [x[0] for x in top5]
    top5_costs = [float(x[1]) for x in top5]

    return render_template("view_supplies.html",
                           username=session['username'],
                           supplies=supply_data,
                           chart_names=chart_names,
                           chart_costs=chart_costs,
                           chart_quantities=chart_quantities,
                           category_labels=list(category_totals.keys()),
                           category_values=list(category_totals.values()),
                           top5_names=top5_names,
                           top5_costs=top5_costs,
                           categories=list(category_totals.keys()),
                           selected_category=selected_category,
                           from_date=from_date,
                           to_date=to_date)

if __name__ == '__main__':
    app.run(debug=True)
