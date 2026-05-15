# Relatório — Compilador Fortran

---

## 1. Introdução

Este relatório documenta o desenvolvimento de um compilador para a linguagem Fortran, realizado no âmbito do estudo dos princípios fundamentais de construção de compiladores. O objetivo principal é explorar e implementar as etapas essenciais do processo de compilação: análise léxica, análise sintática, análise semântica e geração de código. Estes conceitos são fundamentais para compreender o funcionamento interno das linguagens de programação e dos seus sistemas de tradução.

O projeto foi desenvolvido em Python, recorrendo à biblioteca PLY (Python Lex-Yacc), que facilitou a implementação das fases de análise léxica e sintática. A especificação da linguagem Fortran 77 foi utilizada como referência de modo a garantir a conformidade do compilador com os padrões da linguagem.

---

## 2. Descrição Geral do Projeto

O compilador foi organizado em módulos distintos, cada um responsável por uma fase específica do processo de compilação. A estrutura do projeto é composta pelos seguintes ficheiros, localizados na pasta `src/`:

| Ficheiro | Responsabilidade |
|---|---|
| `lexer.py` | Análise léxica — converte código-fonte em tokens |
| `parser.py` | Análise sintática — constrói a AST a partir dos tokens |
| `semantic.py` | Análise semântica — valida tipos, escopos e regras contextuais |
| `symbolTable.py` | Tabela de símbolos com suporte a escopos aninhados |
| `optimizer.py` | Otimizações de código intermediário (constant folding, etc.) |
| `generator.py` | Geração de código a partir da AST validada |

Os ficheiros de teste localizam-se na pasta `testFiles/`, contendo programas em Fortran utilizados para validar cada módulo do compilador.

---

## 3. Objetivos

Os principais objetivos do projeto foram:

- Explorar os conceitos fundamentais de compiladores, implementando as fases de análise léxica, sintática, semântica e geração de código para a linguagem Fortran.
- Desenvolver um compilador funcional capaz de processar programas escritos em Fortran e gerar uma saída válida em código de máquina virtual.
- Garantir a qualidade do sistema através de testes, validando o correto funcionamento de cada módulo individualmente e em conjunto.

---

## 4. Análise Léxica

A análise léxica constitui a primeira etapa do processo de compilação. É responsável por ler o código-fonte em Fortran e convertê-lo numa sequência de tokens, que representam as unidades léxicas básicas da linguagem. Esta fase identifica e classifica palavras-chave, identificadores, operadores, delimitadores e literais, ignorando comentários e espaços em branco.

A implementação encontra-se no ficheiro `lexer.py`, utilizando a biblioteca PLY. Foram definidas expressões regulares para reconhecer os diferentes tokens da linguagem, incluindo palavras-chave, identificadores, números inteiros e reais, operadores aritméticos e relacionais, entre outros.

### Tokens reconhecidos

Os principais grupos de tokens suportados são:

- **Palavras-chave:** `PROGRAM`, `END`, `INTEGER`, `REAL`, `LOGICAL`, `IF`, `THEN`, `ELSE`, `ENDIF`, `DO`, `CONTINUE`, `GOTO`, `READ`, `PRINT`, `RETURN`, `FUNCTION`, `MOD`, entre outros.
- **Identificadores e constantes:** `ID`, `INT_CONST`, `REAL_CONST`, `STRING_CONST`.
- **Operadores aritméticos:** `PLUS`, `MINUS`, `TIMES`, `DIVIDE`, `POWER`.
- **Operadores relacionais e lógicos (padrão F77):** `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`, `.AND.`, `.OR.`, `.NOT.`, `.TRUE.`, `.FALSE.`.

Exemplo de definição de alguns tokens:

```python
def t_REAL_CONST(self, t):
    r'\d+\.\d+([ED][+-]?\d+)?'
    val = t.value.upper().replace('D', 'E')
    t.value = float(val)
    return t

def t_ID(self, t):
    r'[a-zA-Z][a-zA-Z0-9_]*'
    val_lower = t.value.lower()
    t.type = self.reserved.get(val_lower, 'ID')
    return t
```

### Características relevantes

- **Case-insensitivity:** O lexer converte identificadores para minúsculas antes de os comparar com a tabela de palavras reservadas, em conformidade com a especificação Fortran.
- **Gestão contextual de LABELs:** O token numérico no início de uma linha é interpretado como `LABEL` (e não `INT_CONST`), usando a flag `at_line_start`.
- **Distinção entre `STAR` e `TIMES`:** Após um comando `READ` ou `PRINT`, o `*` é interpretado como `STAR` (formato livre), não como multiplicação, usando a flag `expecting_io_star`.
- **Comentários:** Linhas que começam por `C`, `c` ou `*` são ignoradas, assim como comentários inline iniciados por `!`.

---

## 5. Análise Sintática

A análise sintática é a segunda etapa do processo de compilação. Tem como objetivo verificar se a sequência de tokens produzida pelo analisador léxico forma estruturas válidas segundo as regras gramaticais da linguagem Fortran. Para isso, é utilizada uma gramática livre de contexto, definida formalmente no ficheiro `parser.py` com recurso ao PLY.

### Gramática implementada

A gramática cobre as principais construções da linguagem Fortran 77:

- Declarações de variáveis (`INTEGER`, `REAL`, `LOGICAL`) e arrays (unidimensionais e multidimensionais).
- Atribuições e acessos a arrays com suporte a múltiplos índices (ex: `M(I,J) = VAL`).
- Funções com lista de argumentos e valor de retorno tipado.
- Comandos de controlo de fluxo: `IF/THEN/ELSE/ENDIF`, `DO/CONTINUE`, `GOTO`.
- Comandos de I/O: `READ` e `PRINT`.
- Expressões aritméticas, lógicas e relacionais, com precedência correta.

Exemplos de regras gramaticais implementadas:

```python
def p_start(p):
    '''start : program functions'''
    p[0] = (p[1], p[2])

def p_program(p):
    '''program : PROGRAM ID body END 
               | empty'''
    p[0] = ('program', p[2], p[3])

def p_body(p):
    '''body : declarations statements'''
    p[0] = {'decls': p[1], 'stmts': p[2]}

def p_declaration(p):
    '''declaration : type_spec id_list'''
    p[0] = ('decl', p[1], p[2])

def p_do_stmt(p):
    '''do_stmt : DO LABEL ID ASSIGN expression COMMA expression'''
    p[0] = ('do', p[2], p[3], p[5], p[7])
```

### Precedência de operadores

A precedência é definida explicitamente para garantir a correta interpretação das expressões:

```python
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'UMINUS', 'UPLUS'),
)
```

### Árvore Sintática Abstrata (AST)

O parser constrói uma AST que representa a estrutura hierárquica do programa na seguinte estrutura ( programa, lista de funções). Por exemplo o seguinte programa: 

```fortran
PROGRAM TESTE
INTEGER I
I = 2 + 3
END
```

Produz a AST:

```python
(('program', 'TESTE',
  {'decls': [('decl', 'INTEGER', ['I'])],
   'stmts': [('assign', 'I', ('binop', '+', ('val', 2, 'INT_CONST'), ('val', 3, 'INT_CONST')))]}),
[])
```

Esta AST serve de base para as fases seguintes de análise semântica e geração de código.

---

## 6. Análise Semântica

A análise semântica é responsável por validar a correção lógica e contextual do programa após a análise sintática. Esta fase assegura que o código respeita as regras semânticas da linguagem Fortran, como coerência de tipos, existência e âmbito de identificadores, e chamadas a funções com argumentos corretos.

A implementação encontra-se no ficheiro `semantic.py`, com recurso à tabela de símbolos definida em `symbolTable.py`. A tabela suporta escopos aninhados, permitindo a correta gestão de variáveis globais, locais e argumentos de funções.

### Principais validações

- **Declaração e uso de variáveis:** Verifica duplicação de identificadores e uso de variáveis não declaradas. Uma variável usada sem declaração prévia lança um `SemanticError`.
- **Verificação de tipos:** Garante compatibilidade entre tipos em atribuições, operações aritméticas e chamadas de funções.
- **Validação de condições:** Confirma que condições em `IF` e `DO` são do tipo booleano, e que variáveis de controlo de ciclos são inteiras.
- **Validação de Matrizes:** Verifica se o número de índices fornecido em acessos ou atribuições coincide com o número de dimensões declaradas, e se todos os índices são do tipo `INTEGER`.
- **Gestão de escopos:** Cada função possui a sua própria tabela de símbolos, isolando variáveis locais das globais.
- **Gestão de rótulos:** Valida a existência e correspondência correta de rótulos para comandos `DO` e `CONTINUE`.
- **Otimizações:** Aplica constant folding e propagação de constantes através do módulo `optimizer.py` durante a travessia da AST.

### Tabela de símbolos

Cada entrada na tabela de símbolos para um array contém:

```python
{
    'type': 'INTEGER',       # Tipo da variável
    'initialized': False,    # Se já foi atribuída
    'kind': 'array',         # 'scalar', 'array' ou 'function'
    'shape': [3, 3],         # Dimensões da matriz (ex: M(3,3))
    'total_size': 9,         # Tamanho total (produto das dimensões)
    'const': None,           
    'const_type': None,
}
```

---

## 7. Otimizações

O módulo `optimizer.py` implementa otimizações independentes que são aplicadas durante a análise semântica, antes da geração de código. As otimizações operam diretamente sobre os nós da AST, substituindo subárvores por valores constantes sempre que possível.

### 7.1 Constant Folding

O constant folding avalia em tempo de compilação expressões cujos operandos são todos constantes conhecidas, eliminando operações desnecessárias em tempo de execução.

**Exemplo — operação aritmética:**

Código Fortran:
```fortran
X = 4 * 2 + 10
```

Sem otimização, o gerador emitiria:
```
PUSHI 4
PUSHI 2
MUL
PUSHI 10
ADD
STOREG 0
```

Com constant folding, a expressão `4 * 2` é dobrada para `8` e depois `8 + 10` para `18`, gerando apenas:
```
PUSHI 18
STOREG 0
```

**Exemplo — operador MOD:**

```fortran
X = MOD(10, 3)
```

Resultado em tempo de compilação: `10 % 3 → 1`

```
PUSHI 1
STOREG 0
```

### 7.2 Otimização de Condições

Expressões condicionais com operandos constantes são avaliadas em tempo de compilação.

**Exemplo:**

```fortran
IF (3 .GT. 1) THEN ...
```

A condição `3 .GT. 1` é sempre verdadeira, sendo substituída por `.TRUE.` na AST, eliminando o salto condicional no código gerado.

### 7.3 Otimização de NOT

Expressões `.NOT.` sobre valores booleanos constantes são invertidas diretamente.

**Exemplo:**

```fortran
.NOT. .TRUE.  →  .FALSE.
```


### 7.4 Eliminação de Código Morto
 
A eliminação de código morto (*dead code elimination*) é aplicada durante a análise semântica, no método `visit_if` do `SemanticAnalyzer`. Quando a condição de um `IF` é avaliada como uma constante booleana em tempo de compilação, o bloco que nunca será executado é removido diretamente da AST, sem gerar qualquer instrução para ele.
 
A lógica funciona da seguinte forma:
 
```python
if cond_opt[0] == 'val' and (cond_opt[2] in ['TRUE', 'FALSE'] or ...):
    is_true = True if (cond_opt[2] == 'TRUE' or ...) else False
    if is_true:
        # Mantém apenas o bloco 'then', descarta o 'else'
        return new_then
    else:
        # Mantém apenas o bloco 'else' (se existir), descarta o 'then'
        return new_else if else_stmts else None
```
 
Esta otimização trabalha em conjunto com o constant folding — primeiro o constant folding avalia a condição para `.TRUE.` ou `.FALSE.`, e só depois o eliminador de código morto decide qual o ramo a manter.
 
**Exemplo — condição sempre verdadeira:**
 
```fortran
IF (10 .GT. 3) THEN
    X = 1
ELSE
    X = 2
ENDIF
```
 
O constant folding reduz `10 .GT. 3` a `.TRUE.`. A eliminação de código morto descarta o ramo `ELSE` por completo, ficando a AST equivalente a:
 
```fortran
X = 1
```
 
O código gerado é simplesmente:
 
```
PUSHI 1
STOREG 0
```
 
Em vez do código com saltos condicionais que seria gerado sem esta otimização:
 
```
PUSHI 1       ! avaliação da condição
PUSHI 1
INFEQ
JZ IFELSE1
PUSHI 1
STOREG 0
JUMP IFEND1
IFELSE1:
PUSHI 2
STOREG 0
IFEND1:
```
 
**Exemplo — condição sempre falsa, sem ramo ELSE:**
 
```fortran
IF (.FALSE.) THEN
    PRINT *, 'nunca executado'
ENDIF
```
 
O bloco inteiro é eliminado da AST — não gera nenhuma instrução.
 
**Interação com constant propagation:**
 
A eliminação de código morto torna-se ainda mais poderosa quando combinada com constant propagation. Por exemplo:
 
```fortran
INTEGER FLAG
FLAG = 0
IF (FLAG .EQ. 1) THEN
    PRINT *, 'nunca'
ENDIF
```
 
A constant propagation substitui `FLAG` por `0`, o constant folding avalia `0 .EQ. 1` como `.FALSE.`, e a eliminação de código morto remove o bloco `THEN` inteiramente.
 
### 7.5 Limitações das Otimizações
 
As otimizações implementadas têm algumas limitações relevantes:
 
- **Sem análise de fluxo de controlo:** Se uma variável for modificada dentro de um bloco `IF` ou `DO`, o compilador pode não reconhecer que o valor constante deixou de ser válido, podendo propagar um valor incorreto.
- **Arrays não são otimizados:** O constant folding não é aplicado a acessos a arrays, uma vez que os índices podem variar em tempo de execução.
- **Eliminação de código morto limitada a `IF`:** A eliminação de código morto só atua em blocos condicionais com condição constante. Código morto após `GOTO` ou em ciclos `DO` com limites impossíveis não é eliminado.
- **Divisão por zero não é detetada:** O otimizador de `MOD` verifica divisão por zero e recua para o nó original, mas para a divisão aritmética (`/`) não existe essa verificação explícita.
---

## 8. Geração de Código

A geração de código é a fase final do processo de compilação, onde a AST validada semanticamente é convertida numa sequência de instruções de uma máquina virtual baseada em pilha. O objetivo é produzir uma representação executável do programa Fortran.

A implementação encontra-se no ficheiro `generator.py`, utilizando o padrão de visita (visitor pattern) para percorrer recursivamente a AST e gerar as instruções correspondentes a cada nó.

### Principais características

**Gestão de memória:** As variáveis globais são alocadas em endereços fixos (via `PUSHG`/`STOREG`), enquanto as variáveis locais de funções usam endereços relativos à frame atual (via `PUSHL`/`STOREL`). O gerador mantém um dicionário `offsets` para mapear cada identificador ao seu endereço.

**Funções:** O gerador cria um prólogo para cada função que: mapeia os argumentos com offsets negativos em relação ao topo da frame, reserva espaço para variáveis locais com `PUSHN`, e termina com `RETURN`. O slot de retorno (nome da função) é mapeado para `-(n+1)`, onde `n` é o número de argumentos.

**Controlo de fluxo:**
- `DO`: gera etiquetas de início e fim de ciclo, com incremento e verificação da condição.
- `IF/ELSE`: gera saltos condicionais `JZ` para os ramos `ELSE` e `IFEND`.
- `GOTO`: gera um salto incondicional `JUMP`.

### Exemplo de geração de código

Dado o seguinte código Fortran:

```fortran
PROGRAM EXEMPLO
INTEGER A, B, C
A = 4
B = 2
C = (A * B + 3) - 1
PRINT *, C
END
```

O código gerado seria:

```
PUSHN 3
PUSHI 4
STOREG 0       ! A = 4
PUSHI 2
STOREG 1       ! B = 2
PUSHG 0        ! A
PUSHG 1        ! B
MUL            ! A * B
PUSHI 3
ADD            ! + 3
PUSHI 1
SUB            ! - 1
STOREG 2       ! C = resultado
PUSHG 2        ! C
WRITEI
WRITELN
STOP
```

### Suporte a Matrizes e Linearização

O compilador suporta arrays multidimensionais (matrizes) de qualquer dimensão. Como a memória da máquina virtual (EWVM) é linear, o compilador implementa a estratégia de **Row-Major Linearization** para mapear os múltiplos índices para um único offset de memória.

**Fórmula de Linearização:**
Para uma matriz $M(d_n)$, o offset para um acesso $M(i_0, i_1, \dots, i_n)$ é calculado como:
$Offset = (\dots((i_0-1) \times d_1 + (i_1-1)) \times d_2 + \dots ) \times d_n + (i_n-1)$

O gerador de código constrói dinamicamente uma sub-árvore AST que realiza este cálculo em tempo de execução, garantindo que o endereço correto seja acedido.

**Exemplo de Código Gerado:**
Para um acesso `M(I,J)` em uma matriz `INTEGER M(3,3)`, o compilador gera:

```
PUSHGP          # Base da memória
PUSHI <offset_M> # Offset inicial de M
PADD
PUSHG I         # Cálculo do índice linearizado:
PUSHI 1         # (I - 1)
SUB
PUSHI 3         # * ncols (d1)
MUL
PUSHG J         # + (J - 1)
PUSHI 1
SUB
ADD
PADD            # Soma offset ao ponteiro base
LOAD 0          # Carrega o valor
```

A reserva de memória (instrução `PUSHN`) também é atualizada para considerar o `total_size` linearizado da matriz, garantindo espaço suficiente para todos os elementos.

---

## 9. Conclusão

O desenvolvimento deste compilador para Fortran permitiu consolidar e aplicar os conceitos fundamentais da teoria de compiladores, desde a análise léxica até à geração de código. Cada fase foi implementada de forma modular, o que facilitou o desenvolvimento, teste e manutenção individual de cada componente.

A análise léxica, com recurso ao PLY, mostrou-se adequada para lidar com as particularidades do Fortran, como a insensibilidade a maiúsculas/minúsculas, a distinção contextual de rótulos e a interpretação do operador `*` em contextos diferentes.

A análise sintática cobriu as principais construções da linguagem Fortran 77, produzindo uma AST que serve de interface limpa entre o front-end e o back-end do compilador. A análise semântica assegurou a correção lógica dos programas através de validações de tipos, escopos e uso de variáveis. O recente suporte a **matrizes multidimensionais** expandiu significativamente a capacidade de processamento de dados do compilador, utilizando técnicas robustas de linearização de memória.

O módulo de otimizações, com constant folding e propagação de constantes, permitiu reduzir o número de instruções geradas em casos comuns, melhorando a eficiência do código produzido. No entanto, as otimizações implementadas têm um âmbito local e não contemplam análise de fluxo de controlo, eliminação de código morto ou otimizações inter-procedurais — aspetos que poderiam ser explorados em trabalho futuro.

A geração de código para uma máquina virtual baseada em pilha revelou-se uma escolha adequada para este projeto, simplificando a tradução de expressões e a gestão de memória. A distinção entre variáveis globais e locais, a gestão de frames de função e o suporte a arrays constituíram os principais desafios desta fase.

Em suma, o compilador desenvolvido é funcional para um subconjunto representativo da linguagem Fortran 77, cumprindo os objetivos propostos e servindo como base sólida para futuras extensões.
