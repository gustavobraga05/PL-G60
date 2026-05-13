      PROGRAM LOGICOS
      LOGICAL FLAG, RES
      INTEGER A, B
      A = 5
      B = 10
      FLAG = .TRUE.
      RES = FLAG .AND. (A .LT. B)
      IF (RES) THEN
          PRINT *, A
      ENDIF
      END
