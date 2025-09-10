from flask import Flask, jsonify, request
from aquiesaleatorio import model, FireState, FireRescueModel, grid_layout  # Importa el modelo, clase y layout

app = Flask(__name__)


# Endpoint para obtener las celdas con humo
@app.route("/api/smoke", methods=["GET"])
def get_smoke():
    smoke = []
    for y in range(model.height):
        for x in range(model.width):
            if model._get_fire_state(x, y) == FireState.SMOKE:
                smoke.append({"row": y, "col": x})
    return jsonify({"smoke": smoke})

# Endpoint para obtener los POIs activos
@app.route("/api/pois", methods=["GET"])
def get_pois():
    pois = []
    for poi in model.active_pois:
        pois.append({
            "x": poi.x,
            "y": poi.y,
            "type": poi.type.value,
            "revealed": poi.revealed
        })
    return jsonify({"pois": pois})

# Endpoint para reiniciar el modelo y comenzar desde el estado inicial
@app.route("/api/reset", methods=["POST"])
def reset_model():
    global model
    model = FireRescueModel(grid_layout)
    return jsonify({"message": "Modelo reiniciado"})

# 🔥 Endpoint de fuegos (ahora dinámico)
@app.route("/api/fires", methods=["GET"])
def get_fires():
    fires = []
    for y in range(model.height):
        for x in range(model.width):
            if model._get_fire_state(x, y) == FireState.FIRE:
                fires.append({"row": y, "col": x})
    return jsonify({"fires": fires})

# 🧑‍🚒 Endpoint de agentes (dinámico)
@app.route("/api/agents", methods=["GET"])
def get_agents():
    agents = []
    for agent in model.agent_list:
        agents.append({
            "id": agent.unique_id,
            "x": agent.pos[0],
            "y": agent.pos[1],
            "role": agent.role.value if agent.role else None,
            "knocked_out": agent.is_knocked_out()
        })
    return jsonify({"agents": agents})

# 🌫️ Endpoint de humo (dinámico)
    
# Endpoint para avanzar la simulación y generar fuegos/humo aleatorios
@app.route("/api/step", methods=["POST"])
def step_model():
    model.step()
    fires = []
    for y in range(model.height):
        for x in range(model.width):
            if model._get_fire_state(x, y) == FireState.FIRE:
                fires.append({"row": y, "col": x})
    agents = []
    for agent in model.agent_list:
        agents.append({
            "id": agent.unique_id,
            "x": agent.pos[0],
            "y": agent.pos[1],
            "role": agent.role.value if agent.role else None,
            "knocked_out": agent.is_knocked_out()
        })
    return jsonify({
        "message": "Modelo avanzado",
        "step": model.step_count,
        "fires": fires,
        "agents": agents
    })



if __name__ == "__main__":
    print("🚀 Iniciando servidor de debug...")
    print("📡 Endpoints disponibles:")
    print("   GET /api/fires")
    print("   GET /api/smoke")
    app.run(host="0.0.0.0", port=3690, debug=True)





