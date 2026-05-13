      PROGRAM ERROFUNC
      INTEGER R
      INTEGER SOMA
      R = SOMA(1, 2, 3)
      PRINT *, R
      END

      INTEGER FUNCTION SOMA(A, B)
      INTEGER A, B
      SOMA = A + B
      RETURN
      END
