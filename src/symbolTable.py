
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
        return self.__table[id] # Returns the dict {'type': type, 'initialized': bool}

  # notice that this allows multiple declarations of the same variable
    def declare(self, id, var_type, arg_size=None):
        if isinstance(id, tuple) and id[0] == 'array':
            name = id[1]
            if name in self.__table:
                raise SemanticError(f"Variable {name} already declared")
            self.__table[name] = {
                'type': var_type,
                'initialized': False,
                'kind': 'array',
                'size': id[2],
                'const': None,
                'const_type': None,
            }
            return        
        
        if arg_size is None:
            if id in self.__table:
                raise SemanticError(f"Variable {id} already declared")
            self.__table[id] = {
                'type': var_type,
                'initialized': False,
                'kind': 'scalar',
                'const': None,
                'const_type': None,
            }
        else:
            self.__table[id] = {
                'type': var_type,
                'initialized': False,
                'kind': 'scalar',
                'arg_size': arg_size,
                'const': None,
                'const_type': None,
            }

    def initialize(self, id):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        self.__table[id]['initialized'] = True

    def set_constant(self, id, value, const_type):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        self.__table[id]['const'] = value
        self.__table[id]['const_type'] = const_type
        self.__table[id]['initialized'] = True

    def clear_constant(self, id):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        self.__table[id]['const'] = None
        self.__table[id]['const_type'] = None

    def is_initialized(self, id):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        return self.__table[id]['initialized']