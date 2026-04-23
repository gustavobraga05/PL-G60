
class SemanticError(Exception):
    pass

class SyntaxError(Exception):
    pass

class SymbolTable():
    def __init__(self):
        self.__table = {}

  # if the variable is not declared, raise a semantic error
    def lookup(self, id):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        return self.__table[id] # Returns the type

  # notice that this allows multiple declarations of the same variable
    def declare(self, id, var_type):
        if id in self.__table:
            raise SemanticError(f"Variable {id} already declared")
        self.__table[id] = var_type