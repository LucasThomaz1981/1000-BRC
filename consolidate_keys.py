import csv
import re
import os

def extract_from_csv(file_path):
    keys = set()
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # O formato parece ser FDR,CAISK,ID,ADDRESS,PRIVKEY,DATE,STATUS
                if len(row) >= 5:
                    priv_key = row[4].strip()
                    if len(priv_key) == 64: # Hex key
                        keys.add(priv_key)
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
    return keys

def extract_from_txt(file_path):
    keys = set()
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            content = f.read()
            # Encontrar hexadecimais de 64 caracteres
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            keys.update(hex_keys)
            # Encontrar WIFs
            wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            keys.update(wif_keys)
    except Exception as e:
        print(f"Erro ao ler TXT: {e}")
    return keys

def main():
    base_dir = '/home/ubuntu/extracted_data'
    all_keys = set()
    
    csv_file = os.path.join(base_dir, 'FDR_Master_Wallet_Complete_20251006_143555.csv')
    txt_file = os.path.join(base_dir, 'extracted_keys_and_addresses.txt')
    pasted_file = os.path.join(base_dir, 'pasted_content_2.txt')
    
    if os.path.exists(csv_file):
        all_keys.update(extract_from_csv(csv_file))
    
    if os.path.exists(txt_file):
        all_keys.update(extract_from_txt(txt_file))
        
    if os.path.exists(pasted_file):
        all_keys.update(extract_from_txt(pasted_file))

    print(f"Total de chaves únicas extraídas: {len(all_keys)}")
    
    with open('/home/ubuntu/consolidated_keys.txt', 'w') as f:
        for key in sorted(list(all_keys)):
            f.write(f"{key}\n")

if __name__ == "__main__":
    main()
