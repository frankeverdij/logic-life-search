import re
import copy
from src.rules import rulestring_from_rule
from src.logging import log
from src.utilities import format_carriage_returns, make_grid
from src.literal_manipulation import standard_form_literal
from src.sat_solvers import Status


def parse_input_string(input_string):
    """Parses a search pattern given as a string"""

    log("Parsing input pattern...", 1)

    input_string = format_carriage_returns(input_string)

    # Remove any comments
    input_string = re.sub('#.*', '', input_string)

    # Remove any trailing or leading whitespace and commas
    input_string = input_string.strip(" ,\t\n")

    # Break down string into list-of-lists-of-lists
    split_by_generation = re.split(
        r"[ ,\t]*\n(?:[ ,\t]*\n)+[ ,\t]*",  # Split on at least two newlines and any spaces, commas or tabs
        input_string
    )
    split_by_line = [
        re.split(
            r"[ ,\t]*\n[ ,\t]*",  # Split on single newline and any amount of commas or spaces
            generation
        )
        for generation in split_by_generation]
    grid = [[
        re.split(
            r"[ ,\t]+",  # Split on any amount of commas or spaces
            line
        )
        for line in generation] for generation in split_by_line]

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
    ignore_transition = [[[(cell[-1] in "'’")
                           for cell in row] for row in generation] for generation in grid]
    grid = [[[cell.rstrip("'’")  # The "'"s are now unnecessary
              for cell in row] for row in generation] for generation in grid]

    log("Done\n", -1)

    return grid, ignore_transition


def make_rle(grid, solution, background_grid=None, rule=None, determined=None, show_background=None):
    """Turn a search pattern into nicely formatted string form"""
    log('Format: RLE')

    grid = copy.deepcopy(grid)

    width = len(grid[0][0])
    height = len(grid[0])

    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if cell in solution:
                    grid[t][y][x] = "o"
                else:
                    grid[t][y][x] = "b"

    rle_string = "x = " + str(width) + ", y = " + str(height)

    if rule is not None:
        for transition in rule:
            rule[transition] = 1 if rule[transition] in solution else -1
        rle_string += ", rule = " + rulestring_from_rule(rule)

    rle_string += "\n"

    rle_string += "$\n".join("".join(line) for line in grid[0])

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
                    if cell in solution:
                        background_grid[t][y][x] = "o"
                    else:
                        background_grid[t][y][x] = "b"

        rle_string += "\n\n".join(
            "$\n".join("".join(line) for line in generation) for generation in background_grid) + "\n"

    return rle_string


def make_csv(
        grid,
        ignore_transition=None,
        background_grid=None,
        background_ignore_transition=None,
        rule=None,
        determined=None,
        show_background=None
):
    """Turn a search pattern in list form into nicely formatted csv string"""

    log('Format: csv')

    grid = space_evenly(grid, ignore_transition)

    csv_string = ""

    if rule is not None:
        csv_string += "Rule = " + rulestring_from_rule(rule) + "\n"

    csv_string += "\n".join(",".join(line) for line in grid[0]) + "\n"

    if not determined:
        csv_string += "\n" + "\n\n".join(
            "\n".join(",".join(line) for line in generation) for generation in grid[1:]) + "\n"

    if show_background:
        csv_string += "\nBackground:\n"
        background_grid = space_evenly(background_grid, background_ignore_transition)
        csv_string += "\n" + "\n\n".join(
            "\n".join(",".join(line) for line in generation) for generation in background_grid) + "\n"

    return csv_string


def space_evenly(grid, ignore_transition=None):
    grid = [[[str(cell) for cell in row] for row in generation] for generation in grid]
    if ignore_transition is None:
        ignore_transition = make_grid(False, template=grid)

    lengths = []
    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if x != 0:
                    lengths.append(len(cell) + ignore_transition[t][y][x - 1])

    length_first_column = max([max([
        len(row[0])
        for row in generation]) for generation in grid])
    length_other_columns = max(lengths) if lengths else 0
    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                if x == 0:
                    grid[t][y][x] = " " * (length_first_column - len(cell)) + cell
                else:
                    grid[t][y][x] = " " * (length_other_columns - len(cell) - ignore_transition[t][y][x - 1]) + \
                                    grid[t][y][x]
                if ignore_transition[t][y][x]:
                    grid[t][y][x] += "'"

    return grid

lookup_block = {
        0 : ' ' , 1 : '\u2598', 2 : '\u259d', 3 : '\u2580',
        4 : '\u2596', 5 : '\u258c', 6 : '\u259e', 7 : '\u259b',
        8 : '\u2597', 9 : '\u259a', 10 : '\u2590', 11 : '\u259c',
        12 : '\u2584', 13 : '\u2599', 14 : '\u259f', 15 : '\u2588'
        }

def make_blk(
        grid,
        background_grid=None,
        rule = None,
        determined = None,
        show_background = None,
):
    """Turn a search pattern in unicode block form"""

    log('Format: csv')

    grid = copy.deepcopy(grid)

    width = len(grid[0][0])
    height = len(grid[0])
    period = len(grid)
    bitmap = [[[0 for i in range(width)] for j in range(height)] for k in range(period)]

    for t, generation in enumerate(grid):
        for y, row in enumerate(generation):
            for x, cell in enumerate(row):
                assert cell in ["0","1"], "Cell not equal to 0 or 1 in RLE format"
                if cell == "1":
                    bitmap[t][y][x] = 1

    blk_string = "x = " + str(width) + ", y = " + str(height)

    if rule != None:
        blk_string += ", rule = " + rulestring_from_rule(rule)

    block = []
    for i in range(0,height,2) :
        for j in range(0,width) :
            key = 3 * bitmap[0][i][j]
            key += 12 * bitmap[0][i+1][j] if i+1<height else 0
            block.append(lookup_block[key])
        block.append('\n')
    blk_string += '\n' + "".join(block)
    return blk_string

def clauses_to_dimacs(clauses, number_of_variables):
    log('Writing clauses into DIMACS format ...', 1)
    dimacs = f"p cnf {number_of_variables} {len(clauses)}\n" + "".join(
        ' '.join(str(literal) for literal in clause) + ' 0\n' for clause in clauses)
    log('Done\n', -1)
    return dimacs


def format_dimacs_output(dimacs_output):
    lines = dimacs_output.strip('\n').split('\n')

    statuses = [line[2:] for line in lines if line[0] == 's']
    variable_lines = [line[2:] for line in lines if line[0] == 'v']

    if len(statuses) != 1:
        raise Exception('Wrong number of status lines')
    if statuses[0] == 'UNSATISFIABLE':
        return Status.UNSAT, None
    elif statuses[0] == 'SATISFIABLE':
        solution = set(int(literal) for line in variable_lines for literal in line.split() if literal != '0')
        return Status.SAT, solution
    else:
        raise Exception('Unknown exit status for SAT solver')

