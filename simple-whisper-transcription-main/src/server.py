

from pathlib import Path
from flask import Flask, render_template, request, jsonify

# ---------------------------------------------------------------------------
#  Configure Flask so Jinja looks for templates in the SAME directory
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../src
app = Flask(__name__, template_folder=str(BASE_DIR))

# ---------------------------------------------------------------------------
#  Shared application state
# ---------------------------------------------------------------------------
app_state = {
    "slider_value": 50,      # Light intensity
    "volume_level": 50,      # Speedometer
    "button_pressed": False  # Example boolean flag
}

# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # No path prefixes—just the filename
    return render_template("index.html", state=app_state)


@app.route("/api/slider", methods=["GET", "POST"])
def slider():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "value" in data:
            try:
                app_state["slider_value"] = int(data["value"])
            except (ValueError, TypeError):
                pass
        return jsonify(success=True, slider_value=app_state["slider_value"])
    return jsonify(slider_value=app_state["slider_value"])


@app.route("/api/volume", methods=["GET", "POST"])
def volume():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "value" in data:
            try:
                app_state["volume_level"] = int(data["value"])
            except (ValueError, TypeError):
                pass
        return jsonify(success=True, volume_level=app_state["volume_level"])
    return jsonify(volume_level=app_state["volume_level"])


@app.route("/api/button", methods=["POST"])
def button():
    """
    Optional endpoint if you have a button in your UI.
    Toggles or sets `button_pressed`.
    """
    data = request.get_json(silent=True) or {}
    # If a value is provided, use it; otherwise, simply toggle.
    app_state["button_pressed"] = bool(
        data.get("pressed", not app_state["button_pressed"])
    )
    return jsonify(success=True, button_pressed=app_state["button_pressed"])


@app.route("/api/state")
def state():
    return jsonify(app_state)

# ---------------------------------------------------------------------------
#  Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # host='0.0.0.0' lets you reach it from other devices on the LAN;
    # change to '127.0.0.1' if you only need local access.
    app.run(host="0.0.0.0", port=5000, debug=True)