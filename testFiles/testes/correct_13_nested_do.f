      PROGRAM ARRAY
      INTEGER M(9), I, J
      DO 20 I = 1, 3
          DO 10 J = 1, 3
              M(I + J) = I + J
10        CONTINUE
20    CONTINUE
      PRINT *, M(3)
      END
