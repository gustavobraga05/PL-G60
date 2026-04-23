PROGRAM TESTERRO
    INTEGER A, B, X, SOMA, VALOR
    REAL C
    
    ! Variáveis declaradas (OK)
    A = 10
    C = 5.5
    
    ! ERRO SEMÂNTICO: 'X' não foi declarada em lado nenhum
    X = 20
    
    ! ERRO SEMÂNTICO: 'SOMA' é usada numa expressão sem declaração
    B = A + SOMA
    
    ! ERRO SEMÂNTICO: 'VALOR' é usada no PRINT mas não existe
    PRINT *, 'Resultado:', VALOR
    
END