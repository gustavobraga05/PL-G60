import os
import subprocess
import re

def parse_expectations(md_path):
    expectations = {}
    if not os.path.exists(md_path):
        return expectations
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    rows = re.findall(r'\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\s*\|', content)
    for filename, result_type in rows:
        expectations[filename.strip()] = result_type.strip()
    return expectations

def run_test(file_path):
    cmd = ["python3", "src/main.py", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout
        error_output = result.stderr

        combined_output = output + error_output
        
        if "----- Código -----" in combined_output:
            parts = combined_output.split("----- Código -----")
            if len(parts) > 1 and parts[1].strip():
                return "✅ Correto", parts[1].strip()
        
        if "❌ Erro Semântico" in combined_output:
            err_msg = re.search(r"❌ Erro Semântico: (.*)", combined_output)
            return "❌ Erro Semântico", err_msg.group(1).strip() if err_msg else "Erro Semântico detectado"
        
        if "Erro Sintatico" in combined_output:
            err_msg = re.search(r"(Erro Sintatico.*)", combined_output)
            return "❌ Erro Sintático", err_msg.group(1).strip() if err_msg else "Erro Sintático detectado"

        return "❓ Desconhecido", combined_output.strip()
    except Exception as e:
        return "🔥 Crash", str(e)

def main():
    test_dir = "testFiles/testes"
    md_path = "testFiles/testes_compilador_fortran.md"
    
    expectations = parse_expectations(md_path)
    
    if not os.path.exists(test_dir):
        print(f"Erro: Diretorio {test_dir} não encontrado.")
        return

    files = sorted([f for f in os.listdir(test_dir) if f.endswith('.f')])
    
    passed = 0
    total = len(files)
    
    print("=" * 80)
    print(f"{'RELATÓRIO DE TESTES DO COMPILADOR FORTRAN':^80}")
    print("=" * 80)
    
    for filename in files:
        file_path = os.path.join(test_dir, filename)
        expected = expectations.get(filename, "N/A")
        
        result_type, detail = run_test(file_path)
       
        is_ok = False
        if "Correto" in expected and result_type == "✅ Correto":
            is_ok = True
        elif "Erro Semântico" in expected and result_type == "❌ Erro Semântico":
            is_ok = True
        elif "Erro Sintático" in expected and result_type == "❌ Erro Sintático":
            is_ok = True
            
        status_str = "✅ PASSOU" if is_ok else "❌ FALHOU"
        if is_ok: passed += 1
            
        print(f"\n Ficheiro: {filename}")
        print(f"    Esperado: {expected}")
        print(f"    Obtido:   {result_type}")
        print(f"    Status:   {status_str}")
        
        if result_type == "✅ Correto":
            print("   Código VM Gerado:")
            vm_lines = detail.split('\n')
            for line in vm_lines[:15]:
                print(f"      {line}")
            if len(vm_lines) > 15:
                print(f"      ... ({len(vm_lines)-15} mais linhas)")
        else:
            print(f"     Mensagem: {detail}")
        print("-" * 40)

    print("\n" + "=" * 80)
    print(f"RESUMO FINAL: {passed}/{total} TESTES PASSARAM")
    print("=" * 80)

if __name__ == "__main__":
    main()
