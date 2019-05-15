#!/usr/bin/env python3

#####################################################
#                                                   #
#     ______        _______..___  ___.   ______     #
#    /  __  \      /       ||   \/   |  /  __  \    #
#   |  |  |  |    |   (----`|  \  /  | |  |  |  |   #
#   |  |  |  |     \   \    |  |\/|  | |  |  |  |   #
#   |  `--'  | .----)   |   |  |  |  | |  `--'  |   #
#    \______/  |_______/    |__|  |__|  \______/    #
#                                                   #
#                                                   #
#####################################################

# This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import random
import math

from consts import Consts
from cell import Cell

import copy

class World():
    def __init__(self, player0, player1, names=None):
        # Variables and setup
        self.cells_count = 0
        # Init
        self.new_game()
        self.player0 = player0
        self.player1 = player1
        self.names = names

    # Methods
    def new_game(self):
        self.cells = [] # Array of cells
        self.frame_count = 0
        self.database = []
        self.result = None
        # Define the players first
        self.cells.append(Cell(0, [Consts["WORLD_X"] / 4, Consts["WORLD_Y"] / 2], [0, 0], 30))
        self.cells.append(Cell(1, [Consts["WORLD_X"] / 4 * 3, Consts["WORLD_Y"] / 2], [0, 0], 30))
        # Generate a bunch of random cells
        for i in range(Consts["CELLS_COUNT"]):
            if i < 4:
                rad = 3 + (random.random() * 3) # Small cells
            elif i < 10:
                rad = 20 + (random.random() * 8) # Big cells
            else:
                rad = 4 + (random.random() * 18) # Everything else
            ang = random.random() * 2 * math.pi
            x = Consts["WORLD_X"] * random.random()
            y = Consts["WORLD_Y"] * random.random()
            cell = Cell(i + 2, [x, y], [(random.random() - 0.5) * 2, (random.random() - 0.5) * 2], rad)
            self.cells.append(cell)

    def game_over(self, loser):
        self.result = {
            "players": self.names,
            "winner": 1 - loser,
            "data": self.database,
            "saved": False
        }
        print("Winner Winner Chicken Dinner!")
        print("Player {} dead".format(loser))

    def eject(self, player, theta):
        if player.dead or theta == None:
            return
        # Reduce force in proportion to area
        fx = math.sin(theta)
        fy = math.cos(theta)
        # Push player
        new_veloc_x = player.veloc[0] + Consts["DELTA_VELOC"] * fx * (1 - Consts["EJECT_MASS_RATIO"])
        new_veloc_y = player.veloc[1] + Consts["DELTA_VELOC"] * fy * (1 - Consts["EJECT_MASS_RATIO"])
        player.veloc[0] -= Consts["DELTA_VELOC"] * fx * Consts["EJECT_MASS_RATIO"]
        player.veloc[1] -= Consts["DELTA_VELOC"] * fy * Consts["EJECT_MASS_RATIO"]
        # Shoot off the expended mass in opposite direction
        newrad = player.radius * Consts["EJECT_MASS_RATIO"] ** 0.5
        # Lose some mass (shall we say, Consts["EJECT_MASS_RATIO"]?)
        player.radius *= (1 - Consts["EJECT_MASS_RATIO"]) ** 0.5
        new_pos_x = player.pos[0] + fx * (player.radius + newrad)
        new_pos_y = player.pos[1] + fy * (player.radius + newrad)
        new_cell = Cell(len(self.cells), [new_pos_x, new_pos_y], [new_veloc_x, new_veloc_y], newrad)
        new_cell.stay_in_bounds()
        new_cell.limit_speed()
        self.cells.append(new_cell)

    def absorb(self, collision):
        # Calculate total momentum and mass
        mass = sum(self.cells[ele].area() for ele in collision)
        px = sum(self.cells[ele].area() * self.cells[ele].veloc[0] for ele in collision)
        py = sum(self.cells[ele].area() * self.cells[ele].veloc[1] for ele in collision)
        # Determine the biggest cell
        collision.sort(key = lambda ele: self.cells[ele].radius)
        biggest = collision.pop()
        self.cells[biggest].radius = (mass / math.pi) ** 0.5
        self.cells[biggest].veloc[0] = px / mass
        self.cells[biggest].veloc[1] = py / mass
        for ele in collision:
            self.cells[ele].dead = True
            # If we just killed the player, Game over
            if self.cells[ele].id <= 1:
                self.game_over(ele)

    def update(self, frame_delta):
        allcells = [cell for cell in self.cells if not cell.dead]
        print(len(allcells))
        # Save
        self.database.append(copy.deepcopy(self.cells))
        # New frame
        self.frame_count += 1
        for cell in self.cells:
            if not cell.dead:
                cell.move(frame_delta)
        # Detect collisions
        collisions = []
        for i in range(len(self.cells)):
            if self.cells[i].dead:
                continue
            for j in range(i + 1, len(self.cells)):
                if not self.cells[j].dead and self.cells[i].collide(self.cells[j]):
                    if self.cells[i].collide_group == None == self.cells[j].collide_group:
                        self.cells[i].collide_group = self.cells[j].collide_group = len(collisions)
                        collisions.append([i, j])
                    elif self.cells[i].collide_group != None == self.cells[j].collide_group:
                        collisions[self.cells[i].collide_group].append(j)
                        self.cells[j].collide_group = self.cells[i].collide_group
                    elif self.cells[i].collide_group == None != self.cells[j].collide_group:
                        collisions[self.cells[j].collide_group].append(i)
                        self.cells[i].collide_group = self.cells[j].collide_group
                    elif self.cells[i].collide_group != self.cells[j].collide_group:
                        collisions[self.cells[i].collide_group] += collisions[self.cells[j].collide_group]
                        for ele in collisions[self.cells[j].collide_group]:
                            self.cells[ele].collide_group = self.cells[i].collide_group
                        collisions[self.cells[j].collide_group] = []
        # Run absorbs
        for collision in collisions:
            if collision != []:
                self.absorb(collision)
        # Eject!
        allcells = [cell for cell in self.cells if not cell.dead]
        self.cells_count = len(allcells)

        theta0 = theta1 = None
        try:
            theta0 = self.player0.strategy(copy.deepcopy(allcells))
        except:
            self.game_over(0)
        try:
            theta1 = self.player1.strategy(copy.deepcopy(allcells))
        except:
            self.game_over(1)

        if isinstance(theta0, (int, float, type(None))):
            self.eject(self.cells[0], theta0)
        else:
            self.game_over(0)
        if isinstance(theta1, (int, float, type(None))):
            self.eject(self.cells[1], theta1)
        else:
            self.game_over(1)
