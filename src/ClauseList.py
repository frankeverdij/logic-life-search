from src.messages import print_message
from src.literal_manipulation import negate, variable_from_literal


class ClauseList:

    def __init__(self):
        self.clause_set = set()
        self.number_of_variables = 0
        self.dimacs_literal_from_variable = {}

    def __eq__(self, other):
        if other is None:
            return False
        else:
            return (
                    self.clause_set == other.clause_set
                    and self.number_of_variables == other.number_of_variables
                    and self.dimacs_literal_from_variable == other.dimacs_literal_from_variable
            )

    def __ne__(self, other):
        return not __eq__(self, other)

    def append(self, clause):
        dimacs_clause = []
        clause = set(clause)
        if "1" in clause:
            return
        for literal in clause:
            if literal == "0":
                pass
            else:
                (variable, negated) = variable_from_literal(literal)
                # If we haven't seen it before then add it to the dictionary
                if variable not in self.dimacs_literal_from_variable:
                    self.dimacs_literal_from_variable[variable] = str(self.number_of_variables + 1)
                    self.number_of_variables += 1
                elif negate(literal) in clause:
                    return
                dimacs_clause.append(negate(self.dimacs_literal_from_variable[variable], negated, dimacs=True))
        dimacs_clause.sort()
        dimacs_clause.append("0\n")
        self.clause_set.add(" ".join(dimacs_clause))

    def make_file(self, file_name, indent=0):
        print_message('Writing file "' + file_name + '" ...', 3, indent=indent)
        with open(file_name, "w") as output_file:
            output_file.write("p cnf " + str(self.number_of_variables) + " " + str(len(self.clause_set)) + "\n")
            output_file.write("".join(self.clause_set))
        print_message('Done\n', 3, indent=indent)
