from .core import FireState

def get_active_fires(model):
    """Devuelve todas las posiciones con fuego en el modelo."""
    fires = []
    for y in range(model.height):
        for x in range(model.width):
            if model._get_fire_state(x, y) == FireState.FIRE:
                fires.append({"row": y, "col": x})
    return fires
