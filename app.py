# app.py
import os
import io
import sys
import subprocess
import datetime
from flask import Flask, render_template, request, send_file, jsonify, url_for, send_from_directory
from werkzeug.utils import secure_filename
import qrcode
from qrcode.constants import ERROR_CORRECT_H

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "saved_qrcodes")
os.makedirs(SAVE_DIR, exist_ok=True)

# reuse QR func behaviour as CLI/TK version
def qr_image(text, box_size=10, border=4, fill="black", back="white"):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill, back_color=back).convert("RGBA")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    POST form fields:
      - qr_text: string (required)
      - save: 'true' or 'false' (optional)
    behavior:
      - if save == 'true' -> save file to saved_qrcodes and return JSON with 'path' and 'url'
      - otherwise -> return the PNG image bytes directly (image/png)
    """
    text = (request.form.get("qr_text") or "").strip()
    save_flag = (request.form.get("save") or "false").lower() == "true"

    if not text:
        return jsonify({"error": "No text provided"}), 400

    img = qr_image(text)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    if save_flag:
        # create filename
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = secure_filename(f"qrcode_{ts}.png")
        filepath = os.path.join(SAVE_DIR, fname)
        img.save(filepath)
        return jsonify({
            "saved": True,
            "path": os.path.abspath(filepath),
            "url": url_for("serve_qrcode", filename=fname)
        })
    else:
        return send_file(buffer, mimetype="image/png")


@app.route("/qrcodes/<filename>")
def serve_qrcode(filename):
    # serve storing database
    return send_from_directory(SAVE_DIR, filename, as_attachment=False)


@app.route("/open_folder", methods=["POST"])
def open_folder():
    """
    Expects JSON body: { "path": "<absolute file path>" }
    Only allows paths under SAVE_DIR (safety). On local dev this opens the OS file explorer.
    """
    data = request.get_json(force=True)
    path = data.get("path")
    if not path:
        return jsonify({"error": "missing path"}), 400

    path = os.path.abspath(path)
    # only allow opening folders in SAVE_DIR
    if not path.startswith(SAVE_DIR):
        return jsonify({"error": "path not allowed"}), 403

    folder = os.path.dirname(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
        return jsonify({"opened": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # debug=True
    app.run(debug=True)
