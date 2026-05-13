      PROGRAM PRINCIPAL
      INTEGER N, RES
      INTEGER FAT
      N = 5
      RES = FAT(N)
      PRINT *, RES
      END

      INTEGER FUNCTION FAT(N)
      INTEGER N, I, ACUM
      ACUM = 1
      DO 10 I = 1, N
          ACUM = ACUM * I
10    CONTINUE
      FAT = ACUM
      RETURN
      END
