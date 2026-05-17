import sys
import pprint
import ply.yacc as yacc
from lexer import FortranLexer
import parser as parser_module
from semantic import SemanticAnalyzer
from symbolTable import SemanticError
from generator import CodeGenerator

def main():
    # Inicialização do Lexer
    f_lexer = FortranLexer()
    f_lexer.build()
    
    # Inicialização do Parser usando o módulo parser.py para as regras da gramática
    parser = yacc.yacc(module=parser_module)
    
    # Define o ficheiro a processar (argumento CLI ou default)
    filepath = sys.argv[1] if len(sys.argv) > 1 else "../testFiles/testes_enunciado/ex5.f"

    try:
        with open(filepath, 'r') as f:
            test_code = f.read()
        
        print(f"--- A processar: {filepath} ---")
        
        # Parsing
        ast = parser.parse(test_code, lexer=f_lexer.lexer)
        
        if ast:
            # Análise Semântica e Otimização
            analyzer = SemanticAnalyzer()
            analyzer.analyze(ast)
            
            print("--- Árvore Final ---")
            pprint.pprint(ast)

            print("----- Código -----")
            # Geração de Código
            generator = CodeGenerator()
            final_code = generator.generate(ast)

            for l in final_code:
                print(l)
        else:
            print("\nFalha ao gerar a AST.")

    except SemanticError as e:
        print(f"\n❌ Erro Semântico: {e}")
    except FileNotFoundError:
        print(f"Erro: O ficheiro '{filepath}' não foi encontrado.")
    except Exception as e:
        print(f"Erro durante o processamento: {e}")

if __name__ == "__main__":
    main()
