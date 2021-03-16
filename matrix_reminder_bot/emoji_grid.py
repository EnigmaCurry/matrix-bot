import numpy as np
import emoji
import sys
import random
import math
import re

circle_emoji = np.array(
    [ord(emoji.emojize(f":{color}_circle:")) for color in [
        "red","orange","yellow","green","blue",
        "purple","brown","black","white"]])

warning_emoji = emoji.emojize(":warning:")

## memoize emoji code numbers - don't use the actual unicode code points, just
## assign an incrementing ID number, so that we can use normal integers in
## numpy.
EMOJI_MAP={warning_emoji: 0}
EMOJI_ID_MAP={0: warning_emoji}
def get_emoji_id(chars):
    try:
        ID = EMOJI_MAP[chars]
    except KeyError:
        ID = len(EMOJI_MAP)
        EMOJI_MAP[chars] = ID
        EMOJI_ID_MAP[ID] = chars
    return ID

def grid_str(array):
    "Convert numpy grid to a string of emoji text"
    if len(array.shape) < 2:
        return "".join([EMOJI_ID_MAP[x] for x in array])
    elif len(array.shape) < 3:
        lines = []
        for row in array:
            lines.append("".join([EMOJI_ID_MAP[x] for x in row]))
        return "\n".join(lines)
    else:
        raise NotImplementedError("Not implemented for >2 dimensions")

def grid_from_text(text, **args):
    text = text.strip().replace(" ","")
    width = 0
    height = 0
    chars = []
    for line in text.splitlines():
        if len(line) > 0:
            chars.extend(line)
            height += 1
            if width and width != len(line):
                raise AssertionError("2D input must have rectangular shape")
            width = len(line)
    grid = np.array([get_emoji_id(e['emoji']) for e in \
                     emoji.emoji_lis("".join(chars))]).reshape(height, width)
    return grid

def stacked_row(row, **args):
    size=len(row)
    grid = np.zeros(shape=(size, size), dtype=int)
    for r in range(size):
        grid[r] = np.array(row, dtype=int)
    return grid

def progressive(chars, **args):
    size = len(chars)
    grid = np.zeros(shape=(size, size), dtype=int)
    for r in range(size):
        row = []
        for c in range(size):
            row.append(chars[min(c, r)])
        grid[r] = np.array(row, dtype=int)
    return grid

def top_mirror(in_grid, **args):
    grid = in_grid.copy()
    middle = math.ceil(len(grid) / 2) - 1
    for r in range(len(grid)):
        b = len(grid) - r
        if r > middle:
            grid[r] = grid[b-1]
    return grid

def left_mirror(in_grid, **args):
    return np.rot90(top_mirror(np.rot90(in_grid, -1)))

def four_mirror_square(in_grid, **args):
    top_left = in_grid
    bottom_left = np.rot90(top_left,1)
    bottom_right = np.rot90(top_left,2)
    top_right = np.rot90(top_left,3)
    grid = np.zeros(shape=((len(in_grid)*2)-1,(len(in_grid)*2)-1), dtype=int)
    grid[0:len(in_grid), 0:len(in_grid)] = top_left
    grid[len(in_grid)-1:, 0:len(in_grid)] = bottom_left
    grid[len(in_grid)-1:, len(in_grid)-1:] = bottom_right
    grid[0:len(in_grid), len(in_grid)-1:] = top_right
    return grid

def roll_rows(grid, roll=1, **args):
    grid = grid.copy()
    for r in range(len(grid)):
        grid[r] = np.roll(grid[r], roll*r)
    return grid

def join_right(grid1, grid2, **args):
    return np.concatenate((grid1, grid2), axis=1, dtype=int)

def join_bottom(grid1, grid2, **args):
    return np.concatenate((grid1, grid2), axis=0, dtype=int)

def quad(grid):
    return join_bottom(join_right(grid, grid), join_right(grid, grid))

def quad_mirror(in_grid, **args):
    print(in_grid.shape)
    print(f"0:{in_grid.shape[0]}, 0:{in_grid.shape[1]}")
    top_left = in_grid
    bottom_left = np.flip(in_grid, 0)
    top_right = np.flip(in_grid, 1)
    bottom_right = np.flip(top_right, 0)
    grid = np.zeros(shape=(top_left.shape[0]*2, top_left.shape[1]*2), dtype=int)
    grid[0:in_grid.shape[0], 0:in_grid.shape[1]] = top_left
    grid[in_grid.shape[0]:in_grid.shape[0]*2, in_grid.shape[1]:in_grid.shape[1]*2] = bottom_right
    grid[in_grid.shape[0]:in_grid.shape[0]*2, 0:in_grid.shape[1]] = bottom_left
    grid[0:in_grid.shape[0], in_grid.shape[1]:in_grid.shape[1]*2] = top_right
    return grid

grid1 = lambda c: stacked_row(c)
grid2 = lambda c: roll_rows(grid1(c))
grid3 = lambda c: four_mirror_square(progressive(c))
grid4 = lambda c: four_mirror_square(grid3(c))
grid4X = grid4x = lambda c: four_mirror_square(grid4(c))
grid5 = lambda c: join_right(join_bottom(np.flip(grid2(c), 1), grid1(c)),
                             join_bottom(grid2(c), np.flip(grid1(c), 1)))
grid6 = lambda c: join_right(top_mirror(grid5(c)), top_mirror(grid5(c)))

gridz = gridZ = lambda c: roll_rows(grid3(c), -1)
gridm = gridM = lambda c: np.rot90(top_mirror(gridZ(c)))
gridn = gridN = lambda c: np.rot90(gridZ(c))
gridw = gridW = lambda c: np.flip(gridM(c))
gridx = gridX = lambda c: np.roll(top_mirror(grid5(c)), int(0.5 * (-1 * len(grid5(c)))), axis=1)
grid2d = grid2D = lambda args: quad_mirror(grid_from_text(args))

def emoji_grid(args: str, variation: str = 'grid1'):
    if variation == 'grid':
        variation = "grid2"
    variation_pattern = re.compile("^grid[a-zA-Z0-9]*$")
    try:
        if not variation_pattern.match(variation):
            raise AssertionError("not a valid variation")
        func = globals()[variation]
    except (KeyError, AssertionError) as e:
        variations = [func for func in globals() if variation_pattern.match(str(func))]
        raise NotImplementedError(
            f"Sorry, {variation} is not implemented. "
            f"Try these other variations: {', '.join(variations)}")
    if re.match('^grid2d$', variation, re.I):
        ## Pre-generate IDs for all emoji:
        grid = func(args)
    else:
        grid = func(np.array([get_emoji_id(e['emoji']) for e in emoji.emoji_lis(args)], dtype=int))
    grid = grid_str(grid)
    return grid

if __name__ == "__main__":
    variation = sys.argv[1]
    args = "".join(sys.argv[2:])
    if variation == "grid2D":
        args = """
        🍄💯👅
        🤖👽😹
        """
    print(emoji_grid(emoji.emojize(args, use_aliases=True), variation=sys.argv[1]))
