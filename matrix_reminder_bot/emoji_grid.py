import numpy as np
import emoji
import sys
import random
import math
import re
import shlex

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

def grid_from_text(text):
    text = text.strip().replace(" ","")
    width = 0
    height = 0
    chars = []
    for line in text.splitlines():
        if len(line) > 0:
            chars.extend(line)
            height += 1
            line_width = emoji.emoji_count(line)
            if width and width != line_width:
                raise AssertionError("2D input must have rectangular shape")
            else:
                width = line_width
    grid = np.array([get_emoji_id(e['emoji']) for e in \
                     emoji.emoji_lis("".join(chars))], dtype=int).reshape(height, width)
    return grid

def stacked_row(row):
    size=len(row)
    grid = np.zeros(shape=(size, size), dtype=int)
    for r in range(size):
        grid[r] = np.array(row, dtype=int)
    return grid

def progressive(chars):
    size = len(chars)
    grid = np.zeros(shape=(size, size), dtype=int)
    for r in range(size):
        row = []
        for c in range(size):
            row.append(chars[min(c, r)])
        grid[r] = np.array(row, dtype=int)
    return grid

def top_mirror(in_grid):
    grid = in_grid.copy()
    middle = math.ceil(len(grid) / 2) - 1
    for r in range(len(grid)):
        b = len(grid) - r
        if r > middle:
            grid[r] = grid[b-1]
    return grid

def left_mirror(in_grid):
    return np.rot90(top_mirror(np.rot90(in_grid, -1)))

def roll_rows(grid, roll=1):
    grid = grid.copy()
    for r in range(len(grid)):
        grid[r] = np.roll(grid[r], roll*r)
    return grid

def roll_cols(grid, roll=1):
    return np.rot90(roll_rows(np.rot90(grid)), -1)

def join_right(grid1, grid2):
    return np.concatenate((grid1, grid2), axis=1, dtype=int)

def join_bottom(grid1, grid2):
    return np.concatenate((grid1, grid2), axis=0, dtype=int)

def quad(grid):
    return join_bottom(join_right(grid, grid), join_right(grid, grid))

def mirror(in_grid, overlap=False, axis=0):
    other = np.flip(in_grid.copy(), axis)
    if axis:
        if overlap:
            other = other[0:,1:]
        return join_right(in_grid, other)
    else:
        if overlap:
            other = other[1:,0:]
        return join_bottom(in_grid, other)

def quad_mirror(in_grid, overlap=False):
    top_left = in_grid
    bottom_left = np.flip(in_grid, 0)
    top_right = np.flip(in_grid, 1)
    bottom_right = np.flip(top_right, 0)
    grid = np.zeros(shape=(top_left.shape[0]*2, top_left.shape[1]*2), dtype=int)
    if overlap:
        grid = np.zeros(shape=(top_left.shape[0]*2 - 1, top_left.shape[1]*2 - 1), dtype=int)
        grid[0:in_grid.shape[0], 0:in_grid.shape[1]] = top_left
        grid[in_grid.shape[0]:in_grid.shape[0]*2, in_grid.shape[1]:in_grid.shape[1]*2] = bottom_right[1:,1:]
        grid[in_grid.shape[0]:in_grid.shape[0]*2, 0:in_grid.shape[1]] = bottom_left[1:,0:]
        grid[0:in_grid.shape[0], in_grid.shape[1]:in_grid.shape[1]*2] = top_right[0:,1:]
    else:
        grid = np.zeros(shape=(top_left.shape[0]*2, top_left.shape[1]*2), dtype=int)
        grid[0:in_grid.shape[0], 0:in_grid.shape[1]] = top_left
        grid[in_grid.shape[0]:in_grid.shape[0]*2, in_grid.shape[1]:in_grid.shape[1]*2] = bottom_right
        grid[in_grid.shape[0]:in_grid.shape[0]*2, 0:in_grid.shape[1]] = bottom_left
        grid[0:in_grid.shape[0], in_grid.shape[1]:in_grid.shape[1]*2] = top_right
    return grid

def border(in_grid, sequence):
    grid = np.zeros(shape=(in_grid.shape[0]+len(sequence)*2,
                           in_grid.shape[1]+len(sequence)*2), dtype=int)
    for i in range(len(sequence)):
        grid[i:grid.shape[0]-i,i:grid.shape[1]-i] = get_emoji_id(sequence[i])
    grid[len(sequence):len(sequence)+in_grid.shape[0], len(sequence):len(sequence)+in_grid.shape[1]] = in_grid
    return grid

## 1D sequential input:
grid1 = lambda c: stacked_row(c)
grid2 = lambda c: roll_rows(grid1(c))
grid3 = lambda c: quad_mirror(progressive(c), overlap=True)
grid4 = lambda c: quad_mirror(grid3(c), overlap=True)
grid4X = grid4x = lambda c: quad_mirror(grid4(c), overlap=True)
grid5 = lambda c: join_right(join_bottom(np.flip(grid2(c), 1), grid1(c)),
                             join_bottom(grid2(c), np.flip(grid1(c), 1)))
grid6 = lambda c: join_right(top_mirror(grid5(c)), top_mirror(grid5(c)))
gridz = gridZ = lambda c: roll_rows(grid3(c), -1)
gridm = gridM = lambda c: np.rot90(top_mirror(gridZ(c)))
gridn = gridN = lambda c: np.rot90(gridZ(c))
gridw = gridW = lambda c: np.flip(gridM(c))
gridx = gridX = lambda c: np.roll(top_mirror(grid5(c)), int(0.5 * (-1 * len(grid5(c)))), axis=1)

## 2D grid input:
def grid2D(args):
    "2D grid input"
    # parse command and parameters on the first line
    # parse rectangular grid input on subsequent lines
    lines = args.splitlines()
    text = "\n".join(lines[1:])
    grid = grid_from_text(text)

    def parse_int(cmd, default):
        cmd = cmd[1:]
        for i in range(10):
            try:
                return int(cmd[i])
            except Exception:
                pass
        else:
            return default

    for stage in lines[0].split("|"):
        in_grid = grid.copy()
        cmd = shlex.split(stage)
        if not len(cmd):
            break
        if cmd[0] == "quad_mirror":
            grid = quad_mirror(in_grid, overlap="overlap" in cmd[1:])
        elif cmd[0] == "cat":
            times = parse_int(cmd, 1)
            for t in range(times - 1):
                if "right" in cmd[1:]:
                    grid = join_right(grid, in_grid)
                else:
                    grid = join_bottom(grid, in_grid)
        elif cmd[0] == "pad":
            chars = [e['emoji'] for e in emoji.emoji_lis("".join(cmd[1:]))]
            size = parse_int(cmd, None)
            if size is not None and len(chars) > 1:
                raise AssertionError("When you pad with a number, it only accepts ONE emoji input.")
            elif size is not None and len(chars) == 1:
                v = (get_emoji_id(chars[0]),)
                grid = np.pad(in_grid, pad_width=size, mode="constant", constant_values=v)
            elif size is not None and "mean" in cmd[1:]:
                grid = np.pad(in_grid, pad_width=size, mode="mean")
            elif size is not None:
                grid = np.pad(in_grid, pad_width=size, mode="edge")
            elif len(chars) > 0:
                grid = border(in_grid, sequence=chars)
            else:
                grid = np.pad(in_grid, pad_width=1, mode="edge")
        elif cmd[0] == "roll":
            multiple = parse_int(cmd, 1)
            if "down" in cmd[1:]:
                grid = roll_cols(grid, multiple)
            else:
                grid = roll_rows(grid, multiple)
        elif cmd[0] == "mirror":
            grid = mirror(in_grid, overlap="overlap" in cmd[1:], axis=1 if "down" not in cmd[1:] else 0)
        elif cmd[0] == "rotate":
            multiple = parse_int(cmd, 1)
            if "right" in cmd[1:]:
                multiple = -1 * multiple
            grid = np.rot90(in_grid, multiple)
        elif cmd[0] == "fortune":
            # Mystique example: fortune 30🔵 10🔴 5💶 5🥇 5🎹
            # Find all integers, all emoji, and assert quantity of each are equal:
            nums = [int(x) for x in re.findall('\d+', " ".join(cmd[1:]))]
            total = sum(nums)
            chars = [get_emoji_id(e['emoji']) for e in emoji.emoji_lis("".join(cmd[1:]))]
            if not len(nums) or len(nums) != len(chars):
                raise ValueError("fortune requires a list of: Quantity + Emoji like: 30🔵 10🔴 5💶 5🥇 5🎹")
            nums = zip(nums, chars)
            flatten = lambda t: [item for sublist in t for item in sublist]
            message = flatten([[char for _ in range(num)] for num, char in nums])
            random.shuffle(message)
            # Calculate factors to make a rectangular grid:
            def squareish_factors(n: int):
                for i in range(int(math.sqrt(n)), 0, -1):
                    if n % i == 0:
                        return (i, int(n/i))
                else:
                    raise AssertionError("Bad programmer is bad at math")
            factors = squareish_factors(total)
            print(total)
            print(factors)
            grid = np.array(message).reshape(*factors)
        elif cmd[0] == "top_mirror":
            grid = top_mirror(grid)
        elif cmd[0] == "cut":
            num = parse_int(cmd, 1)
            if "top" in cmd[1:]:
                grid = grid[0:num, 0:]
            else:
                grid = grid[0:, 0:num]
    return grid
grid2d = grid2D

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
    ## Functions either take raw args string or emoji ID array, depending on style:
    if re.match('^grid2d', variation, re.I):
        ## grid2d style passes the unparsed args directly:
        grid = func(args)
    else:
        ## Every other variant passes the parsed array of emoji ids:
        grid = func(np.array([get_emoji_id(e['emoji']) for e in emoji.emoji_lis(args)], dtype=int))
    grid = grid_str(grid)
    return grid

if __name__ == "__main__":
    variation = sys.argv[1]
    args = " ".join(sys.argv[2:])
    if variation.lower() == "grid2d":
        args = args + """
        🍄💯👅
        🤖👽😹
        """
    print(emoji_grid(emoji.emojize(args, use_aliases=True), variation=sys.argv[1]))
