

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
import mesa

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import matplotlib.lines as lines

import pandas as pd
import seaborn as sns
import numpy as np
import random
import heapq
from enum import Enum

sns.set()
plt.rcParams['animation.html'] = 'jshtml'
plt.rcParams['figure.figsize'] = (5, 5)

wall_type = [0, 1, 2, 3, 4] # 0: none, 1: wall 1hp, 2: wall 2hp, 3: open door
                              # 4: closed door

grid_layout = [[(2, 0, 2, 2), (2, 0, 2, 0), (2, 4, 2, 0), (2, 0, 0, 4), (2, 0, 0, 0), (2, 2, 0, 0), (2, 0, 0, 2), (2, 2, 0, 0)],
               [(2, 0, 0, 2), (2, 0, 0, 0), (2, 2, 0, 0), (0, 0, 2, 2), (0, 0, 2, 0), (0, 4, 4, 0), (0, 0, 0, 4), (0, 2, 0, 0)],
               [(0, 0, 0, 3), (0, 0, 2, 0), (0, 2, 0, 0), (2, 0, 0, 2), (2, 0, 0, 0), (4, 2, 0, 0), (0, 0, 0, 2), (0, 2, 0, 0)],
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

class FireFighterRole(Enum):
  RESCUER = "rescuer"
  EXTINGUISHER = "extinguisher"

class POI:
  def __init__(self, poi_id, poi_type, x, y):
    self.id = poi_id
    self.type = poi_type
    self.x = x
    self.y = y
    self.revealed = False

class FireAgent(Agent):
  def __init__(self, unique_id, model):
    super().__init__(model)
    self.actionPoints = 4
    self.role = None
    self.target_poi = None
    self.carrying_victim = None
    self.knockout_timer = 0
    self.path = []
    self.unique_id = unique_id

  def reset_ap(self):
    self.action_points = 4

  def is_knocked_out(self):
    return self.knockout_timer > 0

  def update_knockout(self):
    if self.knockout_timer > 0:
      self.knockout_timer -= 1

  def check_knockout(self):
    fire_state = self.model._get_fire_state(self.pos[0], self.pos[1])
    if fire_state == FireState.FIRE:
      self.knockout_timer = 5

  def step(self):
    self.reset_ap()
    self.update_knockout()

    if self.is_knocked_out():
      return

    if self.role == FireFighterRole.RESCUER:
      self.rescuer_behavior()
    elif self.role == FireFighterRole.EXTINGUISHER:
      self.extinguisher_behavior()

    self.check_knockout()

  def rescuer_behavior(self):
    if self.carrying_victim:
      exits = [(0, 2), (7, 4)]
      target_exit = self.get_nearest_exit(exits)
      if target_exit:
        self.move_towards_target(target_exit)
        if self.pos == target_exit:
          print(f"Victim rescued by FireFighter {self.unique_id}!")
          self.carrying_victim = None
    elif self.target_poi:
      self.move_towards_target((self.target_poi.x, self.target_poi.y))
      if self.pos == (self.target_poi.x, self.target_poi.y):
        self.reveal_and_handle_poi()
    else:
      pass

  def extinguisher_behavior(self):
    while self.action_points > 0:
      target = self.find_nearest_fire()
      if target:
        if self.pos == target:
          self.extinguish_fire(target[0], target[1])
        else:
          moved = self.move_towards_target(target)
          if not moved:
            break
      else:
        break

  def find_nearest_fire(self):
    best_target = None
    best_distance = float('inf')

    for y in range(self.model.height):
      for x in range(self.model.width):
        fire_state = self.model._get_fire_state(x, y)
        if fire_state in [FireState.FIRE, FireState.SMOKE]:
          distance = abs(x - self.pos[0]) + abs(y - self.pos[1])
          if distance < best_distance:
            best_target = (x, y)
            best_distance = distance

    return best_target

  def extinguish_fire(self, x, y):
    fire_state = self.model._get_fire_state(x, y)

    if fire_state == FireState.FIRE:
      if self.action_points >= 2:
        self.action_points -= 2
        self.model._set_fire_state(x, y, FireState.CLEAR)
      elif self.action_points >= 1:
        self.action_points -= 1
        self.model._set_fire_state(x, y, FireState.SMOKE)
    elif fire_state == FireState.SMOKE:
      if self.action_points >= 1:
        self.action_points -= 1
        self.model._set_fire_state(x, y, FireState.CLEAR)

  def get_nearest_exit(self, exits):
    best_exit = None
    best_distance = float('inf')

    for exit in exits:
      distance = abs(exit[0] - self.pos[0]) + abs(exit[1] - self.pos[1])
      if distance < best_distance:
        best_exit = exit
        best_distance = distance

    return best_exit

  def reveal_and_handle_poi(self):
    if self.action_points > 0:
      self.model.reveal_poi(self.target_poi.x, self.target_poi.y)
      if self.target_poi.type == POIType.VICTIM and not self.target_poi in self.model.lost_victims:
        self.carrying_victim = self.target_poi
      self.target_poi = None
      self.action_points -= 1

  def move_towards_target(self, target):
    if self.action_points <= 0:
      return False

    if not self.path or (len(self.path) > 0 and self.path[-1] != target):
      self.path = self.a_star_pathfinding(self.pos, target)

    if self.path and len(self.path) > 1:
      next_pos = self.path[1]
      cost = self.get_move_cost(self.pos, next_pos)
      if self.action_points >= cost:
        wall_type, wall_dir = self.model._get_wall_between_cells(self.pos[0], self.pos[1], next_pos[0], next_pos[1])
        if wall_type == 2:
          self.chop_wall(self.pos[0], self.pos[1], wall_dir)
          return True
        elif wall_type == 1:
          self.chop_wall(self.pos[0], self.pos[1], wall_dir)
          if self.action_points >= 1:
            if self.model.grid.is_cell_empty(next_pos):
              self.model.grid.move_agent(self, next_pos)
              self.action_points -= 1
              self.path.pop(0)
              return True
        elif wall_type == 4:
          self.open_door(self.pos[0], self.pos[1], wall_dir)
          return True
        else:
          if self.model.grid.is_cell_empty(next_pos):
            self.model.grid.move_agent(self, next_pos)
            self.action_points -= cost
            self.path.pop(0)
            return True
      else:
        return False

    return False

  def get_move_cost(self, pos, next_pos):
    wall_type, _ = self.model._get_wall_between_cells(pos[0], pos[1], next_pos[0], next_pos[1])
    if wall_type == 0 or wall_type ==3:
      return 1
    elif wall_type == 1:
      return 2
    elif wall_type == 2:
      return 3
    elif wall_type == 4:
      return 2
    else:
      return float('inf')

  def chop_wall(self, x, y, direction):
    if self.action_points >= 1:
      success = self.model.damage_wall(x, y, direction)
      self.action_points -= 1

  def open_door(self, x, y, direction):
    if self.action_points >= 1 and 0 <= x < self.model.width and 0 <= y < self.model.height:
      if self.model.grid_data[y, x, direction] == 4:
        self.model.grid_data[y, x, direction] = 3
        self.action_points -= 1

  def a_star_pathfinding(self, start, goal):
    if start == goal:
      return [start]

    f_score = {start: self.heuristic(start, goal)}
    open_set = [(f_score[start], start)]
    came_from = {}
    g_score = {start: 0}

    while open_set:
      current = heapq.heappop(open_set)[1]

      if current == goal:
        path = []
        while current in came_from:
          path.append(current)
          current = came_from[current]
        path.append(start)
        path.reverse()
        return path

      neighbors = self.get_neighbors(current)
      for neighbor in neighbors:
        tentative_g_score = g_score[current] + self.get_move_cost(current, neighbor)

        if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
          came_from[neighbor] = current
          g_score[neighbor] = tentative_g_score
          f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
          heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []

  def get_neighbors(self, pos):
    x, y = pos
    neighbors = []
    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # arriba, derecha, abajo, izquierda

    for dx, dy in directions:
      nx, ny = x + dx, y + dy

      if 0 <= nx < self.model.width and 0 <= ny < self.model.height:
        neighbors.append((nx, ny))

    return neighbors

  def heuristic(self, pos, goal):
    x1, y1 = pos
    x2, y2 = goal
    return abs(x1 - x2) + abs(y1 - y2)

class FireRescueModel(Model):
  def __init__(self, grid_data):
    super().__init__()
    self.grid_data = grid_data
    height, width = grid_data.shape[:2]
    self.height = height
    self.width = width

    self.grid = SingleGrid(width, height, torus=False)
    # self.schedule = RandomActivation(self)
    self.running = True
    self.fire_states = np.full((height, width), FireState.CLEAR)
    self.step_count = 0
    self.damage_count = 0

    self.all_pois = []
    self.active_pois = []
    self.revealed_pois = []
    self.lost_victims = []
    self.rescued_victims = []

    self.current_agent_index = 0
    self.agent_list = []
    self.round_count = 0
    self.phase = "AGENT"

    self.game_over = False
    self.game_won = False
    self.game_lost = False
    self.end_reason = ""

    self._create_poi_pool()
    self._place_initial_pois()
    self._place_initial_fires()
    self.place_firefighters()

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

    # Selecciona 2 victim y 1 false_alarm
    victims = [poi for poi in self.all_pois if poi.type == POIType.VICTIM][:2]
    false_alarms = [poi for poi in self.all_pois if poi.type == POIType.FALSE][:1]
    initial_pois = victims + false_alarms
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

    self.assign_roles()

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

  def rescue_victims(self, victim_poi):
    if victim_poi.type == POIType.VICTIM:
      self.rescued_victims.append(victim_poi)
      if victim_poi in self.active_pois:
        self.active_pois.remove(victim_poi)

      self.check_win_condition()
      self.place_new_poi()
      self.assign_roles()

  def check_pois_in_danger(self):
    pois_lost = []
    for poi in self.active_pois[:]:
      fire_state = self._get_fire_state(poi.x, poi.y)
      if fire_state == FireState.FIRE:
        if poi.type == POIType.VICTIM:
          self.lost_victims.append(poi)
        self.active_pois.remove(poi)
        pois_lost.append(poi)
        self.place_new_poi()

    if len(self.lost_victims) >= 4:
      self.end_game(False, f"Derrota: {len(self.lost_victims)} victimas perdidas por fuego")

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

  def assign_roles(self):
    assignments = []
    for poi in self.active_pois:
      distances = []
      for firefighter in self.agent_list:
        if not firefighter.carrying_victim:
          distance = abs(poi.x - firefighter.pos[0]) + abs(poi.y - firefighter.pos[1])
          distances.append((distance, firefighter, poi))
      distances.sort(key=lambda x: x[0])
      assignments.extend(distances[:3])

    assigned_rescuers = set()
    poi_assignments = {}

    assignments.sort(key=lambda x: x[0])
    for distance, firefighter, poi in assignments:
      if firefighter not in assigned_rescuers and len(assigned_rescuers) < 3:
        firefighter.target_poi = poi
        firefighter.role = FireFighterRole.RESCUER
        poi_assignments[poi] = firefighter
        assigned_rescuers.add(firefighter)

    for firefighter in self.agent_list:
      if firefighter not in assigned_rescuers:
        firefighter.role = FireFighterRole.EXTINGUISHER
        firefighter.target_poi = None

  def place_firefighters(self):
    valid_positions = []

    for y in range(self.height):
      for x in range(self.width):
        if self.fire_states[y, x] != FireState.CLEAR:
          continue

        if any(poi.x == x and poi.y == y for poi in self.active_pois):
          continue

        valid_positions.append((x, y))

    selected_positions = random.sample(valid_positions, 5)
    for i, pos in enumerate(selected_positions):
      firefighter = FireAgent(i ,self)
      self.grid.place_agent(firefighter, pos)
      self.agent_list.append(firefighter)

    self.assign_roles()

  def get_current_agent(self):
    if not self.agent_list:
      return None
    return self.agent_list[self.current_agent_index]

  def agent_turn(self):
    current_agent = self.get_current_agent()
    if current_agent is None:
        self.phase = "FIRE"
        return
        
    print(f"\n-- Turn: Agent {current_agent.unique_id} ({current_agent.role.value if current_agent.role else 'No Role'}) ---")
    current_agent.update_knockout()
    current_agent.reset_ap()

    if not current_agent.is_knocked_out():
      if current_agent.role == FireFighterRole.RESCUER:
        current_agent.rescuer_behavior()
      elif current_agent.role == FireFighterRole.EXTINGUISHER:
        current_agent.extinguisher_behavior()

    current_agent.check_knockout()
    self.current_agent_index = (self.current_agent_index + 1) % len(self.agent_list)
    self.phase = "FIRE"
    self.step_count += 1

  def fire_spread_phase(self):
    print(f"\n-- FIRE SPREAD PHASE (Round {self.round_count}) ---")
    self.spread_fire_random()
    self.spread_smoke_to_fire()
    lost_pois = self.check_pois_in_danger()
    if lost_pois:
      victims_lost = sum(1 for p in lost_pois if p.type == POIType.VICTIM)
      alarms_destroyed = sum(1 for p in lost_pois if p.type == POIType.FALSE)
      print(f"¡{victims_lost} víctima(s) y {alarms_destroyed} falsa(s) alarma(s) perdidas por fuego!")
      self.assign_roles()
    self.step_count += 1
    self.phase = "AGENT"
    print(f"Damage count: {self.damage_count}")

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
        self.check_damage_loss_condition()
        return False
      elif current_wall == 1:
        self.grid_data[y, x, direction] = 0
        self.damage_count += 1
        self.check_damage_loss_condition()
        return True
      elif current_wall in [3, 4]:
        self.grid_data[y, x, direction] = 0
        self.damage_count += 1
        self.check_damage_loss_condition()
        return True
      else:
        return True

  def check_damage_loss_condition(self):
    if self.damage_count > 24:
      self.end_game(False, "Derrota: Demasiados daños")

  def check_win_condition(self):
    if len(self.rescued_victims) >= 7:
      self.end_game(True, "Victoria: 7 victimas rescatadas")

  def end_game(self, won, reason):
    self.game_over = True
    self.game_won = won
    self.game_lost = not won
    self.end_reason = reason
    self.running = False

    print(f"JUEGO TERMINADO")
    print(f"{'='*50}")
    print(f"Resultado: {reason}")
    print(f"Estadísticas finales:")
    print(f"- Víctimas rescatadas: {len(self.rescued_victims)}")
    print(f"- Víctimas perdidas: {len(self.lost_victims)}")
    print(f"- Daño estructural: {self.damage_count}")
    print(f"- Rounds jugados: {self.round_count}")

  def is_game_over(self):
    return self.game_over

  def step(self):
    if self.phase == "AGENT":
      self.agent_turn()
    elif self.phase == "FIRE":
      self.fire_spread_phase()


# El modelo debe estar disponible para importar desde Flask
model = FireRescueModel(grid_layout)

# Solo ejecutar la simulación y visualización si este archivo se ejecuta directamente
if __name__ == "__main__":
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

    border_color = 'lightblue'
    border_width = 6
    ax.add_line(lines.Line2D([0, cols], [0, 0], color=border_color, linewidth=border_width))         # Superior
    ax.add_line(lines.Line2D([0, cols], [rows, rows], color=border_color, linewidth=border_width))   # Inferior
    ax.add_line(lines.Line2D([0, 0], [0, rows], color=border_color, linewidth=border_width))         # Izquierdo
    ax.add_line(lines.Line2D([cols, cols], [0, rows], color=border_color, linewidth=border_width))   # Derecho

    exits = [(0, 2), (7, 4)]
    for exit_x, exit_y in exits:
      if 0 <= exit_x < cols and 0 <= exit_y < rows:
        exit_rect = patches.Rectangle(
          (exit_x, exit_y), 1, 1,
          facecolor='lightpink',
          edgecolor='black',
          linewidth=0.5,
          alpha=0.8,
          zorder = 1
        )
        ax.add_patch(exit_rect)

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
          alpha=alpha,
          zorder = 2
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
                dashes=[2,2],
                zorder = 5
              )
            else:
              line = lines.Line2D(
                x_coords, y_coords,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle,
                zorder = 5
              )
            ax.add_line(line)

    ax.set_xticks(range(cols + 1))
    ax.set_yticks(range(rows + 1))
    ax.grid(True, alpha=0.2, color='blue')

    for agent in model.agent_list:
      if agent.carrying_victim:
        agent_color = 'lightblue'
      elif agent.role == FireFighterRole.RESCUER:
        agent_color = 'purple'
      elif agent.role == FireFighterRole.EXTINGUISHER:
        agent_color = 'red'
      else:
        agent_color = 'gray'

      if agent.is_knocked_out():
        agent_alpha = 0.2
      else:
        agent_alpha = 0.9

      ax.scatter(agent.pos[0] + 0.5, agent.pos[1] + 0.5,
            color=agent_color,
            s=400,
            marker='^',
            edgecolors='black',
            linewidth=2,
            alpha=agent_alpha,
            zorder=8)

      ax.text(agent.pos[0] + 0.5, agent.pos[1] + 0.5, str(agent.unique_id),
          ha='center', va='center',
          color='white', fontweight='bold', fontsize=10, zorder=9)

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

