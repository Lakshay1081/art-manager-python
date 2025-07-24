from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import os
import uuid
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
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.connection.commit()
        cur.close()
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
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
            unique_filename = str(uuid.uuid4()) + "_" + filename
            image_path = os.path.join('uploads', unique_filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO artworks (user_id, title, medium, image_path, description, created_on)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user_id, title, medium, image_path, description, created_on))
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
        quantity = request.form['quantity']
        description = request.form['description']
        user_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO supplies (user_id, name, quantity, description) VALUES (%s, %s, %s, %s)",
                    (user_id, name, quantity, description))
        mysql.connection.commit()
        cur.close()
        return redirect('/view_supplies')

    return render_template('add_supply.html')

@app.route('/view_supplies')
def view_supplies():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, quantity, description FROM supplies WHERE user_id=%s", (user_id,))
    supplies = cur.fetchall()
    cur.close()

    return render_template('view_supplies.html', supplies=supplies, username=session['username'])

if __name__ == '__main__':
    app.run(debug=True)
