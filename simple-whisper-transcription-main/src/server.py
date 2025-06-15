from flask import Flask, render_template, request, jsonify
 
app = Flask(__name__)
 
# Shared state
app_state = {
    "slider_value": 50,  # Light intensity
    "volume_level": 50,  # Volume control (speedometer)
    "button_pressed": False
}
 
@app.route('/')
def index():
    return render_template('src/index.html', state=app_state)
 
@app.route('/api/slider', methods=['GET', 'POST'])
def slider():
    if request.method == 'POST':
        data = request.get_json()
        app_state['slider_value'] = data.get('value', app_state['slider_value'])
        return jsonify(success=True, slider_value=app_state['slider_value'])
    return jsonify(slider_value=app_state['slider_value'])
 
@app.route('/api/volume', methods=['GET', 'POST'])
def volume():
    if request.method == 'POST':
        data = request.get_json()
        app_state['volume_level'] = data.get('value', app_state['volume_level'])
        return jsonify(success=True, volume_level=app_state['volume_level'])
    return jsonify(volume_level=app_state['volume_level'])
 
@app.route('/api/state', methods=['GET'])
def state():
    return jsonify(app_state)
 
if __name__ == '__main__':
    app.run(debug=True)