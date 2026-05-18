from flask import Flask, render_template, request
import sqlite3
import qrcode
import os
from datetime import datetime
import uuid
import hashlib

app = Flask(__name__)

# Create folder
if not os.path.exists("static/qr_codes"):
    os.makedirs("static/qr_codes")

# Create database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id TEXT, department TEXT, filename TEXT, timestamp TEXT, hash TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Home page
@app.route('/')
def home():
    return render_template('upload.html')

# Upload document
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    department = request.form['department']

    filename = file.filename
    filepath = "static/" + filename
    file.save(filepath)

    # Generate hash
    with open(filepath, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    doc_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to DB
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
              (doc_id, department, filename, timestamp, file_hash))
    conn.commit()
    conn.close()

    # 🔥 IMPORTANT: CHANGE THIS IP (use hotspot IP for best result)
    qr_data = f"http://10.26.102.227:5000/verify/{doc_id}"

    qr = qrcode.make(qr_data)
    qr_path = f"static/qr_codes/{doc_id}.png"
    qr.save(qr_path)

    return render_template("result.html", doc_id=doc_id, qr_path="/" + qr_path)

# Verify document
@app.route('/verify/<doc_id>')
def verify(doc_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
    data = c.fetchone()
    conn.close()

    if data:
        filepath = "static/" + data[2]

        with open(filepath, "rb") as f:
            new_hash = hashlib.sha256(f.read()).hexdigest()

        if new_hash == data[4]:
            status = "✅ VALID DOCUMENT"
            status_class = "valid"
        else:
            status = "❌ TAMPERED DOCUMENT"
            status_class = "invalid"

        return render_template("verify.html", status=status, data=data, status_class=status_class)

    else:
        return "<h2 style='color:red;'>❌ INVALID DOCUMENT</h2>"

# Admin panel with filter
@app.route('/admin')
def admin():
    dept = request.args.get('dept')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if dept:
        c.execute("SELECT * FROM documents WHERE department=?", (dept,))
    else:
        c.execute("SELECT * FROM documents")

    data = c.fetchall()
    conn.close()

    return render_template("admin.html", data=data)

# Run server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)