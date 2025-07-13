from flask import Flask, render_template, request, redirect, session, url_for
from db import get_connection

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # required for session handling

@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            return redirect('/login')
        except Exception as e:
            return f"Error: {e}"
        finally:
            cursor.close()
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect('/dashboard')
        else:
            return "Invalid username or password"
    return render_template('login.html')

# All imports and routes at the top

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        return redirect('/login')

@app.route('/add_artwork', methods=['GET', 'POST'])
def add_artwork():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        medium = request.form['medium']
        image_path = request.form['image_path']
        description = request.form['description']
        created_on = request.form['created_on']
        user_id = session['user_id']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO artworks (user_id, title, medium, image_path, description, created_on)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, medium, image_path, description, created_on))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/portfolio')

    return render_template('add_artwork.html')

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM artworks WHERE user_id = %s ORDER BY created_on DESC", (user_id,))
    artworks = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('portfolio.html', username=session['username'], artworks=artworks)

if __name__ == '__main__':
    app.run(debug=True)



