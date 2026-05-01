import collections

class CodeGenerator:
    def __init__(self):
        self.offsets = {}
        self.types = {}
        self.next_offset = 0
        self.code = []
        self.label_count = 0
        self.do_loops = collections.defaultdict(list)

    def generate(self, ast):
        if not ast:
            return []
        
        if ast[0] == "program":
            
            body = ast[2]

        for decl in body['decls']:
            _, var_type, ids = decl
            for var_id in ids:
                self.offsets[var_id] = self.next_offset
                self.types[var_id] = var_type
                self.next_offset += 1
            
            if self.next_offset > 0:
                self.code.append(f"PUSHN {self.next_offset}")
            
            for stmt in body['stmts']:
                self.visit_statement(stmt)

            # Print code instructions
            for instruction in self.code:
                print(instruction)
            
            return self.code
        
    def visit_statement(self, stmt):
        if not stmt: return

        if stmt[0] == 'labeled':
            label = stmt[1]
            self.code.append(f"L{label}:")
            self.visit_statement(stmt[2])
            
            if label in self.do_loops:
                for var_id, end_expr, start_label in reversed(self.do_loops[label]):
                    # Increment variable: ID = ID + 1
                    self.code.append(f"PUSHG {self.offsets[var_id]}")
                    self.code.append("PUSHI 1")
                    self.code.append("ADD")
                    self.code.append(f"STOREG {self.offsets[var_id]}")
                    
                    # Jump back to start of loop
                    self.code.append(f"JUMP {start_label}")
                    
                    # Exit label for this loop
                    self.code.append(f"L_END_{label}_{var_id}:")
                del self.do_loops[label]
            return
        
        stmt_kind = stmt[0]
        if stmt_kind == 'assign':
            _, var_id, expr = stmt
    





    def visit_expr(self, expr):
        pass

