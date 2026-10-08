"""Small AWS PhotoShare demo; stores uploads in Amazon EFS when EFS_ID is set."""
import os
import socket
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

application = Flask(__name__)
application.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MiB, demo uploads only
VERSION = "v1"  # Edit to v2 in GitHub to demonstrate automatic CI/CD deployment.
ALLOWED = {"png", "jpg", "jpeg", "gif", "webp"}

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhotoShare | AWS CI/CD Lab</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:#182633;background:#f6f8fb}
*{box-sizing:border-box}body{margin:0}header{background:#173753;color:white;padding:22px 6vw}
header h1{margin:0;font-size:1.55rem}header p{margin:6px 0 0;opacity:.85}
main{max-width:900px;margin:30px auto;padding:0 18px}
.card{background:white;border:1px solid #dce4ec;border-radius:12px;padding:24px;margin:18px 0;box-shadow:0 3px 12px #1831480b}
.status{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}.pill{background:#e8f0f7;color:#245073;padding:7px 12px;border-radius:999px;font-size:.85rem}
form{display:flex;flex-wrap:wrap;gap:12px;align-items:center}button{border:0;background:#187d67;color:white;border-radius:8px;padding:12px 18px;font-weight:650;cursor:pointer}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:16px;margin-top:18px}
.photo{background:#fff;border:1px solid #dfe7ec;border-radius:10px;overflow:hidden}.photo img{width:100%;height:135px;object-fit:cover;display:block}
.photo span{display:block;padding:8px;font-size:12px;overflow-wrap:anywhere}.muted{color:#647687}
</style></head><body>
<header><h1>PhotoShare ☁</h1><p>AWS Auto Scaling + EFS + CI/CD demonstration</p></header>
<main>
<section class="card"><h2>Application dashboard</h2>
<p>Upload a photo, then check that it remains available after load balancing or adding EC2 instances.</p>
<div class="status"><span class="pill">Release: {{ version }}</span><span class="pill">Storage: {{ mode }}</span><span class="pill">Server: {{ server }}</span></div></section>
<section class="card"><h2>Upload an image</h2>
<form action="{{ url_for('upload') }}" method="POST" enctype="multipart/form-data">
<input type="file" name="photo" accept="image/png,image/jpeg,image/gif,image/webp" required>
<button type="submit">Upload Photo</button></form>
<p class="muted">PNG, JPG, GIF or WEBP; maximum 5 MB. Use non-sensitive test photos only.</p></section>
<section class="card"><h2>Shared photo gallery ({{ photos|length }})</h2>
{% if photos %}<div class="gallery">{% for photo in photos %}
<div class="photo"><img src="{{ url_for('photo_file', name=photo) }}" alt="Uploaded photo" loading="lazy"><span>{{ photo }}</span></div>
{% endfor %}</div>{% else %}<p class="muted">No photos yet. Upload one above.</p>{% endif %}
</section></main></body></html>"""


def storage_path():
    """Fail closed if shared storage is requested but EFS is not mounted."""
    if os.environ.get("EFS_ID", "").strip():
        if not os.path.ismount("/mnt/efs"):
            raise RuntimeError("EFS_ID is configured, but /mnt/efs is not mounted")
        return Path("/mnt/efs/photos")
    return Path(os.environ.get("LOCAL_UPLOAD_DIR", "/tmp/photoshare-demo"))


def storage_status():
    return "Amazon EFS (shared)" if os.environ.get("EFS_ID", "").strip() else "Local disk (setup only)"


@application.get("/health")
def health():
    try:
        path = storage_path()
        path.mkdir(parents=True, exist_ok=True)
        return jsonify(status="ok", storage=storage_status(), version=VERSION)
    except (OSError, RuntimeError) as exc:
        application.logger.error("Storage unavailable: %s", exc)
        return jsonify(status="error", error="Storage unavailable"), 503


@application.get("/")
def index():
    try:
        path = storage_path()
        path.mkdir(parents=True, exist_ok=True)
        photos = sorted((p.name for p in path.iterdir() if p.is_file() and p.suffix.lstrip(".").lower() in ALLOWED), reverse=True)
    except (OSError, RuntimeError) as exc:
        application.logger.error("Storage unavailable: %s", exc)
        return "Shared storage unavailable. Check EFS mount and security groups.", 503
    return render_template_string(TEMPLATE, photos=photos, version=VERSION, mode=storage_status(), server=socket.gethostname())


@application.post("/upload")
def upload():
    photo = request.files.get("photo")
    if not photo or not photo.filename:
        abort(400, "Choose a photo")
    original = secure_filename(photo.filename)
    extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if extension not in ALLOWED or not (photo.mimetype or "").startswith("image/"):
        abort(400, "Only PNG/JPG/GIF/WEBP images are allowed")
    try:
        path = storage_path()
        path.mkdir(parents=True, exist_ok=True)
        photo.save(path / f"{uuid4().hex[:10]}_{original}")
    except (OSError, RuntimeError) as exc:
        application.logger.error("Upload storage unavailable: %s", exc)
        return "Upload failed: shared storage unavailable.", 503
    return redirect(url_for("index"), code=303)


@application.get("/photos/<name>")
def photo_file(name):
    # send_from_directory prevents traversal outside the photo directory.
    try:
        path = storage_path()
        return send_from_directory(path, name)
    except (OSError, RuntimeError):
        return "Shared storage unavailable", 503


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=5000)
