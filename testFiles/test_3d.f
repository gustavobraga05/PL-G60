PROGRAM TEST_3D
  INTEGER A(2,2,2)
  INTEGER X, Y, Z, V
  
  DO 30 X = 1, 2
    DO 20 Y = 1, 2
      DO 10 Z = 1, 2
        A(X,Y,Z) = X*100 + Y*10 + Z
10    CONTINUE
20  CONTINUE
30 CONTINUE

  V = A(2,1,2)
  PRINT *, 'A(2,1,2) = ', V
END
