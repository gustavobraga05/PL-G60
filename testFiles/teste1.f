PROGRAM SOMA_LOOP
    INTEGER N, TOTAL, I
    INTEGER W
    
    ! Inicializacao
    TOTAL = 0
    N = 10
    I = 1
    
    PRINT *, 'CALCULANDO A SOMA DE 1 A', N
    
    ! Ciclo DO com label 20
    DO 20 I = 1, N
        TOTAL = TOTAL + I
        PRINT *, 'PASSO:', I, ' SOMA ATUAL:', TOTAL
    20 CONTINUE
    
    PRINT *, 'RESULTADO FINAL:', TOTAL
    
END