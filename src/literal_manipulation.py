import re


def variable_from_literal(literal):
    """Breaks down a literal into a variable and a flag for negation"""

    if isinstance(literal, str):
        if literal[0] == '-':
            return literal[1:], -1
        else:
            return literal, 1
    elif isinstance(literal, int):
        variable = abs(literal)
        sign = literal // variable
        return variable, sign
    else:
        raise ValueError


def implies(antecedents, consequent):
    """Creates a clause saying that the antecedent literals imply the consequent"""
    if isinstance(antecedents, int):
        antecedents = [antecedents]
    return [-antecedent for antecedent in antecedents] + [consequent]


def neighbours_from_coordinates(grid, x, y, t, t_offset=-1, background_grid=None):
    width = len(grid[0][0])
    height = len(grid[0])

    neighbours = []
    for x_offset, y_offset in [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]:
        if x + x_offset in range(width) and y + y_offset in range(height):
            neighbours.append(grid[t + t_offset][y + y_offset][x + x_offset])
        else:
            if background_grid is None:
                background_grid = [[["0"]]]
            background_width = len(background_grid[0][0])
            background_height = len(background_grid[0])
            background_duration = len(background_grid)
            neighbours.append(background_grid[(t + t_offset) % background_duration][(y + y_offset) % background_height][
                                  (x + x_offset) % background_width])

    return neighbours


def offset_background(grid, x_offset, y_offset, t_offset):
    width = len(grid[0][0])
    height = len(grid[0])
    duration = len(grid)

    offset_grid = [
        [
            [
                grid[(t + t_offset) % duration][(y + y_offset) % height][(x + x_offset) % width]
                for x in range(width)]
            for y in range(height)]
        for t in range(duration)]

    for i in range(duration):
        grid[i] = offset_grid[i]


def standard_form_literal(cell):
    """Tidies up a cell into a standard form"""

    cell = re.sub('\xe2\x80\x99', "'", cell)  # Replace alternative "'" character
    cell = re.sub("'+$", "'", cell)  # Remove duplicate "'"s
    cell = re.sub("^(--)*", "", cell)  # Cancel double "-" signs
    # Other simplifications
    replacements = {
        "-*": "*",
        "-*'": "*'",
        "-0": "1",
        "-0'": "1'",
        "-1": "0",
        "-1'": "0'"
    }
    if cell in replacements:
        cell = replacements[cell]

    return cell
