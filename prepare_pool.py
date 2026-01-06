import re, os, json

def clean_rtf(text):
    # Remove metadados de arquivos RTF que quebram chaves privadas
    return re.sub(r'\{\*?\\[^{}]+\}|\\([a-z0-9]+)\s?|;', '', text)

def extract_keys():
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json', '.csv')
    keys_found = set()
    
    print("🛠️ Iniciando Garimpo de Chaves em todos os formatos...")
    
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.lower().endswith(exts) and f != 'MASTER_POOL.txt':
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', errors='ignore') as file:
                        content = file.read()
                        if path.lower().endswith('.rtf'):
                            content = clean_rtf(content)
                        
                        # Captura WIF (L, K, 5) e HEX (64 chars)
                        wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
                        hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
                        
                        for k in (wifs + hex_keys):
                            keys_found.add(k.strip())
                except: continue

    with open('MASTER_POOL.txt', 'w') as f:
        for k in sorted(list(keys_found)):
            f.write(f"{k}\n")
    
    print(f"✅ Sucesso! {len(keys_found)} chaves únicas unificadas.")

if __name__ == "__main__":
    extract_keys()
