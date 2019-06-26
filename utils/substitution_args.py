import os
import re
import copy
import rospkg

class SubstitutionArgs:
    """Evaluate ROS Substitution Args

    http://wiki.ros.org/roslaunch/XML
    """
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.rospack = rospkg.RosPack()

    def evaluate_if(self, statement, context_args, local_args):
        """Evaluate an 'if' statement:
        """
        evaluated_statement = self.evaluate(statement, context_args, local_args)

        # somewhat hacky solution to the fact that roslaunch isn't strict about interpreting capitalization of "false" vs. "False"
        if "false" in evaluated_statement:
            evaluated_statement = evaluated_statement.replace("false", "False")
        if "true" in evaluated_statement:
            evaluated_statement = evaluated_statement.replace("true", "True")

        return eval(evaluated_statement)

    def evaluate_unless(self, statement, context_args, local_args):
        """Evaluate an 'unless' statement:
        """
        return not self.evaluate_if(statement, context_args, local_args)

    @staticmethod
    def get_substrings(input_string):
        """ get substitution arg substrings : $(***)
        """
        string = copy.copy(input_string)
        substrings = []

        start_idx = string.find("$(")
        while start_idx >= 0:
            count = 1
            for idx in range(start_idx+2, len(string)):
                char = string[idx]
                if char == "(":
                    count += 1
                elif char == ")":
                    count -= 1
                if count == 0:
                    # we've closed our bracket
                    substring = string[start_idx:idx+1]
                    string = string.replace(substring, "")
                    substrings.append(substring)
                    break
                if idx == len(string)-1:
                    # if we've got this far the string is unmatched
                    raise RuntimeError("Failed to find matching bracket for '$(' in string {}; is it malformed?".format(input_string))

            start_idx = string.find("$(")
        return substrings

    def evaluate(self, string, context_args=None, local_context=None):
        """ Evaluate a given string in the context of the launch file 
        """
        original = string
        substrings = self.get_substrings(string)
            
        for substring in substrings:
            if substring.find("$(env ") == 0:
                evaluated_string = self._eval_env(substring)
            elif substring.find("$(optenv ") == 0:
                evaluated_string = self._eval_optenv(substring)
            elif substring.find("$(find ") == 0:
                evaluated_string = self._eval_find(substring)
            elif substring.find("$(anon ") == 0:
                evaluated_string = self._eval_anon(substring)
            elif substring.find("$(arg ") == 0:
                evaluated_string = self._eval_arg(substring, context_args, local_context)
            elif substring.find("$(eval ") == 0:
                evaluated_string = self._eval_eval(substring, context_args, local_context)
            elif substring.find("$(dirname ") == 0:
                evaluated_string = self._eval_dirname(substring)
            else:
                raise RuntimeError("Unable to evaluate substitution arg call for string {}".format(substring))

            string = string.replace(substring, evaluated_string)

        self.print_("\tEvaluated '{}' as '{}'".format(original, string))
        return string

    def print_(self, string):
        if self.verbose:
            print(string)

    def _eval_env(self, substring):
        var = substring[6:-1]
        if var not in os.environ.keys():
            raise RuntimeError("Environmental variable '{}' not found.".format(var))
        return os.environ[var]
        
    def _eval_optenv(self, substring):
        optvar = substring[9:-1].split(" ")
        if optvar[0] in os.environ.keys():
            return os.environ[optvar[0]]
        else:
            if len(optvar) == 1:
                print("Warning, no optional environmental variable supplied. Sought in {}!".format(substring))
                return ""
            return optvar[1]

    def _eval_find(self, substring):
        package = substring[7:-1]
        try:
            path = self.rospack.get_path(package)
        except rospkg.common.ResourceNotFound:
            raise RuntimeError("Failed to find package '{}', did you source your workspace?".format(package))
        return path

    def _eval_anon(self, substring):
        print("WARNING: tag anon not supported!")
        return substring[7:-1]

    def _eval_arg(self, substring, context_args, local_context):
        arg = substring[6:-1]

        if arg not in context_args.keys():
            if arg in local_context.keys():
                return local_context[arg]
            raise RuntimeError("Unable to substitute argument '{}'; not found in context.".format(arg))
        return context_args[arg]

    def _eval_eval(self, substring, context_args, local_context):
        eval_statement = substring[7:-1]

        # substitute any arguments:
        for arg_statement in re.findall(r'arg\([^()]*\)', eval_statement):
            arg_to_replace = arg_statement[4:-1].replace("'", "")
            if arg_to_replace not in context_args.keys():
                if arg_to_replace not in local_context.keys():
                    raise RuntimeError("Unable to substitute argument '{}'; not found in context.".format(arg_to_replace))
                else:
                    value = local_context[arg_to_replace]
            else:
                value = context_args[arg_to_replace]
            eval_statement = eval_statement.replace(arg_statement, "'" + value + "'")

        # substitute any arguments not specified by the arg tag (blah)
        for possible_argument in re.split(r'\W+', eval_statement):
            if possible_argument in context_args.keys():
                print("Implicitly substituting {} for {}".format(possible_argument, context_args[possible_argument]))
                eval_statement = eval_statement.replace(possible_argument, context_args[possible_argument])
            elif possible_argument in local_context.keys():
                print("Implicitly substituting {} for {}".format(possible_argument, local_context[possible_argument]))
                eval_statement = eval_statement.replace(possible_argument, local_context[possible_argument])

        return eval_statement

    def _eval_dirname(self, substring):
        print("WARNING: tag dirname not supported!")
