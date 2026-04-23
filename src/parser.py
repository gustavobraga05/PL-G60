import ply.yacc as yacc
import sys 
import pprint
from lexer import FortranLexer
from symbolTable import SymbolTable, SemanticError

tokens = FortranLexer.tokens

precedence = (
    ('left', 'OR'), ('left', 'AND'), ('right', 'NOT'),
    ('nonassoc', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'), ('left', 'TIMES', 'DIVIDE'),
    ('right', 'UMINUS', 'UPLUS'),
)

def p_program(p):
    '''program : PROGRAM ID body END'''
    p[0] = ('program', p[2], p[3])

def p_body(p):
    '''body : declarations statements'''
    p[0] = {'decls': p[1], 'stmts': p[2]}

# --- DECLARAÇÕES ---
def p_declarations(p):
    '''declarations : declarations declaration
                    | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_declaration(p):
    '''declaration : type_spec id_list'''
    var_type = p[1]
    var_list = p[2]
    
    # Register each variable in the list with the correct type
    for var_id in var_list:
        p.parser.symbols.declare(var_id, var_type)
    
    p[0] = ('decl', var_type, var_list)

def p_type_spec(p):
    '''type_spec : INTEGER
                 | REAL
                 | LOGICAL'''
    p[0] = p[1]

def p_id_list(p):
    '''id_list : id_list COMMA ID
               | ID'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

# --- INSTRUÇÕES ---
def p_statements(p):
    '''statements : statements statement
                  | statement'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_statement(p):
    '''statement : labeled_stmt
                 | unlabeled_stmt'''
    p[0] = p[1]

def p_labeled_stmt(p):
    '''labeled_stmt : LABEL unlabeled_stmt'''
    p[0] = ('labeled', p[1], p[2])

def p_unlabeled_stmt(p):
    '''unlabeled_stmt : assignment
                      | print_stmt
                      | read_stmt
                      | do_stmt
                      | if_stmt
                      | goto_stmt
                      | continue_stmt'''
    p[0] = p[1]

def p_assignment(p):
    '''assignment : ID ASSIGN expression'''
    entry = p.parser.symbols.lookup(p[1])
    expected_type = entry['type']
    expr_node, expr_type = p[3]
    # Allow int to real assignment
    if expr_type != expected_type and not (expr_type == 'INTEGER' and expected_type == 'REAL'):
        raise SemanticError(f"Cannot assign {expr_type} to {expected_type} variable {p[1]}")
    p[0] = ('assign', p[1], expr_node, expected_type)
    p.parser.symbols.initialize(p[1])

def p_print_stmt(p):
    '''print_stmt : PRINT STAR COMMA expression_list'''
    expr_nodes = [expr[0] for expr in p[4]]
    p[0] = ('print', expr_nodes)

def p_read_stmt(p):
    '''read_stmt : READ STAR COMMA id_list'''
    p[0] = ('read', p[4])
    for var_id in p[4]:
        p.parser.symbols.initialize(var_id)

def p_goto_stmt(p):
    '''goto_stmt : GOTO LABEL'''
    p[0] = ('goto', p[2])

def p_continue_stmt(p):
    '''continue_stmt : CONTINUE'''
    p[0] = ('continue',)

def p_do_stmt(p):
    '''do_stmt : DO LABEL ID ASSIGN expression COMMA expression'''
    # Check that the bounds are integer
    start_node, start_type = p[5]
    end_node, end_type = p[7]
    if start_type != 'INTEGER' or end_type != 'INTEGER':
        raise SemanticError(f"DO loop bounds must be integer, got {start_type} and {end_type}")
    p[0] = ('do', p[2], p[3], start_node, end_node)

def p_if_stmt(p):
    '''if_stmt : IF LPAREN condition RPAREN THEN statements ELSE statements ENDIF
               | IF LPAREN condition RPAREN THEN statements ENDIF'''
    cond_node, cond_type = p[3]
    if cond_type != 'LOGICAL':
        raise SemanticError(f"IF condition must be logical, got {cond_type}")
    if len(p) == 10:
        p[0] = ('if', cond_node, p[6], p[8])
    else:
        p[0] = ('if', cond_node, p[6], None)

# --- EXPRESSÕES ---
def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    left_node, left_type = p[1]
    right_node, right_type = p[3]
    if left_type not in ['INTEGER', 'REAL'] or right_type not in ['INTEGER', 'REAL']:
        raise SemanticError(f"Arithmetic operation requires numeric operands, got {left_type} and {right_type}")
    # Result type: if both int, int; else real
    result_type = 'REAL' if 'REAL' in [left_type, right_type] else 'INTEGER'
    p[0] = (('binop', p[2], left_node, right_node), result_type)


def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]  # pass through the type


def p_expression_unary(p):
    '''expression : MINUS expression %prec UMINUS
                  | PLUS expression %prec UPLUS'''
    expr_node, expr_type = p[2]
    if expr_type not in ['INTEGER', 'REAL']:
        raise SemanticError(f"Unary {p[1]} requires numeric operand, got {expr_type}")
    p[0] = (('unary', p[1], expr_node), expr_type)

def p_expression_val(p):
    '''expression : INT_CONST
                  | REAL_CONST
                  | ID
                  | STRING_CONST
                  | TRUE
                  | FALSE'''
    if isinstance(p[1], str) and p.slice[1].type == 'ID':
        entry = p.parser.symbols.lookup(p[1])
        if not entry['initialized']:
            raise SemanticError(f"Variable {p[1]} used before initialization")
        expr_type = entry['type']
    elif p.slice[1].type == 'INT_CONST':
        expr_type = 'INTEGER'
    elif p.slice[1].type == 'REAL_CONST':
        expr_type = 'REAL'
    elif p.slice[1].type == 'STRING_CONST':
        expr_type = 'STRING'
    elif p.slice[1].type in ['TRUE', 'FALSE']:
        expr_type = 'LOGICAL'
    else:
        expr_type = 'UNKNOWN'  # fallback
    p[0] = (('val', p[1]), expr_type)
def p_expression_list(p):
    '''expression_list : expression_list COMMA expression
                       | expression'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_condition(p):
    '''condition : expression EQ expression
                 | expression NE expression
                 | expression LT expression
                 | expression LE expression
                 | expression GT expression
                 | expression GE expression
                 | condition AND condition
                 | condition OR condition
                 | NOT condition
                 | LPAREN condition RPAREN
                 | TRUE
                 | FALSE'''
    if len(p) == 4 and p[1] == '(':
        p[0] = p[2]  # grouped condition
    elif len(p) == 4:
        # comparison or logical op
        left_node, left_type = p[1]
        right_node, right_type = p[3]
        if p[2] in ['.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.']:
            # comparison
            if not ((left_type in ['INTEGER', 'REAL'] and right_type in ['INTEGER', 'REAL']) or
                    (left_type == 'LOGICAL' and right_type == 'LOGICAL')):
                raise SemanticError(f"Comparison requires compatible operands, got {left_type} and {right_type}")
            p[0] = (('cond', p[2], left_node, right_node), 'LOGICAL')
        else:
            # AND/OR
            if left_type != 'LOGICAL' or right_type != 'LOGICAL':
                raise SemanticError(f"Logical operation {p[2]} requires logical operands")
            p[0] = (('cond', p[2], left_node, right_node), 'LOGICAL')
    elif len(p) == 3:
        # NOT
        cond_node, cond_type = p[2]
        if cond_type != 'LOGICAL':
            raise SemanticError(f"NOT requires logical operand, got {cond_type}")
        p[0] = (('not', cond_node), 'LOGICAL')
    else:
        # TRUE/FALSE
        p[0] = (('bool', p[1]), 'LOGICAL')

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p is None:
        print('Erro Sintatico: fim de ficheiro inesperado')
    else:
        print(f"Erro Sintatico na linha {p.lineno} perto de '{p.value}'")

if __name__ == "__main__":
    # Verifica se passaste o nome do ficheiro como argumento ou usa o padrão
    # Inicialização
    f_lexer = FortranLexer()
    f_lexer.build()
    parser = yacc.yacc()
    path = "../testFiles/"
    filename = "teste.f"
    filepath = path + filename

    try:
        with open(filepath, 'r') as f:
            test_code = f.read()
        
        print(f"--- A processar: {filepath} ---")
        
        # Executa o parser
        parser.symbols = SymbolTable()
        result = parser.parse(test_code, lexer=f_lexer.lexer)
        
        if result:
            print("\n--- Árvore de Sintaxe Abstrata (AST) Gerada ---")
            pprint.pprint(result)
        else:
            print("\nFalha ao gerar a AST.")

    except SemanticError as e:
        print(f"Erro Semântico: {e}")
    except FileNotFoundError:
        print(f"Erro: O ficheiro '{filepath}' não foi encontrado.")
    except Exception as e:
        print(f"Erro durante o processamento: {e}")