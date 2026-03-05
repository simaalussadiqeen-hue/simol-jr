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

# ---------------- COLORFUL UI ----------------

BASE_HTML = """

<!DOCTYPE html>
<html>
<head>
<title>Simol Jr</title>

<style>

body{
font-family:Arial;
margin:0;
background: linear-gradient(120deg,#fdf497,#fd5949,#d6249f,#285AEB);
background-size:400% 400%;
animation: gradient 12s ease infinite;
}

@keyframes gradient{
0%{background-position:0% 50%}
50%{background-position:100% 50%}
100%{background-position:0% 50%}
}

.navbar{
background:linear-gradient(90deg,#ff512f,#dd2476);
padding:15px;
display:flex;
justify-content:space-between;
align-items:center;
color:white;
}

.logo{
font-size:26px;
font-weight:bold;
}

.container{
max-width:700px;
margin:auto;
padding:20px;
}

.card{
background:white;
border-radius:12px;
box-shadow:0 4px 12px rgba(0,0,0,0.2);
margin-bottom:25px;
overflow:hidden;
}

.card-header{
display:flex;
align-items:center;
padding:10px;
}

.profile-pic{
width:40px;
height:40px;
border-radius:50%;
margin-right:10px;
border:2px solid #ff4b7d;
object-fit:cover;
}

.card img{
width:100%;
}

.card-actions{
padding:10px;
}

button{
background:linear-gradient(90deg,#ff512f,#dd2476);
color:white;
border:none;
padding:10px 18px;
border-radius:8px;
cursor:pointer;
}

input{
padding:10px;
width:100%;
margin-bottom:12px;
border-radius:6px;
border:1px solid #ccc;
}

.center{
max-width:350px;
margin:auto;
margin-top:120px;
background:white;
padding:30px;
border-radius:12px;
box-shadow:0 4px 15px rgba(0,0,0,0.2);
}

a{
text-decoration:none;
color:#dd2476;
font-weight:bold;
}

</style>

</head>

<body>

<div class="navbar">

<div class="logo">Simol Jr</div>

<div>

{% if session.get('user') %}
<a href="/">Home</a> |
<a href="/profile">Profile</a> |
<a href="/logout">Logout</a>
{% endif %}

</div>

</div>

<div class="container">

{{ body|safe }}

</div>

</body>
</html>
"""

# ---------------- LOGIN ----------------

LOGIN_HTML = """

<div class="center">

<h2>Login</h2>

<form method="POST">

<input name="username" placeholder="Username" required>

<input type="password" name="password" placeholder="Password" required>

<button>Login</button>

</form>

<p>New user? <a href="/register">Register</a></p>

<p style="color:red">{{ error }}</p>

</div>
"""

# ---------------- REGISTER ----------------

REGISTER_HTML = """

<div class="center">

<h2>Create Account</h2>

<form method="POST">

<input name="username" placeholder="Username" required>

<input type="password" name="password" placeholder="Password" required>

<button>Register</button>

</form>

<p><a href="/login">Back to login</a></p>

<p style="color:red">{{ error }}</p>

</div>
"""

# ---------------- HOME ----------------

HOME_HTML = """

<h3>Welcome {{ user }}</h3>

{% if pic %}
<img src="/profile_image/{{ pic }}" class="profile-pic">
{% endif %}

<hr>

<form method="POST" enctype="multipart/form-data">

<input type="file" name="photo" required>

<button>Upload Photo</button>

</form>

{% for img in images %}

<div class="card">

<div class="card-header">

{% if pic %}
<img src="/profile_image/{{ pic }}" class="profile-pic">
{% endif %}

<b>{{ user }}</b>

</div>

<img src="/image/{{ img }}">

<div class="card-actions">

<a href="/view/{{ img }}">View</a> |
<a href="/download/{{ img }}">Download</a> |
<a href="/delete/{{ img }}">Delete</a>

</div>

</div>

{% else %}

<p>No photos uploaded yet.</p>

{% endfor %}
"""

# ---------------- PROFILE ----------------

PROFILE_HTML = """

<h3>Upload Profile Picture</h3>

<form method="POST" enctype="multipart/form-data">

<input type="file" name="profile_pic" required>

<button>Upload</button>

</form>

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

    user=session["user"]

    user_folder=os.path.join(UPLOAD_ROOT,user)
    os.makedirs(user_folder,exist_ok=True)

    if request.method=="POST":

        f=request.files.get("photo")

        if f and f.filename:
            name=secure_filename(f.filename)
            f.save(os.path.join(user_folder,name))

        return redirect("/")

    con=get_db()
    cur=con.cursor()

    cur.execute("SELECT profile_pic FROM users WHERE username=?", (user,))
    row=cur.fetchone()

    pic=row[0] if row else None

    con.close()

    images=os.listdir(user_folder)

    return render_page(HOME_HTML,images=images,user=user,pic=pic)

# ---------------- LOGIN ----------------

@app.route("/login",methods=["GET","POST"])
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

@app.route("/register",methods=["GET","POST"])
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

@app.route("/profile",methods=["GET","POST"])
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

<img src='/image/{filename}' style='max-width:100%'>

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

    return send_from_directory(user_folder,filename,as_attachment=True)

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