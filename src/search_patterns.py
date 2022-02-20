import src.files
import src.formatting
import src.rules
import src.defaults
from src.messages import print_message
from src.literal_manipulation import variable_from_literal, negate


def search_pattern_from_string(input_string, indent=0):
    """Create the grid and ignore_transition of a search pattern from the given string"""
    grid, ignore_transition = src.formatting.parse_input_string(input_string, indent=indent)

    print_message("Pattern parsed as:\n" + src.formatting.make_csv(grid, ignore_transition) + "\n", 3, indent=indent)

    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if cell not in ["0", "1", "*"]:
                    variable, negated = variable_from_literal(cell)
                    grid[t][y][x] = negate("user_input_" + variable, negated)

    return grid, ignore_transition


def blank_search_pattern(width, height, duration, indent=0):
    print_message('Creating spaceship search pattern...', 3, indent=indent)

    grid = [[["*" for _x in range(width)] for _y in range(height)] for _t in range(duration)]

    print_message("Pattern created:\n" + src.formatting.make_csv(grid) + "\n", 3, indent=indent + 1)
    print_message('Done\n', 3, indent=indent)
    return grid
