
class SemanticError(Exception):
    pass

class SyntaxError(Exception):
    pass

class SymbolTable():
    def __init__(self):
        self.__table = {}
        self.__func_table = {}  # Tabela separada para funções

  # if the variable is not declared, raise a semantic error
    def lookup(self, id):
        if id not in self.__table:
            raise SemanticError(f"Undeclared variable: {id}")
        return self.__table[id] # Returns the dict {'type': type, 'initialized': bool}

  # notice that this allows multiple declarations of the same variable
    def declare(self, id, var_type, arg_size=None):
        if isinstance(id, tuple) and id[0] == 'array_decl':
            name = id[1]
            dim_exprs = id[2] # List of expressions
            if name in self.__table:
                raise SemanticError(f"Variable {name} already declared")
            
            # For simplicity, assume dimensions are constant during declaration
            dimensions = []
            total_size = 1
            for dim_expr in dim_exprs:
                if dim_expr[0] == 'val' and dim_expr[2] == 'INT_CONST':
                    d = int(dim_expr[1])
                    dimensions.append(d)
                    total_size *= d
                else:
                    # Fallback or complex F77 arg dimensions
                    dimensions.append(1)
            
            self.__table[name] = {
                'type': var_type,
                'initialized': False,
                'kind': 'array',
                'dimensions': dimensions,
                'total_size': total_size,
                'const': None,
                'const_type': None,
            }
            return        
        
        if arg_size is None:
            if id in self.__table:
                if self.__table[id]['kind'] != 'function':
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
                'kind': 'function',
                'arg_size': arg_size,
                'const': None,
                'const_type': None,
            }

    def initialize(self, id):
        if isinstance(id, tuple):
            id = id[1]

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

    def declare_function(self, func_name, func_type, arg_size):
        """Declara uma função na tabela separada de funções."""
        if func_name in self.__func_table:
            raise SemanticError(f"Função '{func_name}' já foi declarada")
        self.__func_table[func_name] = {
            'type': func_type,
            'kind': 'function',
            'arg_size': arg_size,
        }

    def lookup_function(self, func_name):
        """Procura uma função na tabela separada de funções."""
        if func_name not in self.__func_table:
            raise SemanticError(f"Função '{func_name}' não foi declarada")
        return self.__func_table[func_name]