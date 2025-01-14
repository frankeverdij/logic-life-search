import collections
import copy
import itertools
import ast
import src.taocp_variable_scheme
import src.formatting
import src.rules
import settings
import src.files
import src.literal_manipulation
from src.logging import log
from src.literal_manipulation import variable_from_literal, neighbours_from_coordinates, implies, standard_form_literal
from src.utilities import make_grid

class UnsatInPreprocessing(Exception):
    """
    Unsatisfiability proved before SAT solver is run

    Can be called because it's impossible to continue preprocessing
    with an unsatisfiable instance (for example
    "search_pattern.force_equal('0', '1')") or just to complete more quickly.

    """
    pass


class SearchPattern:

    def __init__(
            self,
            grid,
            ignore_transition=None,
            background_grid=None,
            background_ignore_transition=None,
            rulestring=None
    ):
        self.clauses = [[1]]
        self.number_of_variables = 1

        self.grid = copy.deepcopy(grid)
        self.ignore_transition = (
            copy.deepcopy(ignore_transition)
            if (ignore_transition is not None)
            else make_grid(False, template=grid)
        )
        if background_grid is None:
            (
                background_grid,
                self.background_ignore_transition
            ) = src.formatting.parse_input_string(
                src.files.string_from_file(
                    "backgrounds/" + settings.background,
                )
            )
        else:
            self.background_ignore_transition = (
                copy.deepcopy(background_ignore_transition)
                if (background_ignore_transition is not None)
                else make_grid(False, template=background_grid)
            )

        if rulestring is None:
            rulestring = settings.rulestring
        self.grid, self.background_grid, self.rule = self.prepare_variables(grid, background_grid, rulestring)

        width = len(self.grid[0][0])
        height = len(self.grid[0])
        duration = len(self.grid)
        background_width = len(self.background_grid[0][0])
        background_height = len(self.background_grid[0])
        background_duration = len(self.background_grid)

        # Surround the grid by one cell from the background, and offset the background accordingly
        src.literal_manipulation.offset_background(self.background_grid, 1, 1, 0)
        new_grid = make_grid("0", width + 2, height + 2, duration)
        for x in range(width + 2):
            for y in range(height + 2):
                for t in range(duration):
                    if x in range(1, width + 1) and y in range(1, height + 1):
                        new_grid[t][y][x] = self.grid[t][y - 1][x - 1]
                    else:
                        new_grid[t][y][x] = self.background_grid[t % background_duration][y % background_height][
                            x % background_width]
        self.grid = new_grid
        src.literal_manipulation.offset_background(self.background_ignore_transition, 1, 1, 0)
        new_ignore_transition = make_grid("0", width + 2, height + 2, duration)
        for x in range(width + 2):
            for y in range(height + 2):
                for t in range(duration):
                    if 1 <= x <= width and 1 <= y <= height:
                        new_ignore_transition[t][y][x] = self.ignore_transition[t][y - 1][x - 1]
                    else:
                        new_ignore_transition[t][y][x] = \
                            self.background_ignore_transition[t % background_duration][y % background_height][
                                x % background_width]
        self.ignore_transition = new_ignore_transition

        self.cardinality_variables = dict()
        self.defined_cardinality_variables = set()

    def prepare_variables(self, grid, background_grid, rulestring):
        input_literals = [cell for generation in grid for row in generation for cell in row] +\
                         [cell for generation in background_grid for row in generation for cell in row]

        if rulestring[0] == '{':
            rule = ast.literal_eval(rulestring)
            input_literals += list(rule.values())

        input_variables = set(variable_from_literal(standard_form_literal(literal))[0] for literal in input_literals)

        variable_dict = {'1':1}
        numeric_variables = set()
        nonnumeric_variables = set()
        for variable in input_variables:
            if variable in ['0','*']:
                continue
            try:
                variable_int = int(variable)
                numeric_variables.add(variable_int)
                variable_dict[variable] = variable_int
            except ValueError:
                if variable != '*':
                    nonnumeric_variables.add(variable)

        self.number_of_variables = max(self.number_of_variables, max(int(variable) for variable in variable_dict))

        for variable in nonnumeric_variables:
            self.number_of_variables += 1
            variable_dict[variable] = self.number_of_variables

        variable_dict['0'] = -1

        new_grid = make_grid(None, template=grid)
        for t, generation in enumerate(grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    variable_string, sign = variable_from_literal(standard_form_literal(cell))
                    if variable_string == '*':
                        self.number_of_variables += 1
                        variable = self.number_of_variables
                    else:
                        variable = variable_dict[variable_string]
                    new_grid[t][y][x] = variable * sign

        new_background_grid = make_grid(None, template=background_grid)
        for t, generation in enumerate(background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    variable_string, sign = variable_from_literal(standard_form_literal(cell))
                    if variable_string == '*':
                        self.number_of_variables += 1
                        variable = self.number_of_variables
                    else:
                        variable = variable_dict[variable_string]
                    new_background_grid[t][y][x] = variable * sign

        if rulestring[0] == '{':
            new_rule = dict()
            for transition in rule:
                variable_string, sign = variable_from_literal(standard_form_literal(rule[transition]))
                if variable_string == '*':
                    self.number_of_variables += 1
                    variable = self.number_of_variables
                else:
                    variable = variable_dict[variable_string]
                new_rule[transition] = variable * sign
        else:
            new_rule, self.number_of_variables = src.rules.rule_from_rulestring(rulestring, self.number_of_variables)

        return new_grid, new_background_grid, new_rule

    def number_of_cells(self):
        return len(set(abs(cell) for generation in self.grid for row in generation for cell in row if
                       cell not in [1, -1]))

    def remove_redundancies(self):
        log("Removing redundant transitions...", 1)
        parents_dict = {}
        to_force_equal = []
        background_duration = len(self.background_grid)
        for t, generation in enumerate(self.background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    predecessor_cell = self.background_grid[(t - 1) % background_duration][y][x]
                    neighbours = neighbours_from_coordinates(self.background_grid, x, y, t,
                                                             background_grid=self.background_grid)
                    if not self.background_ignore_transition[t][y][x]:
                        parents = [predecessor_cell] + list(src.rules.sort_neighbours(neighbours))
                        parents_string = str(parents)
                        if parents_string in parents_dict:
                            self.background_grid[t][y][x] = parents_dict[parents_string]
                            to_force_equal.append((parents_dict[parents_string], cell))
                            self.background_ignore_transition[t][y][x] = True
                        elif all(parent in [-1, 1] for parent in parents):
                            bs_letter = ["B", "S"][[-1, 1].index(predecessor_cell)]
                            transition = src.rules.transition_from_cells(neighbours)
                            child = self.rule[bs_letter + transition]
                            if cell not in [-1, 1]:
                                self.background_grid[t][y][x] = child
                            to_force_equal.append((cell, child))
                            self.background_ignore_transition[t][y][x] = True
                            parents_dict[parents_string] = self.background_grid[t][y][x]
                        else:
                            parents_dict[parents_string] = cell
        self.force_equal(to_force_equal)
        to_force_equal = []
        for t, generation in enumerate(self.grid):
            if t > 0:
                for y, row in enumerate(generation):
                    for x, cell in enumerate(row):
                        predecessor_cell = self.grid[t - 1][y][x]
                        neighbours = neighbours_from_coordinates(self.grid, x, y, t,
                                                                 background_grid=self.background_grid)

                        if not self.ignore_transition[t][y][x]:
                            parents = [predecessor_cell] + list(src.rules.sort_neighbours(neighbours))
                            parents_string = str(parents)
                            if parents_string in parents_dict:
                                self.grid[t][y][x] = parents_dict[parents_string]
                                to_force_equal.append((parents_dict[parents_string], cell))
                                self.ignore_transition[t][y][x] = True
                            elif all(parent in [-1, 1] for parent in parents):
                                bs_letter = ["B", "S"][[-1, 1].index(predecessor_cell)]
                                transition = src.rules.transition_from_cells(neighbours)
                                child = self.rule[bs_letter + transition]
                                if cell not in [-1, 1]:
                                    self.grid[t][y][x] = child
                                to_force_equal.append((cell, child))
                                self.ignore_transition[t][y][x] = True
                                parents_dict[parents_string] = self.grid[t][y][x]
                            else:
                                parents_dict[parents_string] = cell
        self.force_equal(to_force_equal)
        log("Done\n", -1)

    def force_transition(self, grid, x, y, t, method):
        cell = grid[t][y][x]
        duration = len(grid)
        if method == 0:
            src.taocp_variable_scheme.transition_rule(self, grid, x, y, t)

        elif method == 1:
            predecessor_cell = grid[(t - 1) % duration][y][x]
            neighbours = neighbours_from_coordinates(grid, x, y, t, background_grid=self.background_grid)

            # If any four neighbours were live, then the cell is
            # dead
            for four_neighbours in itertools.combinations(neighbours, 4):
                self.clauses.append(
                    implies(four_neighbours, -cell)
                )

            # If any seven neighbours were dead, the cell is dead
            for seven_neighbours in itertools.combinations(neighbours, 7):
                self.clauses.append(
                    implies([-neighbour for neighbour in seven_neighbours], -cell)
                )

            # If the cell was dead, and any six neighbours were
            # dead, the cell is dead
            for six_neighbours in itertools.combinations(neighbours, 6):
                self.clauses.append(
                    implies([-predecessor_cell] + [-neighbour for neighbour in six_neighbours], -cell)
                )

            # If three neighbours were alive and five were dead,
            # then the cell is live
            for three_neighbours in itertools.combinations(neighbours, 3):
                neighbours_counter = collections.Counter(neighbours)
                neighbours_counter.subtract(three_neighbours)
                three_neighbours, five_neighbours = list(three_neighbours), list(neighbours_counter.elements())

                clause = implies(three_neighbours + [-neighbour for neighbour in five_neighbours], cell)
                self.clauses.append(clause)

            # Finally, if the cell was live, and two neighbours
            # were live, and five neighbours were dead, then the
            # cell is live (independently of the final neighbour)
            for two_neighbours in itertools.combinations(neighbours, 2):
                neighbours_counter = collections.Counter(neighbours)
                neighbours_counter.subtract(two_neighbours)
                two_neighbours, five_neighbours = list(two_neighbours), list(neighbours_counter.elements())[1:]

                clause = implies(
                    [predecessor_cell] + two_neighbours + [-neighbour for neighbour in five_neighbours], cell)
                self.clauses.append(clause)

        elif method == 2:

            predecessor_cell = grid[(t - 1) % duration][y][x]
            neighbours = neighbours_from_coordinates(self.grid, x, y, t, background_grid=self.background_grid)

            states = [-1, 1]

            # For each combination of neighbourhoods
            for predecessor_cell_alive in states:
                for neighbours_alive in itertools.product(states, repeat=8):
                    p = "S" if predecessor_cell_alive == 1 else "B"
                    transition = src.rules.transition_from_cells(neighbours_alive)
                    transition_literal = self.rule[p + transition]

                    self.clauses.append(implies(
                        [transition_literal] + [predecessor_cell * predecessor_cell_alive] +
                        [neighbours[i] * neighbours_alive[i] for i in range(8)], cell))
                    self.clauses.append(implies(
                        [-transition_literal] + [predecessor_cell * predecessor_cell_alive] +
                        [neighbours[i] * neighbours_alive[i] for i in range(8)], -cell))

    def force_evolution(self, method=None):
        """Adds clauses that force the search pattern to obey the transition rule"""

        # Methods:
        # 0. An implementation of the scheme Knuth describes in TAOCP Volume 4, Fascicle 6, solution to exercise 65b
        # (57 clauses and 13 auxiliary variables per cell)
        # 1. An implementation of the naive scheme Knuth gives in the solution to exercise 65a
        # (190 clauses and 0 auxiliary variables per cell)
        # 2. A very naive scheme just listing all possible predecessor neighbourhoods
        # (512 clauses and 0 auxiliary variables per cell)

        log("Enforcing evolution rule...", 1)

        if method is None:
            if src.rules.rulestring_from_rule(self.rule) == "B3/S23":
                method = settings.life_encoding_method
            else:
                method = 2  # Default method
        assert method in range(3), "Method not found"
        assert method == 2 or src.rules.rulestring_from_rule(
            self.rule) == "B3/S23", "Rules other than Life can only use method 2"

        log("Method: " + str(method))
        starting_number_of_clauses = len(self.clauses)
        # Iterate over all cells not in the first generation
        for t, generation in enumerate(self.grid):
            if t > 0:
                for y, row in enumerate(generation):
                    for x, cell in enumerate(row):
                        if not self.ignore_transition[t][y][x]:
                            self.force_transition(self.grid, x, y, t, method)

        # Iterate over all background cells
        for t, generation in enumerate(self.background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    if not self.background_ignore_transition[t][y][x]:
                        self.force_transition(self.background_grid, x, y, t, method)

        log("Number of clauses used: " + str(len(self.clauses) - starting_number_of_clauses))
        log("Done\n", -1)

    def force_change(self, times):
        """Adds clauses forcing at least one cell to change between specified generations"""

        (t_0, t_1) = times
        log("Forcing at least one cell to change between generations " + str(t_0) + " and " + str(t_1) + " ...", 1)

        starting_number_of_clauses = len(self.clauses)

        width = len(self.grid[0][0])
        height = len(self.grid[0])

        self.force_unequal([(self.grid[t_0][y][x], self.grid[t_1][y][x]) for x in range(width) for y in range(height)])

        log("Number of clauses used: " + str(len(self.clauses) - starting_number_of_clauses))
        log("Done\n", -1)

    def force_distinct(self, solution, determined=False):
        """Force search_pattern to have at least one difference from given solution"""

        log("Forcing pattern to be different from solution...", 1)

        variables = set()

        for t, generation in enumerate(self.grid):
            if t == 0 or not determined:
                for row in generation:
                    for cell in row:
                        variables.add(abs(cell))

        for generation in self.background_grid:
            for row in generation:
                for cell in row:
                    variables.add(abs(cell))

        for literal in self.rule.values():
            variables.add(abs(literal))

        self.clauses.append([-literal for literal in solution if abs(literal) in variables])
        log("Number of clauses used: 1")
        log("Done\n", -1)

    def get_cardinality_variable(self, literals, at_least):
        if (literals, at_least) not in self.cardinality_variables:
            self.number_of_variables += 1
            self.cardinality_variables[(literals, at_least)] = self.number_of_variables
        return self.cardinality_variables[(literals, at_least)]

    def define_cardinality_variable(self, literals, at_least, preprocessing=True):
        """Generates clauses defining a cardinality variable"""

        if preprocessing:
            at_least -= literals.count(1)
            literals = tuple(sorted(literal for literal in literals if abs(literal) != 1))
        name = self.get_cardinality_variable(literals, at_least)

        if (literals, at_least) not in self.defined_cardinality_variables:
            self.defined_cardinality_variables.add((literals, at_least))

            max_literals = len(literals)  # The most literals that could be true
            max_literals_1 = max_literals // 2
            literals_1 = literals[:max_literals_1]
            variables_to_define_1 = []  # A list of variables we need to define
            max_literals_2 = max_literals - max_literals_1
            literals_2 = literals[max_literals_1:]
            variables_to_define_2 = []  # A list of variables we need to define

            # If at_least is obviously too small or too big, give the obvious answer
            if at_least <= 0:
                self.clauses.append([name])
            elif at_least > max_literals:
                self.clauses.append([-name])
            elif max_literals == 1:
                literal = literals[0]
                self.clauses.append([-name, literal])
                self.clauses.append([name, -literal])

            # Otherwise define the appropriate clauses
            else:
                if at_least <= max_literals_1:
                    self.clauses.append(
                        implies(
                            self.get_cardinality_variable(literals_1, at_least),
                            name))
                    variables_to_define_1.append(at_least)
                for j in range(1, max_literals_2 + 1):
                    for i in range(1, max_literals_1 + 1):
                        if i + j == at_least:
                            self.clauses.append(
                                implies(
                                    [self.get_cardinality_variable(literals_1, i),
                                     self.get_cardinality_variable(literals_2, j)],
                                    name))
                            variables_to_define_1.append(i)
                            variables_to_define_2.append(j)
                if at_least <= max_literals_2:
                    self.clauses.append(
                        implies(
                            self.get_cardinality_variable(literals_2, at_least),
                            name))
                    variables_to_define_2.append(at_least)

                if at_least > max_literals_2:
                    i = at_least - max_literals_2
                    self.clauses.append(
                        implies(
                            -self.get_cardinality_variable(literals_1, i),
                            -name))
                    variables_to_define_1.append(i)
                for j in range(1, max_literals_2 + 1):
                    for i in range(1, max_literals_1 + 1):
                        if i + j == at_least + 1:
                            self.clauses.append(implies([
                                -self.get_cardinality_variable(literals_1, i),
                                -self.get_cardinality_variable(literals_2, j)],
                                -name))
                            variables_to_define_1.append(i)
                            variables_to_define_2.append(j)
                if at_least > max_literals_1:
                    j = at_least - max_literals_1
                    self.clauses.append(
                        implies(
                            -self.get_cardinality_variable(literals_2, j),
                            -name))
                    variables_to_define_2.append(j)

            # Remove duplicates from our lists of child variables we need to define
            variables_to_define_1 = set(variables_to_define_1)
            variables_to_define_2 = set(variables_to_define_2)

            # Define the child variables
            for at_least_1 in variables_to_define_1:
                self.define_cardinality_variable(literals_1, at_least_1, preprocessing=False)
            for at_least_2 in variables_to_define_2:
                self.define_cardinality_variable(literals_2, at_least_2, preprocessing=False)
        return name

    def force_symmetry(self, symmetry):
        to_force_equal = self.cell_pairs_from_transformation(symmetry)
        self.force_equal(to_force_equal)

    def force_asymmetry(self, asymmetry):
        to_force_unequal = self.cell_pairs_from_transformation(asymmetry)
        self.force_unequal(to_force_unequal)

    def cell_pairs_from_transformation(self, symmetry):
        (
            transformation,
            x_translate,
            y_translate,
            period
        ) = symmetry
        transformation = transformation.upper()
        width = len(self.grid[0][0])
        height = len(self.grid[0])
        duration = len(self.grid)
        background_width = len(self.background_grid[0][0])
        background_height = len(self.background_grid[0])
        background_duration = len(self.background_grid)

        transformations = {
            "RO0": (
                lambda x, y: (x + x_translate, y + y_translate),
                lambda x, y: (x - x_translate, y - y_translate)
            ),
            "RO1": (
                lambda x, y: ((height - 1) - y + x_translate, x + y_translate),
                lambda x, y: (y - y_translate, (height - 1) - (x - x_translate))
            ),
            "RO2": (
                lambda x, y: ((width - 1) - x + x_translate, (height - 1) - y + y_translate),
                lambda x, y: ((width - 1) - (x - x_translate), (height - 1) - (y - y_translate))
            ),
            "RO3": (
                lambda x, y: (y + x_translate, (height - 1) - x + y_translate),
                lambda x, y: ((height - 1) - (y - y_translate), x - x_translate)
            ),
            "RE-": (
                lambda x, y: (x + x_translate, (height - 1) - y + y_translate),
                lambda x, y: (x - x_translate, (height - 1) - (y - y_translate))
            ),
            "RE\\": (
                lambda x, y: (y + x_translate, x + y_translate),
                lambda x, y: (y - y_translate, x - x_translate)
            ),
            "RE|": (
                lambda x, y: ((width - 1) - x + x_translate, y + y_translate),
                lambda x, y: ((width - 1) - (x - x_translate), y - y_translate)
            ),
            "RE/": (
                lambda x, y: ((height - 1) - y + x_translate, (height - 1) - x + y_translate),
                lambda x, y: ((height - 1) - (y - y_translate), (height - 1) - (x - x_translate))
            )
        }

        f, f_inv = transformations[transformation]

        cell_pairs = []

        for x_0 in range(width):
            for y_0 in range(height):
                for t in range(duration):
                    cell_0 = self.grid[t][y_0][x_0]
                    if t < duration - period:
                        x_1, y_1 = f(x_0, y_0)
                        if 0 <= x_1 < width and 0 <= y_1 < height:
                            other_cell = self.grid[t + period][y_1][x_1]
                        else:
                            other_cell = \
                                self.background_grid[(t + period) % background_duration][y_1 % background_height][
                                    x_1 % background_width]
                        cell_pairs.append((cell_0, other_cell))
                    if t >= period:
                        x_1, y_1 = f_inv(x_0, y_0)
                        if 0 <= x_1 < width and 0 <= y_1 < height:
                            other_cell = self.grid[t - period][y_1][x_1]
                        else:
                            other_cell = \
                                self.background_grid[(t - period) % background_duration][y_1 % background_height][
                                    x_1 % background_width]
                        cell_pairs.append((cell_0, other_cell))
        return cell_pairs

    def force_at_least(self, literals, amount):
        """Adds clauses forcing at least the given amount of literals to be true"""

        starting_number_of_clauses = len(self.clauses)
        name = self.define_cardinality_variable(literals, amount)
        self.clauses.append([name])
        log("Number of clauses used: " + str(len(self.clauses) - starting_number_of_clauses))

    def force_at_most(self, literals, amount):
        """Adds clauses forcing at most the given amount of literals to be true"""

        self.force_at_least([-literal for literal in literals], len(literals) - amount)

    def force_exactly(self, literals, amount):
        """Adds clauses forcing exactly the given amount of literals to be true"""

        self.force_at_least(literals, amount)
        self.force_at_most(literals, amount)

    def force_population_at_least(self, constraint):
        (times, population) = constraint
        log("Forcing the population in generation" + ("s" if len(times) > 1 else "") + " " + ", ".join(
            str(t) for t in times) + " to be at least " + str(population), 1)
        literals = [cell for t in times for row in self.grid[t] for cell in row]
        self.force_at_least(literals, population)
        log("Done\n", -1)

    def force_population_at_most(self, constraint):
        (times, population) = constraint
        log("Forcing the population in generation" + ("s" if len(times) > 1 else "") + " " + ", ".join(
            str(t) for t in times) + " to be at most " + str(population), 1)
        literals = [cell for t in times for row in self.grid[t] for cell in row]
        self.force_at_most(literals, population)
        log("Done\n", -1)

    def force_population_exactly(self, constraint):
        (times, population) = constraint
        log("Forcing the population in generation" + ("s" if len(times) > 1 else "") + " " + ", ".join(
            str(t) for t in times) + " to be exactly " + str(population), 1)
        literals = [cell for t in times for row in self.grid[t] for cell in row]
        self.force_exactly(literals, population)
        log("Done\n", -1)

    def force_max_change(self, max_change):
        log("Forcing the pattern to never change by more than " + str(max_change) + " cells", 1)
        width = len(self.grid[0][0])
        height = len(self.grid[0])
        duration = len(self.grid)
        for t in range(1, duration):
            literals = []
            for x in range(width):
                for y in range(height):
                    self.number_of_variables += 1
                    literal = self.number_of_variables
                    self.clauses.append(implies([self.grid[t][y][x], -self.grid[0][y][x]], literal))
                    self.clauses.append(implies([-self.grid[t][y][x], self.grid[0][y][x]], literal))
                    literals.append(literal)
            log("Generation " + str(t))
            self.force_at_most(literals, max_change)
        log("Done\n", -1)

    def force_max_decay(self, max_decay):
        log("Forcing the pattern to never decay by more than " + str(max_decay) + " cells", 1)
        width = len(self.grid[0][0])
        height = len(self.grid[0])
        duration = len(self.grid)
        for t in range(1, duration):
            literals = []
            for x in range(width):
                for y in range(height):
                    self.number_of_variables += 1
                    literal = self.number_of_variables
                    self.clauses.append(implies([-self.grid[t][y][x], self.grid[0][y][x]], literal))
                    literals.append(literal)
            log("Generation " + str(t))
            self.force_at_most(literals, max_decay)
        log("Done\n", -1)

    def force_max_growth(self, max_growth):
        log("Forcing the pattern to never grow by more than " + str(max_growth) + " cells", 1)
        width = len(self.grid[0][0])
        height = len(self.grid[0])
        duration = len(self.grid)
        for t in range(1, duration):
            literals = []
            for x in range(width):
                for y in range(height):
                    self.number_of_variables += 1
                    literal = self.number_of_variables
                    self.clauses.append(implies([self.grid[t][y][x], -self.grid[0][y][x]], literal))
                    literals.append(literal)
            log("Generation " + str(t))
            self.force_at_most(literals, max_growth)
        log("Done\n", -1)

    def force_equal(self, cell_pair_list):

        replacement = {}
        replaces = {}

        for cell_0, cell_1 in cell_pair_list:
            variable_0, negated_0 = variable_from_literal(cell_0)
            variable_1, negated_1 = variable_from_literal(cell_1)
            cell_0, cell_1 = max(variable_0,variable_1), min(variable_0,variable_1) * negated_0 * negated_1
            while cell_0 not in [-1, 1]:
                variable_0, negated_0 = variable_from_literal(cell_0)
                if variable_0 in replacement:
                    cell_0 = replacement[variable_0] * negated_0
                else:
                    break
            while cell_1 not in [-1, 1]:
                variable_1, negated_1 = variable_from_literal(cell_1)
                if variable_1 in replacement:
                    cell_1 = replacement[variable_1] * negated_1
                else:
                    break
            if cell_0 != cell_1:
                if cell_0 == -cell_1:
                    raise UnsatInPreprocessing
                elif cell_0 in [-1, 1]:
                    cell_0, cell_1 = cell_1, cell_0

                variable_0, negated_0 = variable_from_literal(cell_0)
                cell_0, cell_1 = variable_0, cell_1 * negated_0

                if cell_1 not in [-1, 1]:
                    variable_1, negated_1 = variable_from_literal(cell_1)
                    if variable_1 not in replaces:
                        replaces[variable_1] = []

                if variable_0 in replaces:
                    for variable in replaces[variable_0]:
                        replacement_variable, replacement_negated = variable_from_literal(replacement[variable])
                        replacement[variable] = cell_1 * replacement_negated
                        if cell_1 not in [-1, 1]:
                            replaces[variable_1].append(variable)
                    del replaces[variable_0]

                replacement[variable_0] = cell_1
                if cell_1 not in [-1, 1]:
                    replaces[variable_1].append(variable_0)

        for t, generation in enumerate(self.grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    if cell not in [-1, 1]:
                        variable, negated = variable_from_literal(cell)
                        if variable in replacement:
                            if replacement[variable] != variable:
                                self.grid[t][y][x] = replacement[variable] * negated

        for t, generation in enumerate(self.background_grid):
            for y, row in enumerate(generation):
                for x, cell in enumerate(row):
                    if cell not in [-1, 1]:
                        variable, negated = variable_from_literal(cell)
                        if variable in replacement:
                            if replacement[variable] != variable:
                                self.background_grid[t][y][x] = replacement[variable] * negated

        for transition, literal in self.rule.items():
            if literal not in [-1, 1]:
                variable, negated = variable_from_literal(literal)
                if variable in replacement:
                    if replacement[variable] != variable:
                        self.rule[transition] = replacement[variable] * negated

    def force_unequal(self, cell_pair_list):

        clause = []
        for cell_pair in cell_pair_list:
            self.number_of_variables += 1
            cells_equal = self.number_of_variables
            self.clauses.append(implies(cell_pair, cells_equal))
            self.clauses.append(implies([-cell for cell in cell_pair], cells_equal))
            clause.append(-cells_equal)

        self.clauses.append(clause)

    def make_string(self, pattern_output_format=None, determined=None, show_background=None):
        if pattern_output_format is None:
            pattern_output_format = settings.pattern_output_format

        log('Formatting output...', 1)

        assert pattern_output_format in ["rle", "csv", "blk"], "Format not recognised"

        background_grid = copy.deepcopy(self.background_grid)
        src.literal_manipulation.offset_background(background_grid, -1, -1, 0)
        background_ignore_transition = copy.deepcopy(self.background_ignore_transition)
        src.literal_manipulation.offset_background(background_ignore_transition, -1, -1, 0)
        if pattern_output_format == "rle":
            output_string = src.formatting.make_rle(
                self.grid,
                solution={1},
                background_grid=background_grid,
                rule=self.rule,
                determined=determined,
                show_background=show_background
            )
        elif pattern_output_format == "csv":
            output_string = src.formatting.make_csv(
                self.grid,
                ignore_transition=self.ignore_transition,
                background_grid=background_grid,
                background_ignore_transition=background_ignore_transition,
                rule=self.rule,
                determined=determined,
                show_background=show_background
            )
        elif pattern_output_format == "blk":
            output_string = src.formatting.make_blk(
                self.grid,
                solution={1},
                background_grid=background_grid,
                rule=self.rule,
                determined=determined,
                show_background=show_background
            )
        else:
            raise Exception

        log('Done\n', -1)

        return output_string

    def deterministic(self):
        log("Checking if pattern is deterministic...", 1)
        determined = make_grid(False, template=self.grid)
        determined_variables = set()
        width = len(self.grid[0][0])
        height = len(self.grid[0])

        while True:
            determined_copy = copy.deepcopy(determined)
            for t, generation in enumerate(self.grid):
                for y, row in enumerate(generation):
                    for x, cell in enumerate(row):
                        if not determined[t][y][x]:
                            if cell in [-1, 1]:
                                determined[t][y][x] = True
                            else:
                                variable, negated = variable_from_literal(cell)
                                if t == 0:
                                    determined[t][y][x] = True
                                    determined_variables.add(variable)
                                elif variable in determined_variables:
                                    determined[t][y][x] = True
                                elif all(determined[t - 1][y + y_offset][x + x_offset] for x_offset in range(2) for
                                         y_offset in range(2) if
                                         x + x_offset in range(width) and y + y_offset in range(height)) and not \
                                        self.ignore_transition[t][y][x]:
                                    determined[t][y][x] = True
                                    determined_variables.add(variable)
            if determined == determined_copy:
                break

        log("Done\n", -1)
        if all(flag for generation in determined for row in generation for flag in row):
            return True
        else:
            return False

    def background_nontrivial(self):
        return (
            len(self.background_grid[0]) > 1
            and len(self.background_grid[0][0]) > 1
            and any(cell not in [-1, 1] for generation in self.background_grid for row in generation for cell in row)
        )
