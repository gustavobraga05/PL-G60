# Processamento de linguagens - Grupo 60
## Membros do grupo
* Francisco Contente - A106846
* Gustavo Braga - A107379
* Lucas Pinto - A107288

## Manual de utilização

### Correr os testes
Para correr os testes, execute o seguinte comando na raiz do projeto:
```bash
python3 tests.py
```

### Executar o compilador
Para executar o compilador sobre um ficheiro Fortran, deve navegar para a pasta `src` e correr o `main.py`. 

Por predefinição, o ficheiro executado é o `../testFiles/testes_enunciado/ex5.f`:
```bash
cd src
python3 main.py
```

Também pode escolher um ficheiro à sua escolha, passando o caminho como argumento:
```bash
python3 main.py <caminho_do_ficheiro>
```
Exemplo:
```bash
python3 parser.py ../testFiles/testes/correct_01_basic_arithmetic.f
```