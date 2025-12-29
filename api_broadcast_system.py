import requests
import time
import re
import sys
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
PASSWORD = "Benjamin2020*1981$"
MNEMONIC_11 = "tree dwarf rubber off tree finger hair hope emerge earn friend"

class BalanceChecker:
    def __init__(self):
        # Lista de APIs para redundância
        self.apis = [
            "https://mempool.space/api/address/{}/utxo",
            "https://blockstream.info/api/address/{}/utxo",
            "https://blockchain.info/unspent?active={}"
        ]
        self.current_api_idx = 0

    def get_utxos(self, address):
        """Tenta obter UTXOs alternando entre APIs em caso de erro"""
        for _ in range(len(self.apis)):
            url = self.apis[self.current_api_idx].format(address)
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    # Normalização básica (Blockchain.info tem formato diferente)
                    if "unspent_outputs" in data: # Formato Blockchain.info
                        return self._parse_blockchain_info(data)
                    return self._parse_electrum_style(data) # Formato Mempool/Blockstream
                
                # Se der erro 429 (Too Many Requests), troca de API
                if r.status_code == 429:
                    self.current_api_idx = (self.current_api_idx + 1) % len(self.apis)
            except:
                self.current_api_idx = (self.current_api_idx + 1) % len(self.apis)
            
            time.sleep(0.5) # Delay entre tentativas de fallback
        return 0, []

    def _parse_electrum_style(self, data):
        if not data: return 0, []
        total = sum(u['value'] for u in data)
        return total, data

    def _parse_blockchain_info(self, data):
        utxos = []
        total = 0
        for u in data.get('unspent_outputs', []):
            total += u['value']
            utxos.append({
                'txid': u['tx_hash_big_endian'],
                'vout': u['tx_output_n'],
                'value': u['value']
            })
        return total, utxos

checker = BalanceChecker()

def create_tx_hex(addr, wif, utxos):
    try:
        total_in = sum(u['value'] for u in utxos)
        fee = 10000 # Taxa levemente maior para garantir prioridade
        amount = total_in - fee
        if amount > 546:
            tx = Transaction(network='bitcoin')
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            print(f"HEX_GEN:{tx.raw_hex()}")
            return True
    except: pass
    return False

def clean_rtf(filename):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            clean_text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', content)
            clean_text = re.sub(r'[{}]', '', clean_text)
            return clean_text
    except: return ""

def run_liquidation():
    print(f"🚀 INICIANDO PROTOCOLO COM FALLBACK DE API")
    
    # 1. PROCESSAR ARQUIVOS (Alta Prioridade)
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']
    keys_found = set()
    for f in files:
        text = clean_rtf(f) if f.endswith('.rtf') else ""
        if not text:
            try:
                with open(f, 'r', errors='ignore') as file: text = file.read()
            except: continue
        keys_found.update(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', text))
        keys_found.update(re.findall(r'\b[0-9a-fA-F]{64}\b', text))

    print(f"📦 Chaves únicas encontradas: {len(keys_found)}")
    for wif in keys_found:
        for comp in [True, False]:
            try:
                k = Key(wif, network='bitcoin', compressed=comp)
                bal, utxos = checker.get_utxos(k.address())
                if bal > 0:
                    print(f"💰 SALDO EM ARQUIVO: {k.address()} | {bal} sats")
                    create_tx_hex(k.address(), wif, utxos)
                time.sleep(0.5)
            except: continue

    # 2. BRUTE-FORCE BIP39
    print("🔎 Iniciando Brute-force Mnemônico...")
    words = Mnemonic('english').words
    for word in words:
        mnemonic = f"{MNEMONIC_11} {word}"
        try:
            master = HDKey.from_passphrase(mnemonic, PASSWORD, network='bitcoin')
            for purpose in [44, 49, 84]:
                for i in range(25): # Foco nos 25 primeiros de cada tipo
                    path = f"m/{purpose}'/0'/0'/0/{i}"
                    derived = master.subkey_for_path(path)
                    wif = derived.wif()
                    
                    # Determinar endereço pelo propósito
                    for comp in [True, False]:
                        k = Key(wif, network='bitcoin', compressed=comp)
                        if purpose == 44: addr = k.address()
                        elif purpose == 49: addr = k.address(witness_type='p2sh-p2wpkh')
                        else: addr = k.address(witness_type='p2wpkh')
                        
                        bal, utxos = checker.get_utxos(addr)
                        if bal > 0:
                            print(f"💰 SALDO EM MNEMÔNICO: {addr} ({path}) | {bal} sats")
                            create_tx_hex(addr, wif, utxos)
                        time.sleep(0.5)
        except: continue

if __name__ == "__main__":
    run_liquidation()
