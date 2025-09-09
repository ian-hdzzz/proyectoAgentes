
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
import seaborn as sns
import mesa
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import matplotlib.lines as lines
import pandas as pd
from enum import Enum
import random

sns.set()
plt.rcParams['animation.html'] = 'jshtml'
plt.rcParams['figure.figsize'] = (5, 5)

wall_type = [0, 1, 2, 3, 4] # 0: none, 1: wall 1hp, 2: wall 2hp, 3: open door
                              # 4: closed door

grid_layout = [[(2, 0, 2, 2), (2, 0, 2, 0), (2, 4, 2, 0), (2, 0, 0, 4), (2, 0, 0, 0), (2, 2, 0, 0), (2, 0, 0, 2), (2, 2, 0, 0)],
               [(2, 0, 0, 2), (2, 0, 0, 0), (2, 2, 0, 0), (0, 0, 2, 2), (0, 0, 2, 0), (0, 4, 4, 0), (0, 0, 0, 4), (0, 2, 0, 0)],
               [(0, 0, 0, 2), (0, 0, 2, 0), (0, 2, 0, 0), (2, 0, 0, 2), (2, 0, 0, 0), (4, 2, 0, 0), (0, 0, 0, 2), (0, 2, 0, 0)],
               [(0, 2, 4, 2), (2, 2, 0, 2), (0, 2, 0, 2), (0, 0, 2, 2), (0, 0, 0, 0), (0, 2, 0, 0), (0, 0, 2, 2), (0, 2, 2, 0)],
               [(4, 0, 0, 2), (0, 2, 0, 0), (0, 0, 2, 2), (2, 3, 2, 0), (0, 0, 4, 3), (0, 3, 2, 0), (2, 0, 0, 3), (2, 3, 0, 0)],
               [(0, 0, 2, 2), (0, 0, 2, 0), (2, 0, 2, 0), (2, 0, 2, 0), (4, 0, 2, 0), (2, 2, 2, 0), (0, 0, 2, 2), (0, 2, 2, 0)]
               ]

grid_layout = np.array(grid_layout)

class FireState(Enum):
  CLEAR = 0
  SMOKE = 1
  FIRE = 2

class POIType(Enum):
  VICTIM = "victim"
  FALSE = "false_alarm"

class POI:
  def __init__(self, poi_id, poi_type, x, y):
    self.id = poi_id
    self.type = poi_type
    self.x = x
    self.y = y
    self.revealed = False

class FireRescueModel(Model):
  def __init__(self, grid_data):
    super().__init__()
    self.grid_data = grid_data
    height, width = grid_data.shape[:2]
    self.height = height
    self.width = width

    self.grid = SingleGrid(width, height, torus=False)
    self.schedule = RandomActivation(self)
    self.running = True
    self.fire_states = np.full((height, width), FireState.CLEAR)
    self.step_count = 0
    self.damage_count = 0

    self.all_pois = []
    self.active_pois = []
    self.revealed_pois = []
    self.lost_victims = []


    self._create_poi_pool()
    self._place_initial_pois()
    self._place_initial_fires()

  def _create_poi_pool(self):
    poi_id = 1
    for i in range(10):
      poi = POI(poi_id, POIType.VICTIM, -1, -1)
      self.all_pois.append(poi)
      poi_id += 1

    for i in range(5):
      poi = POI(poi_id, POIType.FALSE, -1, -1)
      self.all_pois.append(poi)
      poi_id += 1

    random.shuffle(self.all_pois)

  def _get_valid_positions_for_poi(self):
    valid_positions = []

    for y in range(self.height):
      for x in range(self.width):
        # Verificar que no haya poi en esa pocision
        if any(poi.x == x and poi.y == y for poi in self.active_pois):
          continue

        valid_positions.append((x, y))

    return valid_positions

  def _place_initial_pois(self):
    valid_positions = self._get_valid_positions_for_poi()

    initial_pois = random.sample(self.all_pois, 3)
    selected_positions = random.sample(valid_positions, 3)

    for poi, (x, y) in zip(initial_pois, selected_positions):
      poi.x = x
      poi.y = y
      self.active_pois.append(poi)

    for poi in initial_pois:
      self.all_pois.remove(poi)

  def _get_poi_at_position(self, x, y):
    for poi in self.active_pois:
      if poi.x == x and poi.y == y:
        return poi
    return None

  def place_new_poi(self):
    if len(self.all_pois) == 0:
      return None

    valid_positions = self._get_valid_positions_for_poi()
    if len(valid_positions) == 0:
      return None

    new_poi = random.choice(self.all_pois)
    selected_position = random.choice(valid_positions)

    new_poi.x = selected_position[0]
    new_poi.y = selected_position[1]
    self.fire_states[new_poi.y, new_poi.x] = FireState.CLEAR
    self.active_pois.append(new_poi)
    self.all_pois.remove(new_poi)

    return new_poi

  def reveal_poi(self, x, y):
    for poi in self.active_pois:
      if poi.x == x and poi.y == y and not poi.revealed:
        poi.revealed = True
        self.revealed_pois.append(poi)

        if poi.type == POIType.VICTIM:
          print(f"Es una victima.")
        elif poi.type == POIType.FALSE:
          print(f"Es una falsa alarma.")
          self.place_new_poi()

    return False

  def check_pois_in_danger(self):
    pois_lost = []
    for poi in self.active_pois:
      fire_state = self._get_fire_state(poi.x, poi.y)
      if fire_state == FireState.FIRE:
        if poi.type == POIType.VICTIM:
          self.lost_victims.append(poi)
        self.active_pois.remove(poi)
        pois_lost.append(poi)
        self.place_new_poi()

    return pois_lost

  def _place_initial_fires(self):
      self.fire_states[3, 1] = FireState.FIRE
      self.fire_states[3, 3] = FireState.FIRE
      self.fire_states[1, 5] = FireState.FIRE

  def spread_fire_random(self):
    x = random.randint(0, self.width - 1)
    y = random.randint(0, self.height - 1)

    current_state = self._get_fire_state(x, y)

    if current_state == FireState.CLEAR:
      self._set_fire_state(x, y, FireState.SMOKE)

    elif current_state == FireState.SMOKE:
      self._set_fire_state(x, y, FireState.FIRE)

    elif current_state == FireState.FIRE:
      adjacent_cells = self._get_adjacent_cells(x, y)

      for adj in adjacent_cells:
        ax, ay = adj['pos']
        wall_type = adj['wall_type']
        wall_dir = adj['wall_dir']

        can_pass = self.damage_wall(ax, ay, wall_dir)

        if can_pass:
          adj_state = self._get_fire_state(ax, ay)

          if adj_state == FireState.CLEAR:
            self._set_fire_state(ax, ay, FireState.FIRE)
          elif adj_state == FireState.SMOKE:
            self._set_fire_state(ax, ay, FireState.FIRE)

  def spread_smoke_to_fire(self):
    fire_positions = []
    for y in range(self.height):
      for x in range(self.width):
        if self._get_fire_state(x, y) == FireState.FIRE:
          fire_positions.append((x, y))

    smoke_to_convert = []
    for fx, fy in fire_positions:
      adjacent_cells = self._get_adjacent_cells(fx, fy)
      for adj in adjacent_cells:
        ax, ay = adj['pos']
        wall_type = adj['wall_type']
        if (self._get_fire_state(ax, ay) == FireState.SMOKE and wall_type == 0):
          smoke_to_convert.append((ax, ay))

    for sx, sy in smoke_to_convert:
      self._set_fire_state(sx, sy, FireState.FIRE)

  def _get_fire_state(self, x, y):
    return self.fire_states[y, x]

  def _set_fire_state(self, x, y, state):
    self.fire_states[y, x] = state

  def _get_adjacent_cells(self, x, y):
    adjacent = []
    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # arriba, derecha, abajo, izquierda
    for i, (dx, dy) in enumerate(directions):
      nx, ny = x + dx, y + dy
      if 0 <= nx < self.width and 0 <= ny < self.height:
        wall_type, wall_dir = self._get_wall_between_cells(x, y, nx, ny)
        adjacent.append({
            'pos': (nx, ny),
            'wall_type': wall_type,
            'wall_dir': wall_dir,
            'source_pos': (x, y)
        })
    return adjacent

  def _get_wall_between_cells(self, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == -1: # Arriba
      direction = 0
    elif dx == 1 and dy == 0: # Derecha
      direction = 1
    elif dx == 0 and dy == 1: # Abajo
      direction = 2
    elif dx == -1 and dy == 0: # Izquierda
      direction = 3
    else: # No son adyacentes
      return 0, -1

    if 0 <= x1 < self.width and 0 <= y1 < self.height:
      wall_type = self.grid_data[y1, x1, direction]
      return wall_type, direction
    else:
      return 0, -1

  def damage_wall(self, x, y, direction):
    if 0 <= x < self.width and 0 <= y < self.height:
      current_wall = self.grid_data[y, x, direction]
      if current_wall == 2:
        self.grid_data[y, x, direction] = 1
        self.damage_count += 1
        return False
      elif current_wall == 1:
        self.grid_data[y, x, direction] = 0
        self.damage_count += 1
        return True
      elif current_wall in [3, 4]:
        self.grid_data[y, x, direction] = 0
        self.damage_count += 1
        return True
      else:
        return True

  def step(self):
    self.schedule.step()
    self.spread_fire_random()
    self.spread_smoke_to_fire()
    lost_pois = self.check_pois_in_danger()
    if lost_pois:
      victims_lost = sum(1 for p in lost_pois if p.type == POIType.VICTIM)
      alarms_destroyed = sum(1 for p in lost_pois if p.type == POIType.FALSE)
      print(f"¡{victims_lost} víctima(s) y {alarms_destroyed} falsa(s) alarma(s) perdidas por fuego!")
    self.step_count += 1
    print(f"Damage count: {self.damage_count}")

model = FireRescueModel(grid_layout)
rows = model.height
cols = model.width
print(f"Dimensiones del grid: {rows} filas x {cols} columnas")
print(f"Ejemplo accediendo como lista: {model.grid_data[0][0]}")
print(f"Ejemplo FireState fuego: {model.fire_states[3,3]}")

def get_wall_visual_style(wall_type):
  if wall_type == 0:
    return None, 0, '-'
  elif wall_type == 1:
    return 'black', 2, '-'
  elif wall_type == 2:
    return 'black', 4, '-'
  elif wall_type == 3:
    return 'green', 4, '--'
  elif wall_type == 4:
    return 'red', 4, '-'

fig, ax = plt.subplots(figsize=(cols, rows))

def draw_grid(ax, model):
  ax.clear()
  ax.set_xlim(0, cols)
  ax.set_ylim(0, rows)
  ax.set_aspect('equal', adjustable='box')
  ax.invert_yaxis()

  border_color = 'darkblue'
  border_width = 6
  ax.add_line(lines.Line2D([0, cols], [0, 0], color=border_color, linewidth=border_width))         # Superior
  ax.add_line(lines.Line2D([0, cols], [rows, rows], color=border_color, linewidth=border_width))   # Inferior
  ax.add_line(lines.Line2D([0, 0], [0, rows], color=border_color, linewidth=border_width))         # Izquierdo
  ax.add_line(lines.Line2D([cols, cols], [0, rows], color=border_color, linewidth=border_width))   # Derecho


  for y in range(rows):
    for x in range(cols):
      fire_state = model._get_fire_state(x, y)

      if fire_state == FireState.CLEAR:
        face_color = 'lightgray'
        alpha = 0.7
      elif fire_state == FireState.SMOKE:
        face_color = 'darkgray'
        alpha = 0.8
      elif fire_state == FireState.FIRE:
        face_color = 'orange'
        alpha = 0.9

      rect = patches.Rectangle(
          (x, y), 1, 1,
          facecolor=face_color,
          edgecolor='black',
          linewidth=0.5,
          alpha=alpha
      )
      ax.add_patch(rect)

      walls = model.grid_data[y][x]

      wall_positions = [([x, x + 1], [y, y]),        # Arriba
                        ([x + 1, x + 1], [y, y + 1]), # Derecha
                        ([x, x + 1], [y + 1, y + 1]), # Abajo
                        ([x, x], [y, y + 1])]         # Izquierda

      for i, wall_type in enumerate(walls):
        color, linewidth, linestyle = get_wall_visual_style(wall_type)
        if color is not None:
          x_coords, y_coords = wall_positions[i]

          if linestyle == '--':
            line = lines.Line2D(
                x_coords, y_coords,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle,
                dashes=[2,2]
              )
          else:
            line = lines.Line2D(
                x_coords, y_coords,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle
              )
          ax.add_line(line)

  ax.set_xticks(range(cols + 1))
  ax.set_yticks(range(rows + 1))
  ax.grid(True, alpha=0.2, color='blue')

  for poi in model.active_pois:
    if poi.type == POIType.VICTIM:
      if poi.revealed:
        color = 'gold'
        alpha = 1.0
      else:
        color = 'yellow'
        alpha = 0.9
      marker = 'o'
      size = 300
    else:
      color = 'purple'
      marker = 's'
      size = 250
      alpha = 0.9


    ax.scatter(poi.x + 0.5, poi.y + 0.5,
              color=color,
              s=size,
              marker=marker,
              edgecolors='black',
              linewidth=2,
              alpha=alpha,
              zorder=10)  # Encima de todo

    # Agregar número del POI
    ax.text(poi.x + 0.5, poi.y + 0.5, str(poi.id),
            ha='center', va='center',
            color='black', fontweight='bold', fontsize=8,
            zorder=11)  # Encima del círculo

draw_grid(ax, model)



def animate(i):
  model.step()
  draw_grid(ax, model)
  return []

anim = animation.FuncAnimation(fig, animate, frames=100, interval=1000)
plt.show()

print("\n=== COMPARACIÓN DE ACCESO A DATOS ===")
print("Con listas anidadas:")
print(f"  grid_data[0][0] = {grid_layout[0][0]}")

anim