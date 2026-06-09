from flask import Flask, request, redirect, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
import os

APP_DIR = "/home/pi/alkosto/publicidad"
LOGO_FILE = "/home/pi/alkosto/logo/logo_pyp.jpg"
ALLOWED = {"mp3", "wav", "mp4"}

app = Flask(__name__)
os.makedirs(APP_DIR, exist_ok=True)

HTML = """
<!doctype html>
<html>
<head>
  <title>Cliente Ganador - Publicidad</title>
  <style>
    body { font-family: Arial; background:#f4f6f8; padding:30px; }
    .box { position:relative; background:white; padding:25px; border-radius:12px; max-width:700px; margin:auto; }
    .logo { position:absolute; top:18px; right:18px; width:70px; height:70px; object-fit:contain; border-radius:50%; }
    h2 { color:#1f2937; }
    table { width:100%; border-collapse:collapse; margin-top:20px; }
    td, th { padding:10px; border-bottom:1px solid #ddd; }
    button { padding:8px 14px; border:0; border-radius:6px; cursor:pointer; }
    .upload { background:#2563eb; color:white; }
    .delete { background:#dc2626; color:white; }
  </style>
</head>
<body>
<div class="box">
  <img class="logo" src="/logo" alt="PYP Tecnología">
  <h2>Cliente Ganador - Gestión de Publicidad</h2>

  <form method="POST" enctype="multipart/form-data" action="/upload">
    <input type="file" name="file" required>
    <button class="upload" type="submit">Subir archivo</button>
  </form>

  <table>
    <tr><th>Archivo</th><th>Acción</th></tr>
    {% for f in files %}
    <tr>
      <td><a href="/files/{{f}}" target="_blank">{{f}}</a></td>
      <td>
        <form method="POST" action="/delete/{{f}}">
          <button class="delete" type="submit">Eliminar</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
</body>
</html>
"""

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

@app.route("/")
def index():
    files = sorted(os.listdir(APP_DIR))
    return render_template_string(HTML, files=files)
  
@app.route("/logo")
def logo():
    logo_dir = os.path.dirname(LOGO_FILE)
    logo_name = os.path.basename(LOGO_FILE)
    return send_from_directory(logo_dir, logo_name)

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or f.filename == "":
        return redirect("/")
    if not allowed(f.filename):
        return "Archivo no permitido. Use mp3, wav o mp4.", 400

    filename = secure_filename(f.filename)
    f.save(os.path.join(APP_DIR, filename))
    return redirect("/")

@app.route("/delete/<filename>", methods=["POST"])
def delete(filename):
    filename = secure_filename(filename)
    path = os.path.join(APP_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect("/")

@app.route("/files/<filename>")
def files(filename):
    return send_from_directory(APP_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)