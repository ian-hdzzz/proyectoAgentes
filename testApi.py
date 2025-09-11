from flask import Flask, jsonify, request
from aquiesaleatorio import (
    model, FireState, FireRescueModel, grid_layout,
    POIType  # Agregamos POIType a las importaciones
)

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
        poi_data = {
            "x": poi.x,
            "y": poi.y,
            "type": poi.type.value,
            "revealed": poi.revealed
        }
        print(f"Enviando POI: {poi_data}")  # Debug print
        pois.append(poi_data)
    response = {"pois": pois}
    print(f"Respuesta completa: {response}")  # Debug print
    return jsonify(response)

# Endpoint para revelar un POI
@app.route("/api/reveal_poi", methods=["POST"])
def reveal_poi():
    try:
        data = request.form
        x = int(data['x'])
        y = int(data['y'])
        
        # Buscar el POI en esa posición
        poi = model._get_poi_at_position(x, y)
        if poi is None:
            return jsonify({
                'success': False,
                'message': 'No hay POI en esta posición'
            })
            
        if poi.revealed:
            return jsonify({
                'success': False,
                'message': 'POI ya fue revelado'
            })
            
        # Revelar el POI
        model.reveal_poi(x, y)
        
        # Preparar respuesta
        response = {
            'success': True,
            'poiType': 'victim' if poi.type == POIType.VICTIM else 'false_alarm',
            'wasRevealed': poi.revealed,
            'message': 'POI revelado exitosamente'
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

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

@app.route("/api/gamestate", methods=["GET"])
def get_game_state():
    return jsonify({
        "gameState": {
            "phase": model.phase,
            "currentAgent": model.current_agent_index,
            "damageCount": model.damage_count,
            "roundCount": model.round_count,
            "gameOver": model.game_over,
            "gameWon": model.game_won,
            "endReason": model.end_reason if hasattr(model, 'end_reason') else ""
        }
    })

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





