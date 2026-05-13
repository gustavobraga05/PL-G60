from symbolTable import SymbolTable, SemanticError
from optimizer import fold_constants

class SemanticAnalyzer:
    def __init__(self):
        self.symbols = SymbolTable()
        self.pending_do_labels = set()  # Rótulos de DO loops que esperam um CONTINUE
        self.labeled_statements = set()  # Rótulos de statements encontrados
        self.goto_labels = set()  # Rótulos usados em GOTO

    # Função de entrada
    def analyze(self, ast):
        if not ast:
            return
        
        functions = ast[1]
        
        # Declarar funções
        self.declare_functions(functions)


        if ast[0] is not None:
            self.analyze_program(ast[0])

        # 5. Validar semântica de cada função
        for func in functions:
            self.analyze_function(func)

    def analyze_program(self, program):
        _, _, body = program

        # 2. Processar declarações e statements do programa
        body['stmts'] = self.process_scope(body['decls'], body['stmts'])

        # 3. Verificar se todos os GOTO apontam para rótulos existentes
        undefined = self.goto_labels - self.labeled_statements
        if undefined:
            raise SemanticError(f"GOTO para rótulo(s) inexistente(s): {', '.join(str(l) for l in sorted(undefined))}.")

        # 4. Verificar se sobraram DO loops abertos
        if self.pending_do_labels:
            missing_labels = ', '.join(str(l) for l in sorted(self.pending_do_labels))
            raise SemanticError(f"DO loops com rótulos faltantes: {missing_labels}.")
        
    def process_scope(self, decls, stmts):
        self.declare_variables(decls)
        return self.process_stmts(stmts)
                
    
    def analyze_function(self, func):
        """Analisa a semântica de uma função com a sua própria symbol table."""
        _, func_type, func_name, arg_list, body = func

        decls = body['decls']
        
        # Guardar a symbol table global
        old_symbols = self.symbols
        old_do_labels = self.pending_do_labels
        old_labeled = self.labeled_statements
        old_goto_labels = self.goto_labels
        old_table = self.symbols._SymbolTable__table
        
        # Reinicializar apenas a tabela de variáveis locais, mantendo a tabela de funções global
        self.symbols._SymbolTable__table = {}
        self.pending_do_labels = set()
        self.labeled_statements = set()
        self.goto_labels = set()
        
        # Processar declarações locais
        self.declare_variables(decls)
        
        # Registar a função (retorno) como variável local com o tipo da função
        self.symbols.declare(func_name, func_type)
                
        # Registar argumentos como variáveis locais inicializadas
        for arg_name in arg_list:
            # Argumentos são escalares inicializados
            self.symbols.initialize(arg_name)

        # Processar declarações e statements do body da função
        body['stmts'] = self.process_stmts( body['stmts'])

        # Verificar se todos os GOTO apontam para rótulos existentes
        undefined = self.goto_labels - self.labeled_statements
        if undefined:
            raise SemanticError(f"Na função '{func_name}': GOTO para rótulo(s) inexistente(s): {', '.join(str(l) for l in sorted(undefined))}.")

        # Verificar se sobraram DO loops abertos na função
        if self.pending_do_labels:
            missing_labels = ', '.join(str(l) for l in sorted(self.pending_do_labels))
            raise SemanticError(f"Na função '{func_name}': DO loops com rótulos faltantes: {missing_labels}.")

        # Restaurar a tabela de variáveis global
        self.symbols._SymbolTable__table = old_table
        self.pending_do_labels = old_do_labels
        self.labeled_statements = old_labeled
        self.goto_labels = old_goto_labels

    def process_stmts(self, stmts):
        optimized_stmts = []
        for stmt in stmts:
            new_stmt = self.visit_statement(stmt)
            if new_stmt is None:
                continue
            if isinstance(new_stmt, list):
                optimized_stmts.extend(new_stmt)
            else:
                optimized_stmts.append(new_stmt)

        return optimized_stmts

    def declare_variables(self, decls):
        for decl in decls:
            self.visit_declaration(decl)

    def declare_functions(self, functions):
        for func in functions:
            _, func_type, func_name, arg_list, body = func
            self.symbols.declare_function(func_name, func_type, len(arg_list))

    def visit_declaration(self, decl):
        var_type = decl[1]
        var_list = decl[2]
        
        for var_id in var_list:
            if isinstance(var_id, tuple) and var_id[0] == 'array':
                self.symbols.declare(var_id, var_type)
            else:
                self.symbols.declare(var_id, var_type)

    def resolve_call_or_array(self, expr):
        _, name, args = expr
        
        # Tentar procurar como função primeira
        try:
            entry = self.symbols.lookup_function(name)
            return ('call', name, args)
        except SemanticError:
            pass
        
        # Se não for função, procurar como variável (array ou scalar)
        entry = self.symbols.lookup(name)
        if entry.get('kind') == 'array':
            if len(args) != 1:
                raise SemanticError(f"Array '{name}' espera exactamente 1 índice, recebeu {len(args)}.")
            return ('array', name, args[0])

        raise SemanticError(f"'{name}' não é nem um array nem uma função.")
    

    def canonicalize_expression(self, expr):
        """"""
        kind = expr[0]

        if kind == 'call_or_array':
            return self.canonicalize_expression(self.resolve_call_or_array(expr))

        if kind == 'binop':
            return ('binop', expr[1], self.canonicalize_expression(expr[2]), self.canonicalize_expression(expr[3]))

        if kind == 'unary':
            return ('unary', expr[1], self.canonicalize_expression(expr[2]))

        if kind == 'mod':
            return ('mod', self.canonicalize_expression(expr[1]), self.canonicalize_expression(expr[2]))

        if kind == 'array':
            return ('array', expr[1], self.canonicalize_expression(expr[2]))

        if kind == 'call':
            return ('call', expr[1], [self.canonicalize_expression(arg) for arg in expr[2]])

        if kind == 'cond':
            return ('cond', expr[1], self.canonicalize_expression(expr[2]), self.canonicalize_expression(expr[3]))

        if kind == 'not':
            return ('not', self.canonicalize_expression(expr[1]))

        return expr

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
        elif kind == 'goto':
            # ('goto', label)
            self.goto_labels.add(stmt[1])
            return stmt

        # Por omissão, devolve o stmt inalterado
        return stmt


    def visit_assign(self, stmt):
        _, var_id, expr = stmt
        optimized_expr = fold_constants(expr, self.symbols)
        optimized_expr = self.canonicalize_expression(optimized_expr)
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
        idx_opt = self.canonicalize_expression(fold_constants(index_expr, self.symbols))
        val_opt = self.canonicalize_expression(fold_constants(value_expr, self.symbols))
        return ('array_assign', name, idx_opt, val_opt)
    
    def visit_print(self, stmt):
        _, expr_list = stmt
        new_list = []
        for expr in expr_list:
            new_expr = self.canonicalize_expression(fold_constants(expr, self.symbols))
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
        
        start_opt = self.canonicalize_expression(fold_constants(start_expr, self.symbols))
        end_opt = self.canonicalize_expression(fold_constants(end_expr, self.symbols))
        start_type = self.visit_expression(start_opt)
        end_type = self.visit_expression(end_opt)
        
        if start_type != 'INTEGER' or end_type != 'INTEGER':
            raise SemanticError(f"Os limites do ciclo DO devem ser inteiros. Recebido: {start_type} e {end_type}")
        return ('do', label, var_id, start_opt, end_opt)
    
    def visit_if(self, stmt):
        _, cond_expr, then_stmts, else_stmts = stmt

        # Dobrar constantes na condição
        cond_opt = self.canonicalize_expression(fold_constants(cond_expr, self.symbols))

        cond_type = self.visit_condition(cond_opt)
        if cond_type != 'LOGICAL':
            raise SemanticError(f"A condição do IF deve ser LOGICAL, recebido: {cond_type}")

        # Se a condição é constante, eliminar código morto
        if cond_opt[0] == 'val' and (cond_opt[2] in ['TRUE', 'FALSE'] or str(cond_opt[1]).upper() in ['.TRUE.', '.FALSE.']):
            is_true = True if (cond_opt[2] == 'TRUE' or str(cond_opt[1]).upper() == '.TRUE.') else False
            if is_true:
                # Mantém apenas o bloco 'then'
                new_then = []
                #Percorre os statements do bloco 'then'
                for s in then_stmts:
                    r = self.visit_statement(s)
                    if r is None:
                        continue
                    if isinstance(r, list):
                        new_then.extend(r)
                    else:
                        new_then.append(r)
                if not new_then:
                    return None
                return new_then if len(new_then) > 1 else new_then[0]
            else:
                # Mantém apenas o bloco 'else' (se existir)
                if else_stmts:
                    new_else = []
                    for s in else_stmts:
                        r = self.visit_statement(s)
                        if r is None:
                            continue
                        if isinstance(r, list):
                            new_else.extend(r)
                        else:
                            new_else.append(r)
                    if not new_else:
                        return None
                    return new_else if len(new_else) > 1 else new_else[0]
                else:
                    # Nenhum código permanece
                    return None

        new_then = []
        for s in then_stmts:
            res = self.visit_statement(s)
            if res is not None:
                new_then.append(res)

        new_else = []
        if else_stmts:
            for s in else_stmts:
                res = self.visit_statement(s)
                if res is not None:
                    new_else.append(res)

        return ('if', cond_opt, new_then, new_else)

    def visit_expression(self, expr):
        expr = self.canonicalize_expression(expr)
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
            entry = self.symbols.lookup_function(func_name)
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