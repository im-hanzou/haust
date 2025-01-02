from eth_account import Account
import secrets
from datetime import datetime

def generate_wallets(num_wallets):
    Account.enable_unaudited_hdwallet_features()
    
    wallets = []
    
    for _ in range(num_wallets):
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        wallets.append((private_key, acct.address))
        
    return wallets

def save_to_separate_files(wallets):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open("privatekeys.txt", "a") as f_priv:
        for priv, _ in wallets:
            f_priv.write(f"{priv}\n")
    
    with open("addresses.txt", "a") as f_addr:
        for _, addr in wallets:
            f_addr.write(f"{addr}\n")
    
    return "privatekeys.txt", "addresses.txt"

def main():
    try:
        num = int(input("Masukkan jumlah wallet yang ingin dibuat: "))
        
        print("\nMembuat wallet...")
        wallets = generate_wallets(num)
        
        priv_file, addr_file = save_to_separate_files(wallets)
        print(f"\nWallet berhasil dibuat dan disimpan di file:")
        print(f"Private Keys: {priv_file}")
        print(f"Addresses: {addr_file}")
            
    except ValueError:
        print("Error: Masukkan angka yang valid")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()