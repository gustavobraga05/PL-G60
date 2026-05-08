from symbolTable import SymbolTable, SemanticError
from optimizer import fold_constants

class SemanticAnalyzer:
    def __init__(self):
        self.symbols = SymbolTable()
        self.pending_do_labels = set()  # Rótulos de DO loops que esperam um CONTINUE
        self.labeled_statements = set()  # Rótulos de statements encontrados

    def analyze(self, ast):
    
        if not ast: return
        
        if ast[0] == 'program':
            # 1. Processar Declarações de Variáveis
            for decl in ast[2]['decls']:
                self.visit_declaration(decl)

            # 2. Processar Declaração de Funções
            for func in ast[3]:
                _, func_type, func_name, arg_list, body = func
                self.symbols.declare(func_name, func_type, len(arg_list))

            # 3. Processar, Validar e Otimizar Statements (Tudo num só passo)
            optimized_stmts = []
            for stmt in ast[2]['stmts']:
                # visit_statement agora valida a semântica E devolve o nó otimizado
                new_stmt = self.visit_statement(stmt)
                optimized_stmts.append(new_stmt)
            
            # 4. Atualizar a AST com a versão otimizada
            ast[2]['stmts'] = optimized_stmts
            
            # 5. Verificar se sobraram DO loops abertos
            if self.pending_do_labels:
                missing_labels = ', '.join(str(l) for l in sorted(self.pending_do_labels))
                raise SemanticError(f"DO loops com rótulos faltantes: {missing_labels}.")
                
    def visit_body(self, body):
        for decl in body['decls']:
            self.visit_declaration(decl)
            
        

    def visit_declaration(self, decl):
        var_type = decl[1]
        var_list = decl[2]
        
        for var_id in var_list:
            if isinstance(var_id, tuple) and var_id[0] == 'array':
                self.symbols.declare(var_id, var_type)
            else:
                self.symbols.declare(var_id, var_type)

    def visit_statement(self, stmt):
        if stmt[0] == 'labeled':
            label = stmt[1]
            self.labeled_statements.add(label)
            
            # Verificar se este rótulo fecha um DO loop
            if label in self.pending_do_labels:
                self.pending_do_labels.remove(label)
            inner = stmt[2]
            new_inner = self.visit_statement(inner)
            return ('labeled', label, new_inner)

        kind = stmt[0]
        if kind == 'assign':
            return self.visit_assign(stmt)
        elif kind == 'array_assign':
            return self.visit_array_assign(stmt)
        elif kind == 'print':
            return self.visit_print(stmt)
        elif kind == 'read':
            return self.visit_read(stmt)
        elif kind == 'do':
            return self.visit_do(stmt)
        elif kind == 'if':
            return self.visit_if(stmt)

        # Por omissão, devolve o stmt inalterado
        return stmt


    def visit_assign(self, stmt):
        _, var_id, expr = stmt
        optimized_expr = fold_constants(expr, self.symbols)
        entry = self.symbols.lookup(var_id)
        expected_type = entry['type']
        
        expr_type = self.visit_expression(optimized_expr)
        
        if expr_type != expected_type and not (expr_type == 'INTEGER' and expected_type == 'REAL'):
            raise SemanticError(f"Não é possível atribuir uma expressão '{expr_type}' à variável '{var_id}' (declarada como {expected_type}).")
        
        self.symbols.initialize(var_id)

        # Se a expressão é um valor constante, regista-o na symbol table
        if optimized_expr[0] == 'val' and optimized_expr[2] in ['INT_CONST', 'REAL_CONST', 'STRING_CONST', 'TRUE', 'FALSE']:
            self.symbols.set_constant(var_id, optimized_expr[1], optimized_expr[2])
        else:
            # Atribuição não-constante remove qualquer valor constante anterior
            try:
                self.symbols.clear_constant(var_id)
            except Exception:
                pass

        return ('assign', var_id, optimized_expr)

    def visit_array_assign(self, stmt):
        # ('array_assign', name, index_expr, value_expr)
        _, name, index_expr, value_expr = stmt
        entry = self.symbols.lookup(name)
        if entry.get('kind') != 'array':
            raise SemanticError(f"'{name}' não é um array.")
        expected_type = entry['type']
        
        # Check index type
        idx_type = self.visit_expression(index_expr)
        if idx_type != 'INTEGER':
            raise SemanticError(f"Índice de array para '{name}' deve ser INTEGER, recebeu {idx_type}.")
        
        # Check value type
        value_type = self.visit_expression(value_expr)
        if value_type != expected_type and not (value_type == 'INTEGER' and expected_type == 'REAL'):
            raise SemanticError(f"Não é possível atribuir uma expressão '{value_type}' ao array '{name}' (declarado como {expected_type}).")
        
        # Escrever num elemento de array invalida qualquer constante associada ao array
        try:
            self.symbols.clear_constant(name)
        except Exception:
            pass

        self.symbols.initialize(name)

        # Otimização: tentar dobrar constantes no índice e no valor
        idx_opt = fold_constants(index_expr, self.symbols)
        val_opt = fold_constants(value_expr, self.symbols)
        return ('array_assign', name, idx_opt, val_opt)
    def visit_print(self, stmt):
        _, expr_list = stmt
        new_list = []
        for expr in expr_list:
            new_expr = fold_constants(expr, self.symbols)
            # Também valida tipos/uso das variáveis
            self.visit_expression(new_expr)
            new_list.append(new_expr)
        return ('print', new_list)

    def visit_read(self, stmt):
        _, id_list = stmt
        for var_id in id_list:
            if isinstance(var_id, tuple) and var_id[0] == 'array':
                self.symbols.lookup(var_id[1])
                # Read invalida valores constantes
                try:
                    self.symbols.clear_constant(var_id[1])
                except Exception:
                    pass
                self.symbols.initialize(var_id[1])
            else:
                self.symbols.lookup(var_id)
                try:
                    self.symbols.clear_constant(var_id)
                except Exception:
                    pass
                self.symbols.initialize(var_id)
        return stmt
    def visit_do(self, stmt):
        _, label, var_id, start_expr, end_expr = stmt
        
        # Registar que este DO loop espera um statement com este rótulo
        self.pending_do_labels.add(label)
        
        entry = self.symbols.lookup(var_id)
        if entry['type'] != 'INTEGER':
            raise SemanticError(f"A variável de controlo do DO ('{var_id}') tem de ser INTEGER.")
        
        self.symbols.initialize(var_id)
        
        start_type = self.visit_expression(start_expr)
        end_type = self.visit_expression(end_expr)
        
        if start_type != 'INTEGER' or end_type != 'INTEGER':
            raise SemanticError(f"Os limites do ciclo DO devem ser inteiros. Recebido: {start_type} e {end_type}")
        # Otimizar limites do DO
        start_opt = fold_constants(start_expr, self.symbols)
        end_opt = fold_constants(end_expr, self.symbols)
        return ('do', label, var_id, start_opt, end_opt)
    def visit_if(self, stmt):
        _, cond_expr, then_stmts, else_stmts = stmt

        # Dobrar constantes na condição
        cond_opt = fold_constants(cond_expr, self.symbols)

        cond_type = self.visit_condition(cond_opt)
        if cond_type != 'LOGICAL':
            raise SemanticError(f"A condição do IF deve ser LOGICAL, recebido: {cond_type}")

        new_then = []
        for s in then_stmts:
            new_then.append(self.visit_statement(s))

        new_else = None
        if else_stmts:
            new_else = [self.visit_statement(s) for s in else_stmts]

        return ('if', cond_opt, new_then, new_else)

    def visit_expression(self, expr):
        kind = expr[0]
        
        if kind == 'val':
            val, tok_type = expr[1], expr[2]
            
            if tok_type == 'ID':
                entry = self.symbols.lookup(val)
                if not entry['initialized']:
                    raise SemanticError(f"Variável '{val}' foi usada numa expressão mas não foi inicializada.")
                return entry['type']
            
            elif tok_type == 'INT_CONST': return 'INTEGER'
            elif tok_type == 'REAL_CONST': return 'REAL'
            elif tok_type == 'STRING_CONST': return 'STRING'
            elif tok_type in ['TRUE', 'FALSE']: return 'LOGICAL'
            
        elif kind == 'binop':
            _, op, left, right = expr
            lt = self.visit_expression(left)
            rt = self.visit_expression(right)
            
            if lt not in ['INTEGER', 'REAL'] or rt not in ['INTEGER', 'REAL']:
                raise SemanticError(f"Operação matemática ({op}) requer valores numéricos. Encontrados {lt} e {rt}.")
                
            return 'REAL' if 'REAL' in [lt, rt] else 'INTEGER'
        
        elif kind == 'mod':
            _, left, right = expr
            lt = self.visit_expression(left)
            rt = self.visit_expression(right)

            if lt not in ['INTEGER', 'REAL'] or rt not in ['INTEGER', 'REAL']:
                raise SemanticError(f"Operação matemática (.MOD.) requer valores numéricos. Encontrados {lt} e {rt}.")
            
            return 'INTEGER'
            
        elif kind == 'array':
            _, name, index = expr
            entry = self.symbols.lookup(name)
            if entry.get('kind') != 'array':
                raise SemanticError(f"'{name}' não é um array.")
            idx_type = self.visit_expression(index)
            if idx_type != 'INTEGER':
                raise SemanticError(f"Índice de array para '{name}' deve ser INTEGER, recebeu {idx_type}.")
            return entry['type']

        elif kind == 'unary':
            _, op, operand = expr
            t = self.visit_expression(operand)
            if t not in ['INTEGER', 'REAL']:
                raise SemanticError(f"Operação unária ({op}) requer um valor numérico. Encontrado {t}.")
            return t
        
        elif kind == 'call':
            _, func_name, arg_list = expr
            entry = self.symbols.lookup(func_name)
            if len(arg_list) != entry['arg_size']:
                raise SemanticError(f"Função {func_name} espera {entry['arg_size']} argumentos e recebeu {len(arg_list)}")

            return entry['type']
        
            
        elif kind in ['cond', 'not', 'bool']:
            return self.visit_condition(expr)

    def visit_condition(self, cond):
        kind = cond[0]
        
        if kind == 'cond':
            _, op, left, right = cond
            
            if op in ['.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.']:
                lt = self.visit_expression(left)
                rt = self.visit_expression(right)
                
                if not ((lt in ['INTEGER', 'REAL'] and rt in ['INTEGER', 'REAL']) or (lt == 'LOGICAL' and rt == 'LOGICAL')):
                    raise SemanticError(f"Comparação ({op}) requer tipos compatíveis. Encontrados {lt} e {rt}.")
            else:
                lt = self.visit_condition(left)
                rt = self.visit_condition(right)
                
                if lt != 'LOGICAL' or rt != 'LOGICAL':
                    raise SemanticError(f"Operação Lógica ({op}) requer condições ou booleanos.")
            
            return 'LOGICAL'
            
        elif kind == 'not':
            t = self.visit_condition(cond[1])
            if t != 'LOGICAL':
                raise SemanticError("NOT requer um booleano ou condição à sua frente.")
            return 'LOGICAL'
            
        elif kind == 'bool':
            return 'LOGICAL'
            
        else:
            # Caso uma expressão normal (ex: ID) seja avaliada como condição: `IF (FLAG)` onde FLAG é ID
            return self.visit_expression(cond)