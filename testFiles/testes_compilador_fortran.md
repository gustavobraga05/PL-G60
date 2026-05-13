# Testes do Compilador Fortran 77

## Resumo dos Testes

| # | Ficheiro | Tipo | Funcionalidade Testada |
|---|---|---|---|
| 1 | `correct_01_basic_arithmetic.f` | ✅ Correto | Aritmética básica, PRINT, REAL e INTEGER |
| 2 | `correct_02_if_else.f` | ✅ Correto | IF / THEN / ELSE / ENDIF |
| 3 | `correct_03_do_loop.f` | ✅ Correto | Ciclo DO com LABEL e CONTINUE |
| 4 | `correct_04_arrays.f` | ✅ Correto | Arrays e acesso indexado |
| 5 | `correct_05_function.f` | ✅ Correto | Funções com argumento e RETURN |
| 6 | `correct_06_constant_folding.f` | ✅ Correto | Otimização: constant folding |
| 7 | `correct_07_constant_propagation.f` | ✅ Correto | Otimização: constant propagation |
| 8 | `correct_08_dead_code_elimination.f` | ✅ Correto | Otimização: eliminação de código morto |
| 9 | `correct_09_logical_operators.f` | ✅ Correto | LOGICAL, .AND., .OR., .NOT. |
| 10 | `correct_10_mod_real.f` | ✅ Correto | Função MOD, aritmética REAL |
| 11 | `correct_11_goto.f` | ✅ Correto | GOTO com rótulo |
| 12 | `correct_12_read.f` | ✅ Correto | READ * para INTEGER e REAL |
| 13 | `correct_13_nested_do.f` | ✅ Correto | Ciclos DO aninhados |
| 14 | `correct_14_multiplication_not.f` | ✅ Correto | Operador *, .NOT. sobre constante |
| 15 | `correct_15_factorial.f` | ✅ Correto | Programa completo — fatorial |
| 16 | `error_01_undeclared_variable.f` | ❌ Erro Semântico | Variável não declarada |
| 17 | `error_02_duplicate_declaration.f` | ❌ Erro Semântico | Declaração duplicada |
| 18 | `error_03_type_mismatch.f` | ❌ Erro Semântico | Incompatibilidade de tipos |
| 19 | `error_04_if_not_boolean.f` | ❌ Erro Semântico | Condição de IF não booleana |
| 20 | `error_05_do_real_variable.f` | ❌ Erro Semântico | Variável de controlo DO não inteira |
| 21 | `error_06_wrong_arg_count.f` | ❌ Erro Semântico | Número errado de argumentos |
| 22 | `error_07_undefined_label.f` | ❌ Erro Semântico | GOTO para rótulo inexistente |
| 23 | `error_08_missing_end.f` | ❌ Erro Sintático | Falta END |
| 24 | `error_09_malformed_expression.f` | ❌ Erro Sintático | Expressão malformada |
| 25 | `error_10_uninitialized_variable.f` | ❌ Erro Semântico | Variável usada sem inicialização |
