from flask import Flask, jsonify, request

app = Flask(__name__)

# 🔥 Endpoint de fuegos
@app.route("/api/fires", methods=["GET"])
def get_fires():
    fires = [
        {"row": 1, "col": 5},
        {"row": 3, "col": 1},
        {"row": 3, "col": 3}
    ]
    return jsonify({"fires": fires})

# 🧱 Endpoint de muros
@app.route("/api/walls", methods=["GET"])
def get_walls():
    walls = [
        {"row": 0, "col": 2},
        {"row": 2, "col": 2},
        {"row": 4, "col": 5}
    ]
    return jsonify({"walls": walls})

# 🚑 Endpoint de víctimas (POI)
@app.route("/api/pois", methods=["GET"])
def get_pois():
    pois = [
        {"row": 1, "col": 1, "type": "victim"},
        {"row": 2, "col": 3, "type": "victim"},
        {"row": 4, "col": 4, "type": "false_alarm"}  # ejemplo de tipo
    ]
    return jsonify({"pois": pois})

# 🌫️ Endpoint de humo
@app.route("/api/smoke", methods=["GET"])
def get_smoke():
    smoke = [
        {"row": 2, "col": 1},
        {"row": 3, "col": 4}
    ]
    return jsonify({"smoke": smoke})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3690, debug=True)
