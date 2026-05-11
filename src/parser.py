import ply.yacc as yacc
import sys 
import pprint
from lexer import FortranLexer
from semantic import SemanticAnalyzer
from symbolTable import SemanticError
from generator import CodeGenerator

tokens = FortranLexer.tokens

precedence = (
    ('left', 'OR'), ('left', 'AND'), ('right', 'NOT'),
    ('nonassoc', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'), ('left', 'TIMES', 'DIVIDE'),
    ('right', 'UMINUS', 'UPLUS'),
)

def p_program(p):
    '''program : PROGRAM ID body END functions'''
    p[0] = ('program', p[2], p[3], p[5])

def p_body(p):
    '''body : declarations statements'''
    p[0] = {'decls': p[1], 'stmts': p[2]}

def p_functions(p):
    '''functions : functions function
                 | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_function(p):
    '''function : type_spec FUNCTION ID LPAREN arg_list RPAREN body RETURN END'''
    p[0] = ('function', p[1], p[3], p[5], p[7])

def p_func_arguments(p):
    '''arg_list : id_list
                | empty'''
    p[0] = p[1] if p[1] else []

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
    p[0] = ('decl', p[1], p[2])

def p_type_spec(p):
    '''type_spec : INTEGER
                 | REAL
                 | LOGICAL'''
    p[0] = p[1]

def p_id_list(p):
    '''id_list : id_list COMMA ID
               | id_list COMMA ID LPAREN expression RPAREN
               | ID LPAREN expression RPAREN
               | ID'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 7:
        p[0] = p[1] + [('array', p[3], p[5])]
    elif len(p) == 5:
        p[0] = [('array', p[1], p[3])]
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
    '''assignment : ID ASSIGN expression
                  | ID LPAREN expression RPAREN ASSIGN expression'''
    if len(p) == 4:
        p[0] = ('assign', p[1], p[3])
    else:
        # Array assignment: ARRAY(index) = value
        p[0] = ('array_assign', p[1], p[3], p[6])

def p_print_stmt(p):
    '''print_stmt : PRINT STAR COMMA expression_list'''
    p[0] = ('print', p[4])

def p_read_stmt(p):
    '''read_stmt : READ STAR COMMA id_list'''
    p[0] = ('read', p[4])

def p_goto_stmt(p):
    '''goto_stmt : GOTO LABEL'''
    p[0] = ('goto', p[2])

def p_expression_mod(p):
    '''expression : MOD LPAREN expression COMMA expression RPAREN'''
    p[0] = ('mod', p[3], p[5])

def p_continue_stmt(p):
    '''continue_stmt : CONTINUE'''
    p[0] = ('continue',)

def p_do_stmt(p):
    '''do_stmt : DO LABEL ID ASSIGN expression COMMA expression'''
    p[0] = ('do', p[2], p[3], p[5], p[7])

def p_if_stmt(p):
    '''if_stmt : IF LPAREN expression RPAREN THEN statements ELSE statements ENDIF
               | IF LPAREN expression RPAREN THEN statements ENDIF'''
    if len(p) == 10:
        p[0] = ('if', p[3], p[6], p[8])
    else:
        p[0] = ('if', p[3], p[6], None)

# --- EXPRESSÕES ---
def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    p[0] = ('binop', p[2], p[1], p[3])

def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]

def p_call_args(p):
    '''call_args : expression_list'''
    p[0] = p[1]

def p_expression_call_or_array(p):
    '''expression : ID LPAREN call_args RPAREN'''
    p[0] = ('call_or_array', p[1], p[3])


def p_expression_unary(p):
    '''expression : MINUS expression %prec UMINUS
                  | PLUS expression %prec UPLUS'''
    p[0] = ('unary', p[1], p[2])

def p_expression_val(p):
    '''expression : INT_CONST
                  | REAL_CONST
                  | ID
                  | STRING_CONST
                  | TRUE
                  | FALSE'''
    token_type = p.slice[1].type
    p[0] = ('val', p[1], token_type)
    
def p_expression_list(p):
    '''expression_list : expression_list COMMA expression
                       | expression'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_condition(p):
    '''expression : expression EQ expression
                 | expression NE expression
                 | expression LT expression
                 | expression LE expression
                 | expression GT expression
                 | expression GE expression
                 | expression AND expression
                 | expression OR expression
                 | NOT expression'''
    if len(p) == 4 and p[1] == '(':
        p[0] = p[2]
    elif len(p) == 4:
        p[0] = ('cond', p[2], p[1], p[3])
    elif len(p) == 3:
        p[0] = ('not', p[2])
    else:
        p[0] = ('bool', p[1])

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p is None:
        print('Erro Sintatico: fim de ficheiro inesperado')
    else:
        print(f"Erro Sintatico na linha {p.lineno} perto de '{p.value}'")

if __name__ == "__main__":
    f_lexer = FortranLexer()
    f_lexer.build()
    parser = yacc.yacc()
    
    filepath = "../testFiles/ex5.f"

    try:
        with open(filepath, 'r') as f:
            test_code = f.read()
        
        print(f"--- A processar: {filepath} ---")
        
        ast = parser.parse(test_code, lexer=f_lexer.lexer)
        
        if ast:
            analyzer = SemanticAnalyzer()
            analyzer.analyze(ast)
            
            print("--- Árvore Final ---")
            pprint.pprint(ast)

            print("----- Código -----")
            generator = CodeGenerator()
            final_code = generator.generate(ast)

            for l in final_code:
                print(l)


        else:
            print("\nFalha ao gerar a AST.")

    except SemanticError as e:
        print(f"\n❌ Erro Semântico: {e}")
    except FileNotFoundError:
        print(f"Erro: O ficheiro '{filepath}' não foi encontrado.")
    except Exception as e:
        print(f"Erro durante o processamento: {e}")