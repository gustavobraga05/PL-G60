"""Optimizações independentes do analisador semântico.

Fornece `fold_constants(expr, symbols)` que aplica constant folding e
propagação de constantes usando a tabela de símbolos.
"""
from typing import Tuple, Any


def fold_constants(expr: Tuple, symbols) -> Tuple:
    kind = expr[0]

    if kind == 'val' and expr[2] == 'ID':
        name = expr[1]
        try:
            entry = symbols.lookup(name)
            const = entry.get('const')
            const_type = entry.get('const_type')
            if const is not None:
                return ('val', const, const_type)
        except Exception:
            pass

    # binop
    if kind == 'binop':
        op = expr[1]
        left = fold_constants(expr[2], symbols)
        right = fold_constants(expr[3], symbols)

        if left[0] == 'val' and right[0] == 'val':
            val_l, type_l = left[1], left[2]
            val_r, type_r = right[1], right[2]

            if type_l in ['INT_CONST', 'REAL_CONST'] and type_r in ['INT_CONST', 'REAL_CONST']:
                new_val = None
                if op == '+': new_val = val_l + val_r
                elif op == '-': new_val = val_l - val_r
                elif op == '*': new_val = val_l * val_r
                elif op == '/': new_val = val_l / val_r

                new_type = 'REAL_CONST' if (type_l == 'REAL_CONST' or type_r == 'REAL_CONST') else 'INT_CONST'
                if new_type == 'INT_CONST':
                    new_val = int(new_val)

                print(f"Otimizando: {val_l} {op} {val_r} -> {new_val}")
                return ('val', new_val, new_type)

        return ('binop', op, left, right)

    # unary
    if kind == 'unary':
        op = expr[1]
        operand = fold_constants(expr[2], symbols)
        if operand[0] == 'val' and operand[2] in ['INT_CONST', 'REAL_CONST']:
            val = operand[1]
            if op == '+':
                return ('val', val, operand[2])
            elif op == '-':
                new_val = -val
                new_type = operand[2]
                if new_type == 'INT_CONST':
                    new_val = int(new_val)
                print(f"Otimizando unário: {op}{val} -> {new_val}")
                return ('val', new_val, new_type)
        return ('unary', op, operand)

    # mod
    if kind == 'mod':
        left = fold_constants(expr[1], symbols)
        right = fold_constants(expr[2], symbols)
        if left[0] == 'val' and right[0] == 'val' and left[2] in ['INT_CONST', 'REAL_CONST'] and right[2] in ['INT_CONST', 'REAL_CONST']:
            if right[1] == 0:
                return ('mod', left, right)
            new_val = int(left[1]) % int(right[1])
            print(f"Otimizando MOD: {left[1]} % {right[1]} -> {new_val}")
            return ('val', new_val, 'INT_CONST')
        return ('mod', left, right)

    if kind == 'array':
        return ('array', expr[1], fold_constants(expr[2], symbols))

    if kind == 'call_or_array':
        return ('call_or_array', expr[1], [fold_constants(arg, symbols) for arg in expr[2]])

    if kind == 'call':
        return ('call', expr[1], [fold_constants(arg, symbols) for arg in expr[2]])

    # cond
    if kind == 'cond':
        op = expr[1]
        left = fold_constants(expr[2], symbols)
        right = fold_constants(expr[3], symbols)

        if left[0] == 'val' and right[0] == 'val':
            def is_bool(v):
                return v[2] in ['TRUE', 'FALSE'] or str(v[1]).upper() in ['.TRUE.', '.FALSE.']

            if left[2] in ['INT_CONST', 'REAL_CONST'] and right[2] in ['INT_CONST', 'REAL_CONST']:
                a = float(left[1])
                b = float(right[1])
                res = None
                if op == '.EQ.': res = (a == b)
                elif op == '.NE.': res = (a != b)
                elif op == '.LT.': res = (a < b)
                elif op == '.LE.': res = (a <= b)
                elif op == '.GT.': res = (a > b)
                elif op == '.GE.': res = (a >= b)
                if res is not None:
                    val = '.TRUE.' if res else '.FALSE.'
                    tp = 'TRUE' if res else 'FALSE'
                    print(f"Otimizando cond: {left[1]} {op} {right[1]} -> {val}")
                    return ('val', val, tp)

            if is_bool(left) and is_bool(right) and op in ['.AND.', '.OR.']:
                a = True if str(left[1]).upper() == '.TRUE.' or left[2] == 'TRUE' else False
                b = True if str(right[1]).upper() == '.TRUE.' or right[2] == 'TRUE' else False
                res = (a and b) if op == '.AND.' else (a or b)
                val = '.TRUE.' if res else '.FALSE.'
                tp = 'TRUE' if res else 'FALSE'
                print(f"Otimizando lógico: {left[1]} {op} {right[1]} -> {val}")
                return ('val', val, tp)

        return ('cond', op, left, right)

    if kind == 'not':
        operand = fold_constants(expr[1], symbols)
        if operand[0] == 'val' and (operand[2] in ['TRUE', 'FALSE'] or str(operand[1]).upper() in ['.TRUE.', '.FALSE.']):
            a = True if str(operand[1]).upper() == '.TRUE.' or operand[2] == 'TRUE' else False
            res = not a
            val = '.TRUE.' if res else '.FALSE.'
            tp = 'TRUE' if res else 'FALSE'
            print(f"Otimizando NOT: {operand[1]} -> {val}")
            return ('val', val, tp)
        return ('not', operand)

    if kind == 'bool':
        return expr

    return expr
