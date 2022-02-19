import re
import copy
import src.rules as LLS_rules
from src.messages import print_message
from src.literal_manipulation import standard_form_literal

def parse_input_string(input_string, indent = 0):
    """Parses a search pattern given as a string"""

    print_message("Parsing input pattern...", 3, indent = indent)

    # Convert any newline format (\r, \n, \n\r, \r\n) to just \n
    if '\r' in input_string and '\n' not in input_string:
        input_string = re.sub('\r','\n',input_string)
    else:
        input_string = re.sub('\r','',input_string)

    # Remove any comments
    input_string = re.sub('#.*','',input_string)

    # Remove any trailing or leading whitespace and commas
    input_string = input_string.strip(" ,\t\n")
    # Break down string into list-of-lists-of-lists
    split_by_generation = re.split(
        r"[ ,\t]*\n(?:[ ,\t]*\n)+[ ,\t]*", # Split on at least two newlines and any spaces, commas or tabs
        input_string
    )
    split_by_line = [
        re.split(
            r"[ ,\t]*\n[ ,\t]*", # Split on single newline and any amount of commas or spaces
            generation
        )
    for generation in split_by_generation]

    grid = [[re.split(r"[ ,\t]+",  # Split on any amount of commas or spaces
                    line)
                    for line in generation]
                    for generation in split_by_line]

    # Check that the list is cuboidal
    assert (all(
               len(generation) == len(grid[0])
               for generation in grid)
            and all(all(
               len(line) == len(grid[0][0])
               for line in generation) for generation in grid)), \
           "Search pattern is not cuboidal"

    # Tidy up any weird inputs
    grid = [[[standard_form_literal(cell)
                      for cell in row] for row in generation] for generation in grid]

    # Create array which says when a "'" means that a transition should be ignored
    ignore_transition = [[[(cell[-1] == "'")
                      for cell in row] for row in generation] for generation in grid]
    grid = [[[cell.rstrip("'") # The "'"s are now unnecessary
                      for cell in line] for line in generation] for generation in grid]

    print_message("Done\n", 3, indent = indent)

    return grid, ignore_transition

def make_rle(grid, background_grid = None, rule = None, determined = None, show_background = None, indent = 0):
    """Turn a search pattern into nicely formatted string form"""

    print_message('Format: RLE', 3, indent = indent)

    grid = copy.deepcopy(grid)

    width = len(grid[0][0])
    height = len(grid[0])

    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                assert cell in ["0","1"], "Cell not equal to 0 or 1 in RLE format"
                if cell == "0":
                    grid[t][y][x] = "b"
                elif cell == "1":
                    grid[t][y][x] = "o"

    rle_string = "x = " + str(width) + ", y = " + str(height)

    if rule != None:
        rle_string += ", rule = " + LLS_rules.rulestring_from_rule(rule)

    rle_string += "\n"

    rle_string += "$\n".join("".join(line)for line in grid[0])

    rle_string += "!\n"

    if not determined:
        rle_string += "\nOther generations:\n"
        rle_string += "\n\n".join("$\n".join("".join(line) for line in generation) for generation in grid[1:]) + "\n"

    if show_background:
        rle_string += "\nBackground:\n"
        background_grid = copy.deepcopy(background_grid)

        for t, generation in enumerate(background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    assert cell in ["0","1"], "Cell not equal to 0 or 1 in RLE format"
                    if cell == "0":
                        background_grid[t][y][x] = "b"
                    elif cell == "1":
                        background_grid[t][y][x] = "o"

        rle_string += "\n\n".join("$\n".join("".join(line) for line in generation) for generation in background_grid) + "\n"


    return rle_string




def make_csv(
    grid,
    ignore_transition = None,
    background_grid = None,
    background_ignore_transition = None,
    rule = None,
    determined = None,
    show_background = None,
    indent = 0
):
    """Turn a search pattern in list form into nicely formatted csv string"""

    print_message('Format: csv', 3, indent = indent)

    grid = copy.deepcopy(grid)
    if ignore_transition == None:
        ignore_transition = [[[False for cell in row] for row in generation] for generation in grid]

    lengths = []
    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if x != 0:
                    lengths.append(len(cell) + ignore_transition[t][y][x-1])

    length_first_column = max([max([
                                    len(row[0])
                          for row in generation]) for generation in grid])
    if len(lengths) > 0:
        length_other_columns = max(lengths)
    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if x == 0:
                    grid[t][y][x] = " " * (length_first_column - len(cell)) +  cell
                else:
                    grid[t][y][x] = " " * (length_other_columns - len(cell) - ignore_transition[t][y][x-1]) +  grid[t][y][x]
                if ignore_transition[t][y][x]:
                    grid[t][y][x] += "'"

    csv_string = ""

    if rule != None:
        csv_string += "Rule = " + LLS_rules.rulestring_from_rule(rule) + "\n"

    csv_string += "\n".join(",".join(line)for line in grid[0]) + "\n"

    if not determined:
        csv_string += "\n" + "\n\n".join("\n".join(",".join(line) for line in generation) for generation in grid[1:]) + "\n"

    if show_background:
        csv_string += "\nBackground:\n"
        background_grid = copy.deepcopy(background_grid)
        if background_ignore_transition == None:
            background_ignore_transition = [[[False for cell in row] for row in generation] for generation in background_grid]

        lengths = []
        for t, generation in enumerate(background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    if x != 0:
                        lengths.append(len(cell) + background_ignore_transition[t][y][x-1])

        length_first_column = max([max([
                                        len(row[0])
                              for row in generation]) for generation in background_grid])
        if len(lengths) > 0:
            length_other_columns = max(lengths)
        for t, generation in enumerate(background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    if x == 0:
                        background_grid[t][y][x] = " " * (length_first_column - len(cell)) +  cell
                    else:
                        background_grid[t][y][x] = " " * (length_other_columns - len(cell) - background_ignore_transition[t][y][x-1]) +  background_grid[t][y][x]
                    if background_ignore_transition[t][y][x]:
                        background_grid[t][y][x] += "'"
        csv_string += "\n" + "\n\n".join("\n".join(",".join(line) for line in generation) for generation in background_grid) + "\n"


    return csv_string

