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

import math

from consts import Consts

# Super-class of Cell and Player
# Handles physical attributes and actions
class Cell():
    def __init__(self, id = None, pos = [0, 0], veloc = [0, 0], radius = 5):
        # ID to judge Player or free particle
        self.id = id
        # Variables to hold current position
        self.pos = pos
        # Variables to hold current velocity
        self.veloc = veloc
        # Variables to hold size
        self.radius = radius

        # Properties
        self.collide_group = None
        self.dead = False

    # Methods
    def distance_from(self, other):
        """Calculate the distance from another cell.

        Args:
            other: another cell.
        Returns:
            the minimum distance.

        """
        dx = self.pos[0] - other.pos[0]
        dy = self.pos[1] - other.pos[1]
        min_x = min(abs(dx), abs(dx + Consts["WORLD_X"]), abs(dx - Consts["WORLD_X"]))
        min_y = min(abs(dy), abs(dy + Consts["WORLD_Y"]), abs(dy - Consts["WORLD_Y"]))
        return (min_x ** 2 + min_y ** 2) ** 0.5

    def collide(self, other):
        """Determine if it collides with another cell.

        Args:
            other: another cell.
        Returns:
            True / False.

        """
        return self.distance_from(other) < self.radius + other.radius

    def area(self):
        """Calculate the area of the cell.

        Args:
            
        Returns:
            the area of the cell.

        """
        return math.pi * self.radius * self.radius

    def stay_in_bounds(self):
        """Make the out-of-bounds cell stay within the bounds.

        Args:
            
        Returns:
            

        """
        if self.pos[0] < 0:
            self.pos[0] += Consts["WORLD_X"]
        elif self.pos[0] > Consts["WORLD_X"]:
            self.pos[0] -= Consts["WORLD_X"]

        if self.pos[1] < 0:
            self.pos[1] += Consts["WORLD_Y"]
        elif self.pos[1] > Consts["WORLD_Y"]:
            self.pos[1] -= Consts["WORLD_Y"]

    def limit_speed(self):
        """Enforce speed limits.

        Args:
            
        Returns:
            

        """
        if self.veloc[0] > Consts["MAX_VELOC"]:
            self.veloc[0] = Consts["MAX_VELOC"]
        elif self.veloc[0] < -Consts["MAX_VELOC"]:
            self.veloc[0] = -Consts["MAX_VELOC"]

        if self.veloc[1] > Consts["MAX_VELOC"]:
            self.veloc[1] = Consts["MAX_VELOC"]
        elif self.veloc[1] < -Consts["MAX_VELOC"]:
            self.veloc[1] = -Consts["MAX_VELOC"]

    def move(self, frame_delta):
        """Move the cell according to its velocity.

        Args:
            frame_delta: Time interval between two frames.
        Returns:
            

        """
        self.collide_group = None
        # Adjust the position, according to velocity.
        self.pos[0] += self.veloc[0] * frame_delta
        self.pos[1] += self.veloc[1] * frame_delta
        self.stay_in_bounds()
        self.limit_speed()

    def copy(self):
        """Returns a copy of current cell

        Args:
            
        Returns:
            the copy

        """
        res = Cell(self.id, self.pos[:], self.veloc[:], self.radius)
        res.dead = self.dead
        return res
