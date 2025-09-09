import numpy as np
from enum import Enum

# Estados de fuego
class FireState(Enum):
    CLEAR = 0
    SMOKE = 1
    FIRE = 2

# Grid de ejemplo (puedes cargar desde archivo si quieres)
grid_layout = np.array([
    [1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 2, 0, 1],
    [1, 0, 0, 1, 0, 0, 1],
    [1, 0, 2, 0, 2, 0, 1],
    [1, 1, 0, 1, 0, 1, 1],
    [1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1]
])

class FireRescueModel:
    def __init__(self, grid):
        self.grid = grid
        self.height, self.width = grid.shape
        self.fire_states = np.full((self.height, self.width), FireState.CLEAR)

        # Colocar fuegos iniciales
        self._place_initial_fires()

    def _place_initial_fires(self):
        self.fire_states[3, 1] = FireState.FIRE
        self.fire_states[3, 3] = FireState.FIRE
        self.fire_states[1, 5] = FireState.FIRE

    def _get_fire_state(self, x, y):
        return self.fire_states[y, x]

    def step(self):
        # Aquí meterás la lógica de propagación
        pass
