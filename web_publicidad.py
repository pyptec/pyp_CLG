#!/usr/bin/env python3
from flask import Flask, request, redirect, render_template_string, send_from_directory, url_for
from werkzeug.utils import secure_filename
import os
import subprocess
import ipaddress

APP_DIR = "/home/pi/alkosto/publicidad"
ALLOWED = {"mp3", "wav", "mp4"}
ETH_DEV = "eth0"
DEFAULT_PORT = 8080

app = Flask(__name__)
os.makedirs(APP_DIR, exist_ok=True)

HTML = """
<!doctype html>
<html>
<head>
  <title>CLG - Publicidad y Red</title>
  <style>
    body { font-family: Arial; background:#f4f6f8; padding:30px; }
    .box { background:white; padding:25px; border-radius:12px; max-width:860px; margin:0 auto 20px auto; }
    h2, h3 { color:#1f2937; margin-top:0; }
    table { width:100%; border-collapse:collapse; margin-top:20px; }
    td, th { padding:10px; border-bottom:1px solid #ddd; text-align:left; }
    button { padding:8px 14px; border:0; border-radius:6px; cursor:pointer; }
    input { padding:8px; border:1px solid #cbd5e1; border-radius:6px; margin:3px; }
    .upload { background:#2563eb; color:white; }
    .delete { background:#dc2626; color:white; }
    .save { background:#16a34a; color:white; }
    .warn { background:#fff7ed; border:1px solid #fed7aa; padding:12px; border-radius:8px; color:#9a3412; }
    .ok { background:#ecfdf5; border:1px solid #bbf7d0; padding:12px; border-radius:8px; color:#166534; }
    .err { background:#fef2f2; border:1px solid #fecaca; padding:12px; border-radius:8px; color:#991b1b; white-space:pre-wrap; }
    .grid { display:grid; grid-template-columns: 180px 1fr; gap:8px; align-items:center; }
    .small { color:#64748b; font-size:13px; }
    code { background:#f1f5f9; padding:2px 5px; border-radius:4px; }
  </style>
</head>
<body>

<div class="box">
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

<div class="box">
  <h2>Configuración de Red CLG</h2>

  {% if msg %}
    <div class="{{msg_class}}">{{msg}}</div><br>
  {% endif %}

  <h3>Configuración actual</h3>
  <table>
    <tr><th>Interfaz</th><td>{{net.dev}}</td></tr>
    <tr><th>Conexión</th><td>{{net.connection}}</td></tr>
    <tr><th>IP actual</th><td>{{net.ip}}</td></tr>
    <tr><th>Máscara actual</th><td>{{net.mask}}</td></tr>
    <tr><th>Prefijo</th><td>{{net.prefix}}</td></tr>
    <tr><th>Gateway actual</th><td>{{net.gateway}}</td></tr>
    <tr><th>DNS actual</th><td>{{net.dns}}</td></tr>
  </table>

  <h3>Cambiar IP fija</h3>
  <div class="warn">
    Si la IP actual es correcta, no cambies nada. Si cambias la IP puedes perder acceso a esta página hasta conectarte por la nueva dirección.
  </div>
  <br>

  <form method="POST" action="/network/apply">
    <div class="grid">
      <label>IP:</label>
      <input name="ip" value="{{net.ip_value}}" placeholder="10.51.0.151" required>

      <label>Máscara:</label>
      <input name="mask" value="{{net.mask_value}}" placeholder="255.255.240.0" required>

      <label>Gateway:</label>
      <input name="gateway" value="{{net.gateway_value}}" placeholder="Opcional. Ej: 10.51.2.2">

      <label>DNS:</label>
      <input name="dns" value="{{net.dns_value}}" placeholder="Opcional. Puede ser igual al gateway">
    </div>

    <p class="small">
      Para red local sin internet, deja <b>Gateway</b> y <b>DNS</b> vacíos.
      Para máscara <code>255.255.240.0</code> el sistema usará <code>/20</code>.
    </p>

    <label>
      <input type="checkbox" name="reboot" value="1">
      Reiniciar después de guardar
    </label>
    <br><br>

    <button class="save" type="submit">Guardar configuración de red</button>
  </form>
</div>

</body>
</html>
"""

def run_cmd(args, timeout=5):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

def prefix_to_mask(prefix):
    try:
        return str(ipaddress.IPv4Network(f"0.0.0.0/{int(prefix)}").netmask)
    except Exception:
        return ""

def mask_to_prefix(mask):
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except Exception:
        raise ValueError("Máscara inválida. Ejemplo válido: 255.255.240.0")

def get_connection_name():
    rc, out, err = run_cmd(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    if rc == 0:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[-1] == ETH_DEV:
                return ":".join(parts[:-1])
    return "Wired connection 1"

def get_current_network():
    con = get_connection_name()
    ip = ""
    prefix = ""
    mask = ""
    gateway = ""
    dns = ""

    rc, out, err = run_cmd(["ip", "-4", "-o", "addr", "show", "dev", ETH_DEV, "scope", "global"])
    if rc == 0 and out:
        for token in out.split():
            if "/" in token and token.count(".") == 3:
                ip, prefix = token.split("/", 1)
                mask = prefix_to_mask(prefix)
                break

    rc, out, err = run_cmd(["ip", "route", "show", "default", "dev", ETH_DEV])
    if rc == 0 and out:
        parts = out.split()
        if "via" in parts:
            gateway = parts[parts.index("via") + 1]

    rc, out, err = run_cmd(["nmcli", "-g", "IP4.DNS", "connection", "show", con])
    if rc == 0 and out:
        dns = " ".join([x.strip() for x in out.splitlines() if x.strip()])

    return {
        "dev": ETH_DEV,
        "connection": con,
        "ip": ip or "No detectada",
        "mask": mask or "No detectada",
        "prefix": ("/" + prefix) if prefix else "No detectado",
        "gateway": gateway or "Sin gateway",
        "dns": dns or "Sin DNS",
        "ip_value": ip,
        "mask_value": mask,
        "gateway_value": gateway,
        "dns_value": dns,
    }

@app.route("/")
def index():
    files = sorted(os.listdir(APP_DIR))
    msg = request.args.get("msg", "")
    msg_class = request.args.get("msg_class", "ok")
    return render_template_string(HTML, files=files, net=get_current_network(), msg=msg, msg_class=msg_class)

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

@app.route("/network/apply", methods=["POST"])
def network_apply():
    con = get_connection_name()
    ip = request.form.get("ip", "").strip()
    mask = request.form.get("mask", "").strip()
    gateway = request.form.get("gateway", "").strip()
    dns = request.form.get("dns", "").strip()
    reboot = request.form.get("reboot") == "1"

    try:
        ipaddress.IPv4Address(ip)
        prefix = mask_to_prefix(mask)

        if gateway:
            ipaddress.IPv4Address(gateway)
            red = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
            if ipaddress.IPv4Address(gateway) not in red:
                raise ValueError(f"El gateway {gateway} no está dentro de la red {red}")

        if dns:
            dns_list = dns.replace(",", " ").split()
            for d in dns_list:
                ipaddress.IPv4Address(d)
            dns = " ".join(dns_list)

    except Exception as e:
        return redirect(url_for("index", msg=f"Error: {e}", msg_class="err"))

    commands = [
        ["sudo", "nmcli", "connection", "modify", con, "ipv4.addresses", f"{ip}/{prefix}"],
        ["sudo", "nmcli", "connection", "modify", con, "ipv4.method", "manual"],
    ]

    if gateway:
        commands.append(["sudo", "nmcli", "connection", "modify", con, "ipv4.gateway", gateway])
    else:
        commands.append(["sudo", "nmcli", "connection", "modify", con, "-ipv4.gateway"])

    if dns:
        commands.append(["sudo", "nmcli", "connection", "modify", con, "ipv4.dns", dns])
    else:
        commands.append(["sudo", "nmcli", "connection", "modify", con, "ipv4.dns", ""])

    log = []
    for cmd in commands:
        rc, out, err = run_cmd(cmd, timeout=10)
        log.append("$ " + " ".join(cmd))
        if out:
            log.append(out)
        if err:
            log.append(err)
        if rc != 0:
            return redirect(url_for("index", msg="Error aplicando configuración:\n" + "\n".join(log), msg_class="err"))

    if reboot:
        subprocess.Popen(["sudo", "reboot"])
        return "Configuración guardada. Reiniciando CLG... Conéctate nuevamente con la IP nueva.", 200

    return redirect(url_for("index", msg=f"Configuración guardada para {ip}/{prefix}. Reinicia el CLG o ejecuta: sudo reboot", msg_class="ok"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DEFAULT_PORT)
