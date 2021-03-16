import numpy as np
import emoji
import sys
import random
import math

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

def str_2d(array):
    lines = []
    for row in array:
        lines.append("".join([EMOJI_ID_MAP[x] for x in row]))
    return "\n".join(lines)

def grid_from_text(chars, positions, **args):
        print(positions)

def stacked_row_grid(row, max_size=4, **args):
    size=min(len(row), max_size)
    if len(row) > size:
        row = np.array(random.sample(list(row), size), dtype=np.int)
    grid = np.zeros(shape=(size, size), dtype=np.int)
    for r in range(size):
        grid[r] = row
    return grid

def progressive_grid(chars, **args):
    size = len(chars)
    grid = np.zeros(shape=(size, size), dtype=np.int)
    for r in range(size):
        row = []
        for c in range(size):
            row.append(chars[min(c, r)])
        grid[r] = np.array(row, dtype=np.int)
    return grid

def top_mirror(in_grid, **args):
    grid = in_grid.copy()
    middle = math.ceil(len(grid) / 2) - 1
    for r in range(len(grid)):
        b = len(grid) - r
        if r > middle:
            grid[r] = grid[b-1]
    return grid

def four_mirror(in_grid, **args):
    top_left = in_grid
    bottom_left = np.rot90(top_left,1)
    bottom_right = np.rot90(top_left,2)
    top_right = np.rot90(top_left,3)
    grid = np.zeros(shape=((len(in_grid)*2)-1,(len(in_grid)*2)-1), dtype=np.int)
    grid[0:len(in_grid), 0:len(in_grid)] = top_left
    grid[len(in_grid)-1:, 0:len(in_grid)] = bottom_left
    grid[len(in_grid)-1:, len(in_grid)-1:] = bottom_right
    grid[0:len(in_grid), len(in_grid)-1:] = top_right
    return grid


def roll_grid_rows(grid, roll=1, **args):
    grid = grid.copy()
    for r in range(len(grid)):
        grid[r] = np.roll(grid[r], roll*r)
    return grid

gridZ = lambda c: np.flip(roll_grid_rows(four_mirror((progressive_grid(c)))), 1)

def emoji_grid(args: str, variation: str = 'grid1'):
    chars = np.array([get_emoji_id(e['emoji']) for e in emoji.emoji_lis(args)], dtype=np.int)
    positions = [e['location'] for e in emoji.emoji_lis(args)]
    if variation == 'grid':
        variation = "grid1"
    variations = {
        'grid1': lambda c: roll_grid_rows(stacked_row_grid(c)),
        'grid2': lambda c: np.pad(roll_grid_rows(stacked_row_grid(c)), 3, 'reflect'),
        'grid3': lambda c: four_mirror(progressive_grid(c)),
        'grid4': lambda c: progressive_grid(c),
        'grid5': lambda c: roll_grid_rows(four_mirror((progressive_grid(c)))),
        'gridM': lambda c: np.rot90(top_mirror(gridZ(c))),
        'gridN': lambda c: np.rot90(gridZ(c)),
        'gridW': lambda c: np.flip(np.rot90(top_mirror(gridZ(c)))),
        'gridZ': gridZ,
        'grid2D': lambda c: grid_from_text(c, positions=positions)
    }
    try:
        func = variations[variation]
    except KeyError:
        raise NotImplementedError(
            f"Sorry, {variation} is not implemented. "
            f"Try these other variations: {', '.join(variations.keys())}")
    grid = str_2d(func(chars))
    return grid

if __name__ == "__main__":
    variation = sys.argv[1]
    in_txt = "".join(sys.argv[2:])
    print(emoji_grid(emoji.emojize(in_txt, use_aliases=True), variation=sys.argv[1]))
