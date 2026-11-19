import os
import time
import json
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from werkzeug.utils import secure_filename

from engine.database import db
from engine.decision import orchestrator
from engine.extractor import extract_raw_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TEST_INVOICES_DIR = os.path.join(BASE_DIR, "test_invoices")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

# Sample files mapping
SAMPLE_FILES = {
    "happy_path": "01_happy_path_acme.pdf",
    "split_po": "02_split_po_apex.pdf",
    "variance_tolerance": "03_variance_tolerance_nexgen.pdf",
    "fraud_alert": "04_bank_fraud_alert_global.pdf",
    "duplicate": "05_duplicate_invoice.pdf",
    "missing_data": "06_missing_critical_data.pdf"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/api/stats", methods=["GET"])
def get_stats():
    return jsonify(db.get_stats())

@app.route("/api/runs", methods=["GET"])
def get_runs():
    status_filter = request.args.get("status")
    runs = db.runs
    if status_filter and status_filter != "ALL":
        runs = [r for r in runs if r.get("status") == status_filter]
    return jsonify({"runs": runs, "total": len(runs)})

@app.route("/api/run/<run_id>", methods=["GET"])
def get_run_detail(run_id):
    for r in db.runs:
        if r.get("run_id") == run_id:
            return jsonify(r)
    return jsonify({"error": "Run not found"}), 404

@app.route("/api/pos", methods=["GET"])
def get_pos():
    return jsonify({"purchase_orders": list(db.purchase_orders.values())})

@app.route("/api/vendors", methods=["GET"])
def get_vendors():
    return jsonify({"vendors": list(db.vendors.values())})

@app.route("/api/reset", methods=["POST"])
def reset_db():
    db.reset_defaults()
    return jsonify({"success": True, "message": "Database successfully reset to demo baseline."})

@app.route("/api/download_sample/<path:filename>", methods=["GET"])
def download_sample(filename):
    return send_from_directory(TEST_INVOICES_DIR, filename, as_attachment=True)

@app.route("/api/process", methods=["POST"])
def process_invoice_endpoint():
    """
    Standard synchronous processing endpoint.
    Accepts:
    - multipart file upload ('file')
    - JSON payload with 'sample_id'
    - JSON payload with 'raw_text'
    """
    file_path = None
    filename = "invoice.pdf"
    raw_text = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{int(time.time())}_{filename}")
            file.save(file_path)

    elif request.is_json:
        data = request.get_json()
        if "sample_id" in data and data["sample_id"] in SAMPLE_FILES:
            filename = SAMPLE_FILES[data["sample_id"]]
            file_path = os.path.join(TEST_INVOICES_DIR, filename)
        elif "raw_text" in data:
            raw_text = data["raw_text"]
            filename = data.get("filename", "manual_invoice.txt")

    if not file_path and not raw_text:
        return jsonify({"error": "No file or invoice payload provided"}), 400

    result = orchestrator.process_invoice(file_path=file_path, raw_text=raw_text, filename=filename)
    return jsonify(result)

@app.route("/api/stream_process", methods=["GET"])
def stream_process():
    """
    Server-Sent Events (SSE) endpoint to simulate real-time stage execution
    with realistic visual step progression for live demos and interviews.
    """
    sample_id = request.args.get("sample_id", "happy_path")
    filename = SAMPLE_FILES.get(sample_id, "01_happy_path_acme.pdf")
    file_path = os.path.join(TEST_INVOICES_DIR, filename)

    # Prepare pristine scenario state so one-click demo buttons are 100% reliable
    if sample_id == "split_po" and "PO-2026-102" in db.purchase_orders:
        db.purchase_orders["PO-2026-102"]["previously_invoiced"] = 5000.0
        db.purchase_orders["PO-2026-102"]["remaining_balance"] = 5000.0
        db.purchase_orders["PO-2026-102"]["status"] = "PARTIALLY_INVOICED"
        db.runs = [r for r in db.runs if r.get("invoice_number") != "INV-2026-9041"]
    elif sample_id == "happy_path" and "PO-2026-101" in db.purchase_orders:
        db.purchase_orders["PO-2026-101"]["previously_invoiced"] = 0.0
        db.purchase_orders["PO-2026-101"]["remaining_balance"] = 3500.0
        db.purchase_orders["PO-2026-101"]["status"] = "OPEN"
        db.runs = [r for r in db.runs if r.get("invoice_number") != "INV-2026-8812"]
    elif sample_id == "variance_tolerance" and "PO-2026-103" in db.purchase_orders:
        db.purchase_orders["PO-2026-103"]["previously_invoiced"] = 0.0
        db.purchase_orders["PO-2026-103"]["remaining_balance"] = 5000.0
        db.purchase_orders["PO-2026-103"]["status"] = "OPEN"
        db.runs = [r for r in db.runs if r.get("invoice_number") != "INV-2026-7731"]
    elif sample_id == "fraud_alert" and "PO-2026-104" in db.purchase_orders:
        db.purchase_orders["PO-2026-104"]["previously_invoiced"] = 0.0
        db.purchase_orders["PO-2026-104"]["remaining_balance"] = 1850.0
        db.purchase_orders["PO-2026-104"]["status"] = "OPEN"
        db.runs = [r for r in db.runs if r.get("invoice_number") != "INV-2026-6620"]

    def event_generator():
        # Execute processing
        result = orchestrator.process_invoice(file_path=file_path, filename=filename)
        stage_logs = result["stage_logs"]

        yield f"data: {json.dumps({'event': 'start', 'filename': filename, 'sample_id': sample_id})}\n\n"
        time.sleep(0.3)

        for stage in stage_logs:
            time.sleep(0.4) # Realistic visual pause for live interview demo
            yield f"data: {json.dumps({'event': 'stage_complete', 'stage': stage})}\n\n"

        time.sleep(0.2)
        yield f"data: {json.dumps({'event': 'final_decision', 'result': result})}\n\n"

    return Response(event_generator(), mimetype="text/event-stream")

def find_available_port(preferred=8080):
    import socket
    for p in [preferred, 8081, 8082, 5050, 5001]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return p
        except Exception:
            continue
    return preferred

if __name__ == "__main__":
    db.reload()
    is_cloud = "PORT" in os.environ
    port = int(os.environ.get("PORT", find_available_port(8080)))
    url = f"http://127.0.0.1:{port}"
    
    print("==================================================================")
    print("🚀 Zamp AI Solutions Analyst AP Hub")
    print(f"👉 Application URL: {url} (or http://localhost:{port})")
    print("Live Runnable Process · Deliverable 1")
    print("==================================================================")
    
    # Auto-open browser in a separate thread
    import threading
    import webbrowser
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(url)
    if not is_cloud:
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(host="0.0.0.0" if is_cloud else "127.0.0.1", port=port, debug=False, threaded=True)
