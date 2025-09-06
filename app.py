
from flask import Flask, request, jsonify, render_template_string, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, io
from datetime import datetime

app = Flask(__name__)

LAST_RESULTS = {"valid": [], "invalid": [], "timestamp": None}

# HTML embed langsung di kode
HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roblox Cookie Checker</title>
<style>
body { background:#0f1115;color:#fff;font-family:Arial; }
.container { max-width:600px;margin:20px auto;text-align:center; }
button { padding:10px 15px;background:#00ff95;color:#000;border:none;border-radius:8px;cursor:pointer;font-weight:bold; }
pre { background:#111218;padding:10px;border-radius:8px;text-align:left;white-space:pre-wrap;word-break:break-all; }
</style>
</head>
<body>
<div class="container">
  <h1>Roblox Cookie Checker</h1>
  <input id="fileInput" type="file" accept=".txt" />
  <button id="checkBtn">Check Cookies</button>
  <h2>✅ Valid Cookies</h2>
  <pre id="validBox">Menunggu...</pre>
  <h2>❌ Invalid Cookies</h2>
  <pre id="invalidBox">Menunggu...</pre>
</div>
<script>
document.getElementById("checkBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  if (!fileInput.files.length) { alert("Pilih file data.txt dulu"); return; }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  const res = await fetch("/check", { method: "POST", body: fd });
  const data = await res.json();
  document.getElementById("validBox").textContent = data.valid.length ? data.valid.join("\\n") : "Tidak ada cookie valid";
  document.getElementById("invalidBox").textContent = data.invalid.length ? data.invalid.join("\\n") : "Tidak ada cookie invalid";
});
</script>
</body>
</html>
"""

# Fungsi cek cookie Roblox
def check_cookie(cookie):
    cookie = cookie.strip()
    if len(cookie) < 80:
        return False, cookie, ""

    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.roblox.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Origin": "https://www.roblox.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    try:
        r = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers,
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            username = data.get("name") or "Unknown"
            return True, cookie, username
        return False, cookie, ""
    except:
        return False, cookie, ""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/check", methods=["POST"])
def check():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    cookies = list({
        c.strip()
        for c in file.read().decode("utf-8", errors="ignore").splitlines()
        if c.strip()
    })

    valid, invalid = [], []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(check_cookie, c) for c in cookies]
        for fut in as_completed(futures):
            ok, token, username = fut.result()
            if ok:
                valid.append(f"{token}  -->  [{username}]")
            else:
                invalid.append(token)

    LAST_RESULTS["valid"] = valid
    LAST_RESULTS["invalid"] = invalid
    LAST_RESULTS["timestamp"] = datetime.utcnow().isoformat()
    return jsonify(LAST_RESULTS)

@app.route("/download/<which>")
def download(which):
    if which not in ("valid", "invalid"):
        return "Not found", 404
    data = LAST_RESULTS.get(which, [])
    content = "\n".join(data)
    return send_file(io.BytesIO(content.encode()), as_attachment=True, download_name=f"{which}_cookies.txt")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
