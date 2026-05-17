import ply.lex as lex
import re

class FortranLexer:
    # Definição de Palavras Reservadas (Case-Insensitive)
    reserved = {
        'program': 'PROGRAM',
        'end': 'END',
        'integer': 'INTEGER',
        'real': 'REAL',
        'logical': 'LOGICAL',
        'if': 'IF',
        'then': 'THEN',
        'else': 'ELSE',
        'endif': 'ENDIF',
        'do': 'DO',
        'continue': 'CONTINUE',
        'goto': 'GOTO',
        'read': 'READ',
        'print': 'PRINT',
        'stop': 'STOP',
        'return': 'RETURN',
        'call': 'CALL',
        'function': 'FUNCTION',
        'subroutine': 'SUBROUTINE',
        'mod': 'MOD'
    }

    # Lista Completa de Tokens
    tokens = [
        'ID', 'LABEL', 'INT_CONST', 'REAL_CONST', 'STRING_CONST',
        'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER', 'ASSIGN',
        'LPAREN', 'RPAREN', 'COMMA', 'STAR',
        'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
        'AND', 'OR', 'NOT', 'TRUE', 'FALSE',
        'NEWLINE'
    ] + list(reserved.values())

    # Expressões Regulares Simples
    t_PLUS    = r'\+'
    t_MINUS   = r'-'
    t_TIMES   = r'\*'
    t_DIVIDE  = r'/'
    t_ASSIGN  = r'='
    t_LPAREN  = r'\('
    t_RPAREN  = r'\)'
    t_COMMA   = r','

    # Operadores de Comparação e Lógicos 
    t_EQ = r'\.EQ\.'
    t_NE = r'\.NE\.'
    t_LT = r'\.LT\.'
    t_LE = r'\.LE\.'
    t_GT = r'\.GT\.'
    t_GE = r'\.GE\.'
    t_AND = r'\.AND\.'
    t_OR  = r'\.OR\.'
    t_NOT = r'\.NOT\.'
    t_TRUE  = r'\.TRUE\.'
    t_FALSE = r'\.FALSE\.'

    t_ignore = ' \t'

    def __init__(self):
        self.lexer = None
        self.errors = []
        # Estados de contexto
        self.at_line_start = True
        self.expecting_label = False
        self.expecting_io_star = False

    def t_REAL_CONST(self, t):
        r'\d+\.\d+([ED][+-]?\d+)?'
        val = t.value.upper().replace('D', 'E')
        t.value = float(val)
        return t

    def t_INT_CONST(self, t):
        r'\d+'
        t.value = int(t.value)
        
        if self.at_line_start or self.expecting_label:
            t.type = 'LABEL'
            self.expecting_label = False
        
        self.at_line_start = False
        return t

    def t_ID(self, t):
        r'[a-zA-Z][a-zA-Z0-9_]*'
        val_lower = t.value.lower()
        t.type = self.reserved.get(val_lower, 'ID')
        
        if t.type in ['GOTO', 'DO']:
            self.expecting_label = True

        if t.type in ['READ', 'PRINT']:
            self.expecting_io_star = True
            
        self.at_line_start = False
        return t

    def t_STAR(self, t):
        r'\*'

        if self.expecting_io_star:
            t.type = 'STAR'
            self.expecting_io_star = False
            return t
        t.type = 'TIMES'
        return t

    def t_STRING_CONST(self, t):
        r"\'([^\']|\'\')*\'"
        t.value = t.value[1:-1].replace("''", "'")
        return t

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        self.at_line_start = True 
        self.expecting_io_star = False

    def t_comment(self, t):
        r'([Cc\*].*\n)|(!.*\n)'
        t.lexer.lineno += 1
        self.at_line_start = True

    def t_error(self, t):
        err = f"Linha {t.lineno}: Caractere ilegal '{t.value[0]}'"
        self.errors.append(err)
        t.lexer.skip(1)

    def build(self, **kwargs):
        kwargs.setdefault('reflags', re.IGNORECASE | re.MULTILINE)
        self.lexer = lex.lex(module=self, **kwargs)

    def test(self, data):
        self.lexer.input(data)
        while True:
            tok = self.lexer.token()
            if not tok: break
            print(tok)

