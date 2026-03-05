from flask import Flask, request, redirect, session, send_from_directory, render_template_string
import os, sqlite3, hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "simol_jr_secret_key_2026"

DB_PATH = os.path.join("/tmp", "users.db")
UPLOAD_ROOT = os.path.join("/tmp", "uploads")
PROFILE_ROOT = os.path.join("/tmp", "profiles")

os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(PROFILE_ROOT, exist_ok=True)

# ---------------- DATABASE ----------------

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        profile_pic TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ---------------- HTML ----------------

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Simol Jr</title>
<style>
body{
font-family:Arial;
background:#fafafa;
margin:40px;
}

img{
border-radius:10px;
}

button{
padding:8px 15px;
background:#3897f0;
border:none;
color:white;
border-radius:5px;
}

a{
text-decoration:none;
color:#3897f0;
}
</style>
</head>

<body>

<h2>Simol Jr – Private Photo Website</h2>
<hr>

{{ body|safe }}

</body>
</html>
"""

LOGIN_HTML = """
<h3>Login</h3>

<form method="POST">

Username<br>
<input name="username" required><br><br>

Password<br>
<input type="password" name="password" required><br><br>

<button>Login</button>

</form>

<p>New user? <a href="/register">Register here</a></p>

<p style="color:red">{{ error }}</p>
"""

REGISTER_HTML = """
<h3>Register</h3>

<form method="POST">

Username<br>
<input name="username" required><br><br>

Password<br>
<input type="password" name="password" required><br><br>

<button>Create account</button>

</form>

<p><a href="/login">Back to login</a></p>

<p style="color:red">{{ error }}</p>
"""

HOME_HTML = """
<p>
Welcome <b>{{ user }}</b> |
<a href="/profile">Profile</a> |
<a href="/logout">Logout</a>
</p>

{% if pic %}
<img src="/profile_image/{{ pic }}" width="100"><br><br>
{% endif %}

<form method="POST" enctype="multipart/form-data">
<input type="file" name="photo" required>
<button>Upload photo</button>
</form>

<hr>

<h3>Your Photos</h3>

{% for img in images %}

<div style="display:inline-block;margin:15px;text-align:center">

<a href="/view/{{ img }}">
<img src="/image/{{ img }}" width="160">
</a>

<br><br>

<a href="/view/{{ img }}">View</a> |
<a href="/download/{{ img }}">Download</a> |
<a href="/delete/{{ img }}">Delete</a>

</div>

{% else %}

<p>No photos uploaded yet.</p>

{% endfor %}
"""

PROFILE_HTML = """
<h3>Upload Profile Picture</h3>

<form method="POST" enctype="multipart/form-data">

<input type="file" name="profile_pic" required>

<button>Upload</button>

</form>

<br>

<a href="/">Back</a>
"""

def render_page(body, **ctx):
    content = render_template_string(body, **ctx)
    return render_template_string(BASE_HTML, body=content)

# ---------------- ROUTES ----------------

@app.route("/", methods=["GET","POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    user_folder = os.path.join(UPLOAD_ROOT, user)
    os.makedirs(user_folder, exist_ok=True)

    if request.method == "POST":

        f = request.files.get("photo")

        if f and f.filename:
            name = secure_filename(f.filename)
            f.save(os.path.join(user_folder, name))

        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT profile_pic FROM users WHERE username=?", (user,))
    row = cur.fetchone()

    pic = row[0] if row else None

    con.close()

    images = os.listdir(user_folder)

    return render_page(HOME_HTML, images=images, user=user, pic=pic)

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET","POST"])
def login():

    error=""

    if request.method=="POST":

        u=request.form["username"]
        p=hash_pw(request.form["password"])

        con=get_db()
        cur=con.cursor()

        cur.execute(
        "SELECT id FROM users WHERE username=? AND password=?",
        (u,p)
        )

        r=cur.fetchone()

        con.close()

        if r:
            session["user"]=u
            return redirect("/")

        else:
            error="Invalid username or password"

    return render_page(LOGIN_HTML,error=error)

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET","POST"])
def register():

    error=""

    if request.method=="POST":

        u=request.form["username"]
        p=hash_pw(request.form["password"])

        try:

            con=get_db()
            cur=con.cursor()

            cur.execute(
            "INSERT INTO users(username,password,profile_pic) VALUES(?,?,?)",
            (u,p,None)
            )

            con.commit()
            con.close()

            session["user"]=u

            return redirect("/")

        except:
            error="Username already exists"

    return render_page(REGISTER_HTML,error=error)

# ---------------- PROFILE ----------------

@app.route("/profile", methods=["GET","POST"])
def profile():

    if "user" not in session:
        return redirect("/login")

    user=session["user"]

    if request.method=="POST":

        f=request.files.get("profile_pic")

        if f and f.filename:

            filename=secure_filename(f.filename)

            path=os.path.join(PROFILE_ROOT,filename)

            f.save(path)

            con=get_db()
            cur=con.cursor()

            cur.execute(
            "UPDATE users SET profile_pic=? WHERE username=?",
            (filename,user)
            )

            con.commit()
            con.close()

        return redirect("/")

    return render_page(PROFILE_HTML)

# ---------------- VIEW IMAGE ----------------

@app.route("/view/<filename>")
def view_image(filename):

    if "user" not in session:
        return redirect("/login")

    html=f"""

<h2>View Photo</h2>

<img src='/image/{filename}' style='max-width:80%'>

<br><br>

<a href='/download/{filename}'>Download</a> |
<a href='/'>Back</a>

"""

    return render_page(html)

# ---------------- DOWNLOAD ----------------

@app.route("/download/<filename>")
def download_file(filename):

    if "user" not in session:
        return redirect("/login")

    user_folder=os.path.join(UPLOAD_ROOT,session["user"])

    return send_from_directory(
    user_folder,
    filename,
    as_attachment=True
    )

# ---------------- IMAGE ----------------

@app.route("/image/<filename>")
def image(filename):

    if "user" not in session:
        return redirect("/login")

    user_folder=os.path.join(UPLOAD_ROOT,session["user"])

    return send_from_directory(user_folder,filename)

# ---------------- PROFILE IMAGE ----------------

@app.route("/profile_image/<filename>")
def profile_image(filename):

    return send_from_directory(PROFILE_ROOT,filename)

# ---------------- DELETE ----------------

@app.route("/delete/<filename>")
def delete(filename):

    if "user" not in session:
        return redirect("/login")

    user_folder=os.path.join(UPLOAD_ROOT,session["user"])

    path=os.path.join(user_folder,filename)

    if os.path.exists(path):
        os.remove(path)

    return redirect("/")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# ---------------- MAIN ----------------

if __name__=="__main__":

    app.run(host="0.0.0.0",port=5000)