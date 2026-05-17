from typing import Tuple, Any


def is_numeric_constant(expr: Tuple[Any, ...]) -> bool:
    return expr[0] == 'val' and expr[2] in ['INT_CONST', 'REAL_CONST']


def is_boolean_constant(expr: Tuple[Any, ...]) -> bool:
    return expr[0] == 'val' and (expr[2] in ['TRUE', 'FALSE'] or str(expr[1]).upper() in ['.TRUE.', '.FALSE.'])


def fold_binop(expr: Tuple, symbols) -> Tuple:
    op = expr[1]
    left = fold_constants(expr[2], symbols)
    right = fold_constants(expr[3], symbols)

    if is_numeric_constant(left) and is_numeric_constant(right):
        val_l, type_l = left[1], left[2]
        val_r, type_r = right[1], right[2]

        new_val = None
        if op == '+':
            new_val = val_l + val_r
        elif op == '-':
            new_val = val_l - val_r
        elif op == '*':
            new_val = val_l * val_r
        elif op == '/':
            new_val = val_l / val_r

        new_type = 'REAL_CONST' if (type_l == 'REAL_CONST' or type_r == 'REAL_CONST') else 'INT_CONST'
        if new_type == 'INT_CONST':
            new_val = int(new_val)

        print(f"Otimizando: {val_l} {op} {val_r} -> {new_val}")
        return ('val', new_val, new_type)

    return ('binop', op, left, right)


def fold_unary(expr: Tuple, symbols) -> Tuple:
    op = expr[1]
    operand = fold_constants(expr[2], symbols)

    if is_numeric_constant(operand):
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


def fold_mod(expr: Tuple, symbols) -> Tuple:
    left = fold_constants(expr[1], symbols)
    right = fold_constants(expr[2], symbols)

    if is_numeric_constant(left) and is_numeric_constant(right):
        if right[1] == 0:
            return ('mod', left, right)
        new_val = int(left[1]) % int(right[1])
        print(f"Otimizando MOD: {left[1]} % {right[1]} -> {new_val}")
        return ('val', new_val, 'INT_CONST')

    return ('mod', left, right)


def fold_array(expr: Tuple, symbols) -> Tuple:
    return ('array', expr[1], fold_constants(expr[2], symbols))


def fold_call_or_array(expr: Tuple, symbols) -> Tuple:
    return ('call_or_array', expr[1], [fold_constants(arg, symbols) for arg in expr[2]])


def fold_call(expr: Tuple, symbols) -> Tuple:
    return ('call', expr[1], [fold_constants(arg, symbols) for arg in expr[2]])


def fold_cond(expr: Tuple, symbols) -> Tuple:
    op = expr[1]
    left = fold_constants(expr[2], symbols)
    right = fold_constants(expr[3], symbols)

    if left[0] == 'val' and right[0] == 'val':
        if is_numeric_constant(left) and is_numeric_constant(right):
            a = float(left[1])
            b = float(right[1])
            res = None
            if op == '.EQ.':
                res = (a == b)
            elif op == '.NE.':
                res = (a != b)
            elif op == '.LT.':
                res = (a < b)
            elif op == '.LE.':
                res = (a <= b)
            elif op == '.GT.':
                res = (a > b)
            elif op == '.GE.':
                res = (a >= b)
            if res is not None:
                val = '.TRUE.' if res else '.FALSE.'
                tp = 'TRUE' if res else 'FALSE'
                print(f"Otimizando cond: {left[1]} {op} {right[1]} -> {val}")
                return ('val', val, tp)

        if is_boolean_constant(left) and is_boolean_constant(right) and op in ['.AND.', '.OR.']:
            a = True if str(left[1]).upper() == '.TRUE.' or left[2] == 'TRUE' else False
            b = True if str(right[1]).upper() == '.TRUE.' or right[2] == 'TRUE' else False
            res = (a and b) if op == '.AND.' else (a or b)
            val = '.TRUE.' if res else '.FALSE.'
            tp = 'TRUE' if res else 'FALSE'
            print(f"Otimizando lógico: {left[1]} {op} {right[1]} -> {val}")
            return ('val', val, tp)

    return ('cond', op, left, right)


def fold_not(expr: Tuple, symbols) -> Tuple:
    operand = fold_constants(expr[1], symbols)
    if is_boolean_constant(operand):
        a = True if str(operand[1]).upper() == '.TRUE.' or operand[2] == 'TRUE' else False
        res = not a
        val = '.TRUE.' if res else '.FALSE.'
        tp = 'TRUE' if res else 'FALSE'
        print(f"Otimizando NOT: {operand[1]} -> {val}")
        return ('val', val, tp)

    return ('not', operand)


def fold_constants(expr: Tuple, symbols) -> Tuple:
    kind = expr[0]

    if kind == 'binop':
        return fold_binop(expr, symbols)
    if kind == 'unary':
        return fold_unary(expr, symbols)
    if kind == 'mod':
        return fold_mod(expr, symbols)
    if kind == 'array':
        return fold_array(expr, symbols)
    if kind == 'call_or_array':
        return fold_call_or_array(expr, symbols)
    if kind == 'call':
        return fold_call(expr, symbols)
    if kind == 'cond':
        return fold_cond(expr, symbols)
    if kind == 'not':
        return fold_not(expr, symbols)
    if kind == 'bool':
        return expr

    return expr
