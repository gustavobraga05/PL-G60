class CodeGenerator:
    def __init__(self):
        self.offsets = {}
        self.types = {}
        self.kinds = {} 
        self.shapes = {} 
        self.next_offset = 0
        self.code = []
        self.label_count = 0
        self.do_loops = {}
        self.func_slots = {} 

    def _new_label(self, prefix):
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def compute_linear_offset_ast(self, indices, shape):
        """
        Função utilizada para calcular o offset das matrizes 
        """

        current_offset_ast = ('binop', '-', indices[0], ('val', 1, 'INT_CONST'))
        
        for i in range(1, len(shape)):
            dim_val = shape[i]
            next_idx_0_based = ('binop', '-', indices[i], ('val', 1, 'INT_CONST'))
            
            mul_expr = ('binop', '*', current_offset_ast, ('val', dim_val, 'INT_CONST'))
            current_offset_ast = ('binop', '+', mul_expr, next_idx_0_based)
            
        return current_offset_ast

    def generate(self, ast):
        if not ast:
            return []
        
        program, functions = ast

        if program[0] != "program":
            return []

        body = program[2]

        for func in functions:
            _, func_type, func_name, arg_list, body_func = func
            num_args = len(arg_list)
            
            arg_names = set()
            for arg in arg_list:
                arg_names.add(arg[1] if isinstance(arg, tuple) else arg)
            arg_names.add(func_name) 

            local_count = 0
            for decl in body_func["decls"]:
                _, v_type, ids = decl
                for v_id in ids:
                    name = v_id[1] if isinstance(v_id, tuple) else v_id
                    if name in arg_names:
                        continue
                    
                    if isinstance(v_id, tuple) and v_id[0] == 'array_decl':
                        dims = []
                        size = 1
                        for d_expr in v_id[2]:
                            if d_expr[0] == 'val' and d_expr[2] == 'INT_CONST':
                                d = int(d_expr[1])
                                dims.append(d)
                                size *= d
                            else:
                                dims.append(1)
                        local_count += size
                    else:
                        local_count += 1
            
            self.func_slots[func_name] = num_args + local_count

        for decl in body["decls"]:
            _, var_type, ids = decl
            for var_id in ids:
                if isinstance(var_id, tuple) and var_id[0] == 'array_decl':
                    name = var_id[1]
                    dims = []
                    size = 1
                    for d_expr in var_id[2]:
                        d = int(d_expr[1])
                        dims.append(d)
                        size *= d
                        
                    
                    self.offsets[name] = self.next_offset
                    self.kinds[name] = 'array'
                    self.shapes[name] = dims
                    self.types[name] = var_type
                    self.next_offset += size
                else:
                    self.offsets[var_id] = self.next_offset
                    self.kinds[var_id] = 'scalar'
                    self.types[var_id] = var_type
                    self.next_offset += 1

        if self.next_offset > 0:
            self.code.append(f"PUSHN {self.next_offset}")

        for stmt in body["stmts"]:
            self.visit_statement(stmt)

        self.code.append("STOP")

        for func in functions:
            self.visit_function(func)

        return self.code
    
    def visit_function(self, func):
        _, func_type, func_name, arg_list, body = func
        self.code.append(f"{func_name}:")
        
        # Guardar contexto global para restaurar no fim
        old_offsets = self.offsets
        old_types = self.types
        old_kinds = self.kinds
        old_shapes = self.shapes
        self.offsets = {} 
        self.types = {}
        self.kinds = {}
        self.shapes = {}
        self.is_in_func = True 
        
        num_args = len(arg_list)

        self.offsets[func_name] = -(num_args + 1)
        self.types[func_name] = func_type
        self.kinds[func_name] = 'scalar'

        # Mapear Argumentos (Offsets Negativos)
        for i, arg in enumerate(arg_list):
            # Normalizar nome se for um array no arg_list
            arg_name = arg[1] if isinstance(arg, tuple) else arg
            # O i-ésimo argumento está em -(num_args - i)
            self.offsets[arg_name] = -(num_args - i)
            self.kinds[arg_name] = 'scalar' 

        # Mapear Variáveis Locais (Offsets Positivos)
        local_count = 0
        for decl in body["decls"]:
            _, v_type, ids = decl
            for v_id in ids:
                name = v_id[1] if isinstance(v_id, tuple) else v_id
                
                is_array_decl = isinstance(v_id, tuple) and v_id[0] == 'array_decl'

                if name in self.offsets:
                    self.types[name] = v_type
                    if is_array_decl:
                        self.kinds[name] = 'array_ref'
                        dims = []
                        for d_expr in v_id[2]:
                            if d_expr[0] == 'val' and d_expr[2] == 'INT_CONST':
                                dims.append(int(d_expr[1]))
                            else: dims.append(1)
                        self.shapes[name] = dims
                    continue
                
                self.offsets[name] = local_count
                self.types[name] = v_type
                
                if is_array_decl:
                    self.kinds[name] = 'array'
                    dims = []
                    size = 1
                    for d_expr in v_id[2]:
                        if d_expr[0] == 'val' and d_expr[2] == 'INT_CONST':
                            d = int(d_expr[1])
                            dims.append(d)
                            size *= d
                        else:
                            dims.append(1)
                    self.shapes[name] = dims
                    local_count += size
                else:
                    self.kinds[name] = 'scalar'
                    local_count += 1

        # Reservar espaço para as locais na stack
        if local_count > 0:
            self.code.append(f"PUSHN {local_count}")

        # Gerar código para o corpo da função
        for stmt in body["stmts"]:
            self.visit_statement(stmt)

        # Finalizar 
        self.code.append("RETURN")
        
        self.offsets = old_offsets
        self.types = old_types
        self.kinds = old_kinds
        self.shapes = old_shapes
        self.is_in_func = False



    def visit_statement(self, stmt):
        if not stmt:
            return

        if stmt[0] == "labeled":
            label = stmt[1]
            

            if label in self.do_loops:
                for var_id, start_label, exit_label in reversed(self.do_loops[label]):
                    instr_p = "PUSHL" if getattr(self, 'is_in_func', False) else "PUSHG"
                    instr_s = "STOREL" if getattr(self, 'is_in_func', False) else "STOREG"
                    self.code.append(f"{instr_p} {self.offsets[var_id]}")
                    self.code.append("PUSHI 1")
                    self.code.append("ADD")
                    self.code.append(f"{instr_s} {self.offsets[var_id]}")
                    self.code.append(f"JUMP {start_label}")
                    self.code.append(f"{exit_label}:")
                del self.do_loops[label]
                return
        
            self.code.append(f"L{label}:")
            self.visit_statement(stmt[2])
            return

        stmt_kind = stmt[0]

        if stmt_kind == "assign":
            _, var_id, expr = stmt
            self.visit_expression(expr)
            instr = "STOREL" if getattr(self, 'is_in_func', False) else "STOREG"
            self.code.append(f"{instr} {self.offsets[var_id]}")
        
        elif stmt_kind == "array_assign":
            _, name, indices, value_expr = stmt
            
            kind = self.kinds[name]
            offset = self.offsets[name]
            shape = self.shapes[name]

            if kind == 'array_ref':
                self.code.append(f"PUSHL {offset}")
            else:
                instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                self.code.append(instr_p)
                self.code.append(f"PUSHI {offset}")
                self.code.append("PADD")
            
            # Calcular o índice linearizado
            linear_ast = self.compute_linear_offset_ast(indices, shape)
            self.visit_expression(linear_ast)
            self.code.append("PADD")
            
            self.visit_expression(value_expr)
            
            self.code.append("STORE 0")

        elif stmt_kind == "print":
            _, expr_list = stmt
            for expr in expr_list:
                expr_type = self.infer_expression_type(expr)
                self.visit_expression(expr)
                if expr_type == "STRING":
                    self.code.append("WRITES")
                elif expr_type == "REAL":
                    self.code.append("WRITEF")
                else:
                    self.code.append("WRITEI")
            self.code.append("WRITELN")

        elif stmt_kind == "read":
            _, id_list = stmt
            for var_id in id_list:
                if isinstance(var_id, tuple) and var_id[0] == 'array':
                    _, name, indices = var_id
                    
                    kind = self.kinds[name]
                    offset = self.offsets[name]
                    shape = self.shapes[name]

                    if kind == 'array_ref':
                        self.code.append(f"PUSHL {offset}")
                    else:
                        instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                        self.code.append(instr_p)
                        self.code.append(f"PUSHI {offset}")
                        self.code.append("PADD")

                    linear_ast = self.compute_linear_offset_ast(indices, shape)
                    self.visit_expression(linear_ast)
                    self.code.append("PADD")
                    
                    # Lê o valor
                    self.code.append("READ")
                    var_type = self.types[name]
                    self.code.append("ATOF" if var_type == "REAL" else "ATOI")
                    
                    # Guarda
                    self.code.append("STORE 0")
                else:
                    self.code.append("READ")
                    var_type = self.types[var_id]
                    self.code.append("ATOF" if var_type == "REAL" else "ATOI")
                    instr = "STOREL" if getattr(self, 'is_in_func', False) else "STOREG"
                    self.code.append(f"{instr} {self.offsets[var_id]}")

        elif stmt_kind == "goto":
            _, label = stmt
            self.code.append(f"JUMP L{label}")

        elif stmt_kind == "continue":
            return

        elif stmt_kind == "do":
            _, target_label, var_id, start_expr, end_expr = stmt

            self.visit_expression(start_expr)
            instr_s = "STOREL" if getattr(self, 'is_in_func', False) else "STOREG"
            self.code.append(f"{instr_s} {self.offsets[var_id]}")

            start_label = self._new_label("DOSTART")
            exit_label = self._new_label("DOEND")

            self.code.append(f"{start_label}:")
            instr_p = "PUSHL" if getattr(self, 'is_in_func', False) else "PUSHG"
            self.code.append(f"{instr_p} {self.offsets[var_id]}")
            self.visit_expression(end_expr)
            self.code.append("INFEQ")
            self.code.append(f"JZ {exit_label}")

            self.do_loops.setdefault(target_label, []).append((var_id, start_label, exit_label))

        elif stmt_kind == "if":
            _, cond_expr, then_stmts, else_stmts = stmt

            else_label = self._new_label("IFELSE")
            end_label = self._new_label("IFEND")

            self.visit_condition(cond_expr)
            self.code.append(f"JZ {else_label}")

            for then_stmt in then_stmts:
                self.visit_statement(then_stmt)

            self.code.append(f"JUMP {end_label}")
            self.code.append(f"{else_label}:")

            if else_stmts:
                for else_stmt in else_stmts:
                    self.visit_statement(else_stmt)

            self.code.append(f"{end_label}:")

    def visit_expression(self, expr):
        kind = expr[0]

        if kind == "val":
            value, tok_type = expr[1], expr[2]
            if tok_type == "INT_CONST":
                self.code.append(f"PUSHI {value}")
            elif tok_type == "REAL_CONST":
                self.code.append(f"PUSHF {value}")
            elif tok_type == "STRING_CONST":
                escaped = str(value).replace('"', '\\"')
                self.code.append(f"PUSHS \"{escaped}\"")
            elif tok_type == "ID":
                kind = self.kinds[value]
                offset = self.offsets[value]
                if kind == 'array':
                    instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                    self.code.append(instr_p)
                    self.code.append(f"PUSHI {offset}")
                    self.code.append("PADD")
                elif kind == 'array_ref':
                    self.code.append(f"PUSHL {offset}")
                else:
                    instr = "PUSHL" if getattr(self, 'is_in_func', False) else "PUSHG"
                    self.code.append(f"{instr} {offset}")
            elif tok_type == "TRUE":
                self.code.append("PUSHI 1")
            elif tok_type == "FALSE":
                self.code.append("PUSHI 0")
            return

        if kind == "unary":
            _, op, operand = expr
            self.visit_expression(operand)
            if op == "-":
                self.code.append("PUSHI -1")
                self.code.append("MUL")
            return
        
        if kind == "mod":
            _, left, right = expr
            self.visit_expression(left)
            self.visit_expression(right)
            self.code.append("MOD")
            return

        elif kind == "array":
            _, name, indices = expr
            
            kind = self.kinds[name]
            offset = self.offsets[name]
            shape = self.shapes[name]

            if kind == 'array_ref':
                self.code.append(f"PUSHL {offset}")
            else:
                instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                self.code.append(instr_p)
                self.code.append(f"PUSHI {offset}")
                self.code.append("PADD")
            
            # Somar o índice linearizado (Row-Major)
            linear_ast = self.compute_linear_offset_ast(indices, shape)
            self.visit_expression(linear_ast)
            self.code.append("PADD")
            
            # Carregar o valor daquele endereço
            self.code.append("LOAD 0")
            return
        
        elif kind == "call":
            _, func_name, arg_list = expr
            for arg in arg_list:
                self.visit_expression(arg)

            self.code.append(f"PUSHA {func_name}")
            self.code.append("CALL")
            self.code.append(f"POP {self.func_slots[func_name]}")

        if kind == "binop":
            _, op, left, right = expr
            self.visit_expression(left)
            self.visit_expression(right)
            if op == "+":
                self.code.append("ADD")
            elif op == "-":
                self.code.append("SUB")
            elif op == "*":
                self.code.append("MUL")
            elif op == "/":
                self.code.append("DIV")
            return

        elif kind in ["cond", "not", "bool"]:
            self.visit_condition(expr)
            return

    def visit_condition(self, cond):
        kind = cond[0]

        if kind == "bool":
            val = str(cond[1]).upper()
            self.code.append("PUSHI 1" if val == ".TRUE." else "PUSHI 0")
            return

        if kind == "not":
            self.visit_condition(cond[1])
            self.code.append("NOT")
            return

        if kind == "cond":
            _, op, left, right = cond
            op = str(op).upper()

            if op in [".AND.", ".OR."]:
                self.visit_condition(left)
                self.visit_condition(right)
                self.code.append("AND" if op == ".AND." else "OR")
                return

            self.visit_expression(left)
            self.visit_expression(right)

            if op == ".EQ.":
                self.code.append("EQUAL")
            elif op == ".NE.":
                self.code.append("EQUAL")
                self.code.append("NOT")
            elif op == ".LT.":
                self.code.append("INF")
            elif op == ".LE.":
                self.code.append("INFEQ")
            elif op == ".GT.":
                self.code.append("SUP")
            elif op == ".GE.":
                self.code.append("SUPEQ")
            return

        self.visit_expression(cond)

    def infer_expression_type(self, expr):
        kind = expr[0]

        if kind == "val":
            val, tok_type = expr[1], expr[2]
            if tok_type == "ID":
                return self.types[val]
            if tok_type == "INT_CONST":
                return "INTEGER"
            if tok_type == "REAL_CONST":
                return "REAL"
            if tok_type == "STRING_CONST":
                return "STRING"
            if tok_type in ["TRUE", "FALSE"]:
                return "LOGICAL"

        if kind == "binop":
            _, _, left, right = expr
            left_type = self.infer_expression_type(left)
            right_type = self.infer_expression_type(right)
            if left_type == "REAL" or right_type == "REAL":
                return "REAL"
            return "INTEGER"

        if kind == "unary":
            return self.infer_expression_type(expr[2])

        if kind == "mod":
            return "INTEGER"
        
        if kind == "array":
            _, name, _ = expr
            return self.types[name]

        return "LOGICAL"


