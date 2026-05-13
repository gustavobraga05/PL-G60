      PROGRAM SALTO
      INTEGER X
      X = 0
      X = X + 1
      IF (X .LT. 3) 
      THEN 
      GOTO 20 
      ENDIF
      PRINT *, X
      GOTO 30
20    X = X + 10
      PRINT *, X
30    CONTINUE
      END
