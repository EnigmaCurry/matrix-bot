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
variation_pattern = re.compile("^grid[a-zA-Z0-9]*$")
EN_emoji = list(emoji.core.unicode_codes.EMOJI_UNICODE['en'].values())

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

def grid_str(array, small=False):
    "Convert numpy grid to a string of emoji text"
    lines = []
    if len(array.shape) < 2:
        lines.append("".join([EMOJI_ID_MAP[x] for x in array]))
    elif len(array.shape) < 3:
        for row in array:
            lines.append("".join([EMOJI_ID_MAP[x] for x in row]))
    else:
        raise NotImplementedError("Not implemented for >2 dimensions")
    if small:
        # Add some text so as to defeat the 2x embiggening that Element does to emoji-only messages
        lines.append('.')
    return "\n".join(lines)

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
gridx = gridX = lambda c: quad_mirror(grid2(c))

## 2D grid input:
def grid2D(args, in_grid=None):
    "2D grid input"
    # parse command and parameters on the first line
    # parse rectangular grid input on subsequent lines
    lines = args.splitlines()
    text = "\n".join(lines[1:])
    grid = in_grid if in_grid is not None else grid_from_text(text)

    def parse_int(cmd, default):
        if type(cmd) == str:
            cmd = cmd.split(" ")
        for i in range(len(cmd)):
            try:
                return int(re.search(r'^\d+', cmd[i]).group())
            except Exception as e:
                print(e)
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
            times = parse_int(cmd[1:], 1)
            for t in range(times - 1):
                if "right" in cmd[1:]:
                    grid = join_right(grid, in_grid)
                else:
                    grid = join_bottom(grid, in_grid)
        elif cmd[0] == "pad":
            chars = [e['emoji'] for e in emoji.emoji_lis("".join(cmd[1:]))]
            size = parse_int(cmd[1:], None)
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
            multiple = parse_int(cmd[1:], 1)
            if "down" in cmd[1:]:
                grid = roll_cols(grid, multiple)
            else:
                grid = roll_rows(grid, multiple)
        elif cmd[0] == "mirror":
            grid = mirror(in_grid, overlap="overlap" in cmd[1:], axis=1 if "down" not in cmd[1:] else 0)
        elif cmd[0] == "flip":
            grid = np.flip(in_grid, axis="right" in cmd[1:])
        elif cmd[0] == "rotate":
            multiple = parse_int(cmd[1:], 1)
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
            grid = np.array(message).reshape(*factors)
        elif cmd[0] == "top_mirror":
            grid = top_mirror(grid)
        elif cmd[0] == "cut":
            num = parse_int(cmd[1:], 1)
            if "top" in cmd[1:]:
                grid = grid[0:num, 0:]
            else:
                grid = grid[0:, 0:num]
        elif cmd[0] == "small":
            pass #handled in emoji_grid
        elif cmd[0] == "random":
            width = parse_int(cmd[1], None)
            height = parse_int(cmd[2], None)
            if width is None or height is None:
                raise ValueError("Random requires width and height as integers")
            chars = []
            for i in range(width*height):
                while True:
                    r = random.choice(EN_emoji)
                    ## Only accept single character emoji
                    if len(r) == 1:
                        break
                    else:
                        print(len(r))
                chars.append(get_emoji_id(r))
            grid = np.array(chars).reshape(width, height)
        else:
            raise ValueError("grid2d missing command")
    return grid
grid2d = grid2D

def help_text():
    return f"""# Emoji Grids
Make emoji grids by creating a pipeline, each stage of the
pipeline receives input from the previous stage, like a UNIX shell:

```
!grid COMMAND [OPTIONS ...] | COMMAND [OPTIONS ...] | ....
```

## Grid commands and options:

A command consists of one stage in the overall pipeline, which is all the text
before the next `|` character, consisting of the command name (the first word)
and the list of options (all the rest of the words before the next `|`
character). If the options are listed in brackets [] the option is not required
to be specified, and shows the default value that will be used in its place.

 * `cat [right] [N=1]` - concatenate grid down or [right] N times.

    Examples:  `cat 3`, `cat right 2`

    Note: `cat` without any N specified, is identical to its input.

 * `quad_mirror [overlap]` - mirror grid veritically and horizontally.
    If `overlap` is specified, the border between will not be duplicated.

 * `pad EMOJI` - pad the input grid with a border.

    EMOJI specifies the emoji to pad. Can specify a sequence or
    a single emoji with a number multiplier.

    Examples: `pad 🎹🥇`, `pad 2🔵`
 * `roll [down] [multiple=1]` - shift each row of the grid in a cascading pattern.

    By default rows are shifted left or right. If `down` is specified, columns
    are shifted up or down instead.

    Examples: `roll`, `roll down`, `roll down 2`, `roll 3`

 * `flip [right]` - Flip the entire grid upside down, or right side over.

    Examples: `flip`, `flip right`

 * `rotate [multiple=1]` - Rotate the grid

    multiple specifies the direction and how many times. Positive goes
    counter-clockwise, while negative goes clockwise (seems backwards I know.)

 * `fortune [N EMOJI] [N EMOJI] ...` - Randomize grid positions from input

    Examples: `fortune 30🔵 10🔴 5💶 5🥇 5🎹`

 * `top_mirror` - Mirror the top half of the grid 
    (no options)

 * `cut [top]` - Chop off part of the grid.

    top specifies to cut from the top of the grid, otherwise cut from the left of the grid.

    Examples: `cut 5`, `cut top 4`

 * `small` - Force the output of the emoji to be small (Element Desktop only)

 * `random WIDTH HEIGHT` - Ignore input entirely and create a new grid of
   completely random emoji - width and height should be integer numbers.

## Grid generators

The following grid generators exist, which you may invoke as the _first_ grid command only.

{", ".join([func for func in globals() if variation_pattern.match(str(func))])}

These can be followed by any of the pipeline command from above, for example:

```
!gridW 🔵🔴💶🥇🎹 | cat 2 right | small
```

## Two dimensional input

If you don't use one of the grid generators as the first command, you can
instead provide the input grid yourself as a two dimensional array. Simply type
the command as normal, and starting on the second line type the emoji grid to
use as input. Example (this is a single message on three lines:)

```
!grid quad_mirror
```

`🤾‍♂️🤾‍♀️🏌️‍♀️🏌️‍♂️`

`🥏🎱🏓🏸`


## Examples to try yourself
 * `!grid1 👟👠🪜`
 * `!grid2 👟👠🪜`
 * `!grid2 👟👠🪜 | quad_mirror`
"""


def emoji_grid(args: str, variation: str = 'grid1'):
    if re.search("(^|\W)help($|\W)",args):
        return help_text()
    if variation == 'grid':
        variation = "grid2D"
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
        grid = grid2D(args)
    else:
        if "|" in args:
            first_stage = args.split("|")[0]
        else:
            first_stage = args
        ## Every other variant passes the parsed array of emoji ids:
        grid = func(np.array([get_emoji_id(e['emoji']) for e in emoji.emoji_lis(first_stage)], dtype=int))
        ## If there are additional stages, pass the result to grid2d:
        if "|" in args:
            rest_args = "|".join(args.splitlines()[0].split("|")[1:]).strip()
            if len(rest_args):
                grid = grid2D(rest_args, in_grid=grid)
    grid = grid_str(grid, small=re.search("(^|\W)small($|\W)",args))
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
