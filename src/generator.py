class CodeGenerator:
    def __init__(self):
        self.offsets = {}
        self.types = {}
        self.kinds = {} # Track kind: scalar, array, array_ref
        self.next_offset = 0
        self.code = []
        self.label_count = 0
        self.do_loops = {}
        self.func_slots = {} # Track total slots (args + locals) for POP instruction

    def _new_label(self, prefix):
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def generate(self, ast):
        if not ast:
            return []
        
        program, functions = ast

        if program[0] != "program":
            return []

        body = program[2]

        # Pre-pass: Calculate total slots (args + locals) for each function for correct POP
        for func in functions:
            _, func_type, func_name, arg_list, body_func = func
            num_args = len(arg_list)
            
            # Map argument names to avoid counting them as locals
            arg_names = set()
            for arg in arg_list:
                arg_names.add(arg[1] if isinstance(arg, tuple) else arg)
            arg_names.add(func_name) # Return slot is not a local

            local_count = 0
            for decl in body_func["decls"]:
                _, v_type, ids = decl
                for v_id in ids:
                    name = v_id[1] if isinstance(v_id, tuple) else v_id
                    if name in arg_names:
                        continue
                    
                    if isinstance(v_id, tuple) and v_id[0] == 'array':
                        size = v_id[2][1] if v_id[2][0] == 'val' else 1
                        local_count += size
                    else:
                        local_count += 1
            
            self.func_slots[func_name] = num_args + local_count

        for decl in body["decls"]:
            _, var_type, ids = decl
            for var_id in ids:
                if isinstance(var_id, tuple) and var_id[0] == 'array':
                    # Array declaration: ('array', name, size_expr)
                    name = var_id[1]
                    # Evaluate the size expression (should be INT_CONST for now)
                    if var_id[2][0] == 'val' and var_id[2][2] == 'INT_CONST':
                        size = var_id[2][1]
                    else:
                        size = 1  # default fallback
                    self.offsets[name] = self.next_offset
                    self.kinds[name] = 'array'
                    self.types[name] = var_type
                    self.next_offset += size
                else:
                    # Scalar declaration
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
        
        # 1. Guardar contexto global para restaurar no fim
        old_offsets = self.offsets
        old_types = self.types
        old_kinds = self.kinds
        self.offsets = {} # Usaremos apenas offsets locais aqui dentro
        self.types = {}
        self.kinds = {}
        self.is_in_func = True # Flag para usar PUSHL/STOREL
        
        num_args = len(arg_list)

        # 2. Mapear o Slot de Retorno (Nome da Função)
        # Ocupa a posição -(n + 1)
        self.offsets[func_name] = -(num_args + 1)
        self.types[func_name] = func_type
        self.kinds[func_name] = 'scalar'

        # 3. Mapear Argumentos (Offsets Negativos)
        # Se n=1, arg está em -1. Se n=2, args estão em -2 e -1.
        for i, arg in enumerate(arg_list):
            # Normalizar nome se for um array no arg_list
            arg_name = arg[1] if isinstance(arg, tuple) else arg
            # O i-ésimo argumento está em -(num_args - i)
            self.offsets[arg_name] = -(num_args - i)
            self.kinds[arg_name] = 'scalar' # Default

        # 4. Mapear Variáveis Locais (Offsets Positivos)
        local_count = 0
        for decl in body["decls"]:
            _, v_type, ids = decl
            for v_id in ids:
                name = v_id[1] if isinstance(v_id, tuple) else v_id
                
                is_array = isinstance(v_id, tuple) and v_id[0] == 'array'

                # Se já está mapeado (é argumento ou o nome da função), apenas definimos o tipo e kind
                if name in self.offsets:
                    self.types[name] = v_type
                    if is_array:
                        self.kinds[name] = 'array_ref'
                    continue
                
                # Nova variável local (começa no offset 0)
                self.offsets[name] = local_count
                self.types[name] = v_type
                
                if is_array:
                    self.kinds[name] = 'array'
                    size = v_id[2][1] if v_id[2][0] == 'val' else 1
                    local_count += size
                else:
                    self.kinds[name] = 'scalar'
                    local_count += 1

        # 5. Reservar espaço para as locais na stack
        if local_count > 0:
            self.code.append(f"PUSHN {local_count}")

        # 6. Gerar código para o corpo da função
        for stmt in body["stmts"]:
            self.visit_statement(stmt)

        # 7. Finalizar e restaurar contexto
        self.code.append("RETURN")
        
        self.offsets = old_offsets
        self.types = old_types
        self.kinds = old_kinds
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
            # ARRAY(index) = value
            _, name, index_expr, value_expr = stmt
            
            kind = self.kinds[name]
            offset = self.offsets[name]

            if kind == 'array_ref':
                # Array passed by reference: address is in the local variable
                self.code.append(f"PUSHL {offset}")
            else:
                # Global or Local array
                instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                self.code.append(instr_p)
                self.code.append(f"PUSHI {offset}")
                self.code.append("PADD")
            
            # 3. Calcular o índice (1-based to 0-based) e somar ao ponteiro
            self.visit_expression(index_expr)
            self.code.append("PUSHI 1")
            self.code.append("SUB")
            self.code.append("PADD")
            
            # 4. Calcular o valor a ser guardado
            self.visit_expression(value_expr)
            
            # 5. Guardar
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
                    _, name, index_expr = var_id
                    
                    kind = self.kinds[name]
                    offset = self.offsets[name]

                    if kind == 'array_ref':
                        self.code.append(f"PUSHL {offset}")
                    else:
                        instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                        self.code.append(instr_p)
                        self.code.append(f"PUSHI {offset}")
                        self.code.append("PADD")

                    self.visit_expression(index_expr)
                    self.code.append("PUSHI 1")
                    self.code.append("SUB")
                    self.code.append("PADD")
                    
                    # 2. Lê o valor
                    self.code.append("READ")
                    var_type = self.types[name]
                    self.code.append("ATOF" if var_type == "REAL" else "ATOI")
                    
                    # 3. Guarda
                    self.code.append("STORE 0")
                else:
                    # Read into scalar variable
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
                    # Passing entire array by reference
                    instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                    self.code.append(instr_p)
                    self.code.append(f"PUSHI {offset}")
                    self.code.append("PADD")
                elif kind == 'array_ref':
                    # Already an address
                    self.code.append(f"PUSHL {offset}")
                else:
                    # Scalar
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
            _, name, index_expr = expr
            
            kind = self.kinds[name]
            offset = self.offsets[name]

            if kind == 'array_ref':
                self.code.append(f"PUSHL {offset}")
            else:
                instr_p = "PUSHFP" if getattr(self, 'is_in_func', False) else "PUSHGP"
                self.code.append(instr_p)
                self.code.append(f"PUSHI {offset}")
                self.code.append("PADD")
            
            # 3. Somar o índice (1-based to 0-based)
            self.visit_expression(index_expr)
            self.code.append("PUSHI 1")
            self.code.append("SUB")
            self.code.append("PADD")
            
            # 4. Carregar o valor daquele endereço
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


