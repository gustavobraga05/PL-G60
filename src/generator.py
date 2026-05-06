class CodeGenerator:
    def __init__(self):
        self.offsets = {}
        self.types = {}
        self.next_offset = 0
        self.code = []
        self.label_count = 0
        self.do_loops = {}

    def _new_label(self, prefix):
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def generate(self, ast):
        if not ast:
            return []

        if ast[0] != "program":
            return []

        body = ast[2]

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
                    self.offsets[name] = self.next_offset - 1
                    self.types[name] = var_type
                    self.next_offset += size
                else:
                    # Scalar declaration
                    self.offsets[var_id] = self.next_offset
                    self.types[var_id] = var_type
                    self.next_offset += 1

        if self.next_offset > 0:
            self.code.append(f"PUSHN {self.next_offset}")

        for stmt in body["stmts"]:
            self.visit_statement(stmt)

        self.code.append("STOP")
        return self.code

    def visit_statement(self, stmt):
        if not stmt:
            return

        if stmt[0] == "labeled":
            label = stmt[1]
            

            if label in self.do_loops:
                for var_id, start_label, exit_label in reversed(self.do_loops[label]):
                    self.code.append(f"PUSHG {self.offsets[var_id]}")
                    self.code.append("PUSHI 1")
                    self.code.append("ADD")
                    self.code.append(f"STOREG {self.offsets[var_id]}")
                    self.code.append(f"JUMP {start_label}")
                    self.code.append(f"{exit_label}:")
                del self.do_loops[label]
                return
        
            self.code.append(f"L{label}:")
            self.visit_statement(stmt[2])

        stmt_kind = stmt[0]

        if stmt_kind == "assign":
            _, var_id, expr = stmt
            self.visit_expression(expr)
            self.code.append(f"STOREG {self.offsets[var_id]}")
        
        elif stmt_kind == "array_assign":
            # ARRAY(index) = value
            _, name, index_expr, value_expr = stmt
            
            # 1. Colocar o ponteiro para a base da memória global (Tipo Address)
            self.code.append("PUSHGP")
            
            # 2. Somar o offset inicial do array ao ponteiro global
            self.code.append(f"PUSHI {self.offsets[name]}")
            self.code.append("PADD")
            
            # 3. Calcular o índice e somar ao ponteiro (Resultado: Endereço do elemento)
            self.visit_expression(index_expr)
            self.code.append("PADD")
            
            # 4. Calcular o valor a ser guardado
            self.visit_expression(value_expr)
            
            # 5. Agora sim, STORE 0 funcionará porque tem um Address na pilha
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
                    
                    # 1. Calcula e deixa o Address no fundo
                    self.code.append("PUSHGP")
                    self.code.append(f"PUSHI {self.offsets[name]}")
                    self.code.append("PADD")
                    self.visit_expression(index_expr)
                    self.code.append("PADD")
                    
                    # 2. Lê o valor (o valor fica no topo, acima do Address)
                    self.code.append("READ")
                    var_type = self.types[name]
                    self.code.append("ATOF" if var_type == "REAL" else "ATOI")
                    
                    # 3. Guarda
                    self.code.append("STORE 0")
                else:
                    # Read into scalar variable
                    self.code.append("READ")
                    var_type = self.types[var_id]
                    if var_type == "REAL":
                        self.code.append("ATOF")
                    else:
                        self.code.append("ATOI")
                    self.code.append(f"STOREG {self.offsets[var_id]}")

        elif stmt_kind == "goto":
            _, label = stmt
            self.code.append(f"JUMP L{label}")

        elif stmt_kind == "continue":
            return

        elif stmt_kind == "do":
            _, target_label, var_id, start_expr, end_expr = stmt

            self.visit_expression(start_expr)
            self.code.append(f"STOREG {self.offsets[var_id]}")

            start_label = self._new_label("DOSTART")
            exit_label = self._new_label("DOEND")

            self.code.append(f"{start_label}:")
            self.code.append(f"PUSHG {self.offsets[var_id]}")
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
                self.code.append(f"PUSHG {self.offsets[value]}")
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
            
            # 1. Obter ponteiro global
            self.code.append("PUSHGP")
            
            # 2. Ir até ao início do array
            self.code.append(f"PUSHI {self.offsets[name]}")
            self.code.append("PADD")
            
            # 3. Somar o índice (usa PADD)
            self.visit_expression(index_expr)
            self.code.append("PADD")
            
            # 4. Carregar o valor daquele endereço
            self.code.append("LOAD 0")
            return

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

        self.visit_condition(expr)

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


