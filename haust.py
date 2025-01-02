import json
import random
import time
import sys
from typing import List
from pathlib import Path
from web3 import Web3
from colorama import init, Fore, Style
import requests

# Initialize colorama
init(autoreset=True)

def log_info(message: str):
    print(f"{Fore.CYAN+Style.BRIGHT}{message}{Style.RESET_ALL}")

def log_success(message: str):
    print(f"{Fore.GREEN+Style.BRIGHT}{message}{Style.RESET_ALL}")

def log_error(message: str):
    print(f"{Fore.RED+Style.BRIGHT}{message}{Style.RESET_ALL}")

def log_kuning(message: str):
    print(f"{Fore.YELLOW+Style.BRIGHT}{message}{Style.RESET_ALL}")

def log_putih(message: str):
    print(f"{Fore.WHITE+Style.BRIGHT}{message}{Style.RESET_ALL}")

def prompt_user(question: str) -> int:
    while True:
        try:
            answer = input(f"{Fore.CYAN}{question}{Style.RESET_ALL} ")
            return int(answer)
        except ValueError:
            log_error("❗ Please enter a valid integer.")

def delay(seconds: float):
    time.sleep(seconds)

def load_private_keys(file_path: str = "privatekeys.txt") -> List[str]:
    try:
        keys = Path(file_path).read_text().strip().splitlines()
        if not keys:
            raise ValueError('❗ No private keys found in the file.')
        return keys
    except FileNotFoundError:
        log_error(f"❗ File {file_path} not found. Ensure the file exists and contains private keys.")
        sys.exit(1)
    except Exception as e:
        log_error(f"❗ Error loading private keys: {e}")
        sys.exit(1)

def load_proxies(file_path: str = "proxy.txt") -> List[str]:
    try:
        proxies = Path(file_path).read_text().strip().splitlines()
        if not proxies:
            raise ValueError('❗ No proxies found in the file.')
        return proxies
    except FileNotFoundError:
        log_error(f"❗ File {file_path} not found. Ensure the file exists and contains proxies.")
        sys.exit(1)
    except Exception as e:
        log_error(f"❗ Error loading proxies: {e}")
        sys.exit(1)

def load_addresses(file_path: str = "address.txt") -> List[str]:
    try:
        addresses = Path(file_path).read_text().strip().splitlines()
        if not addresses:
            raise ValueError('❗ No addresses found in the file.')
        # Validate addresses
        valid_addresses = []
        for addr in addresses:
            if Web3.is_address(addr):
                valid_addresses.append(Web3.to_checksum_address(addr))
            else:
                log_error(f"❗ Invalid address skipped: {addr}")
        if not valid_addresses:
            raise ValueError('❗ No valid addresses found in the file.')
        return valid_addresses
    except FileNotFoundError:
        log_error(f"❗ File {file_path} not found. Ensure the file exists and contains addresses.")
        sys.exit(1)
    except Exception as e:
        log_error(f"❗ Error loading addresses: {e}")
        sys.exit(1)

def get_random_proxy(proxies: List[str]) -> dict:
    proxy = random.choice(proxies)
    return {
        "http": proxy,
        "https": proxy
    }

def claim_faucet(address: str, proxies: List[str]) -> bool:
    url = "https://faucet-test.haust.network/api/claim"
    
    payload = json.dumps({
      "address": address
    })
    
    headers = {
      'accept': '*/*',
      'accept-language': 'en-US,en;q=0.9',
      'cache-control': 'no-cache',
      'content-type': 'application/json',
      'origin': 'https://faucet-test.haust.network',
      'pragma': 'no-cache',
      'priority': 'u=1, i',
      'referer': 'https://faucet-test.haust.network/',
      'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    
    while True:
        proxy_dict = get_random_proxy(proxies)
        try:
            response = requests.post(url, headers=headers, data=payload, proxies=proxy_dict, timeout=10)
            result = response.json()
            if "msg" in result and "Txhash" in result["msg"]:
                log_success(f"    ✅️ Successfully claimed faucet for address {address}. Waiting 60 seconds")
                time.sleep(60)
                return True
            elif "error" in result and "Too Many Requests" in result["error"]:
                log_error(f"    ⚠️ Faucet already claimed for {address}, waiting for 1 minute before retrying...")
                time.sleep(60)
            elif "msg" in result and "nonce too high" in result["msg"]:
                log_kuning(f"    ⚠️ Failed to claim faucet. Nonce too high {address}")
                return True
            elif "msg" in result and "exceeded" in result["msg"]:
                log_error(f"    ❌ Limit claim faucet for {address}. Waiting 60 seconds.")
                time.sleep(65)
            else:
                log_error(f"    ❌ Unexpected response for {address}: {result}")
                return False
        except requests.exceptions.ProxyError:
            log_error(f"    ❌ Proxy error with proxy {proxy_dict['http']}. Trying another proxy...")
            continue
        except requests.exceptions.ConnectTimeout:
            log_error(f"    ❌ Connection timed out with proxy {proxy_dict['http']}. Trying another proxy...")
            continue
        except requests.exceptions.ReadTimeout:
            log_error(f"    ❌ Read timed out with proxy {proxy_dict['http']}. Trying another proxy...")
            continue
        except Exception as e:
            log_error(f"    ❌ An unexpected error occurred while claiming faucet for {address}: {e}")
            time.sleep(60)

def select_recipient_option(private_keys: List[str], addresses: List[str]) -> int:
    print("\nSelect address to send:")
    print("1. Random address")
    print("2. Load from address.txt")
    print("3. Get address from next private key")
    print("4. Send to all address.txt with 1 private key")  # Added Option 4
    
    while True:
        choice = input(f"{Fore.CYAN}Enter your choice (1/2/3/4): {Style.RESET_ALL}")
        if choice in ['1', '2', '3', '4']:
            return int(choice)
        else:
            log_error("❗ Invalid choice. Please select 1, 2, 3, or 4.")

def get_recipient_address(option: int, private_keys: List[str], current_index: int, addresses: List[str], total_transactions: int, sent_count: int, pk_addresses_map: dict) -> str:
    if option == 1:
        # Random address
        return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])
    elif option == 2:
        # Load from address.txt in a round-robin fashion
        return addresses[sent_count % len(addresses)]
    elif option == 3:
        # Send to the next private key's address
        next_index = (current_index + 1) % len(private_keys)
        next_pk = private_keys[next_index]
        try:
            account = web3.eth.account.from_key(next_pk)
            return account.address
        except ValueError:
            log_error(f"❌ Invalid private key at index {next_index}. Using random address instead.")
            return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])
    elif option == 4:
        # Send to all address.txt with 1 private key
        # Assuming using the first private key for simplicity
        pk = private_keys[0]
        if pk not in pk_addresses_map:
            pk_addresses_map[pk] = 0  # Initialize sent count for this pk
        address_index = pk_addresses_map[pk] % len(addresses)
        recipient = addresses[address_index]
        pk_addresses_map[pk] += 1
        return recipient
    else:
        # Fallback to random address
        return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])

def print_welcome_message():
    print(Fore.WHITE + r"""
          
█▀▀ █░█ ▄▀█ █░░ █ █▄▄ █ █▀▀
█▄█ █▀█ █▀█ █▄▄ █ █▄█ █ ██▄
          """)
    print(Fore.GREEN + Style.BRIGHT + "HAUST Network Testnet Tools\n")
    print(Fore.YELLOW + Style.BRIGHT + "Join Telegram Channel: @gsc_lobby | @sirkel_testnet\n")

def transfer_eth():
    # Configuration
    NETWORK_URL = "https://rpc-test.haust.network"
    CHAIN_ID = 1570754601
    CURRENCY_SYMBOL = "HAUST"

    # Initialize Web3
    global web3
    web3 = Web3(Web3.HTTPProvider(NETWORK_URL))

    # If connecting to a network that uses Proof of Authority (PoA), uncomment the next line
    # web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    if not web3.is_connected():
        log_error("❌ Failed to connect to the Haust Testnet.")
        sys.exit(1)
    else:
        log_success("🌐 Successfully connected to the Haust Testnet.")

    num_transactions = prompt_user('📊 How many transactions would you like to send (ex. 100):')

    private_keys = load_private_keys()
    proxies = load_proxies()
    addresses = load_addresses()  # Load addresses for option 2

    # Select recipient option
    recipient_option = select_recipient_option(private_keys, addresses)
    log_info(f"📁 Selected recipient option: {recipient_option}")

    # Initialize a map to keep track of sent counts for Option 4
    pk_addresses_map = {}

    for idx, key in enumerate(private_keys):
        try:
            account = web3.eth.account.from_key(key)
        except ValueError:
            log_error(f"❌ Invalid private key: {key}")
            continue

        wallet_address = account.address
        log_putih(f"💎 Processing wallet: {wallet_address} ===========")

        # Claim faucet before sending
        claim_success = claim_faucet(wallet_address, proxies)
        if not claim_success:
            log_error(f"    ❌ Failed to claim faucet for {wallet_address}. Skipping...")
            continue

        try:
            balance = web3.eth.get_balance(wallet_address)
            eth_balance = web3.from_wei(balance, 'ether')
            log_info(f"    💲 Balance : {eth_balance:.6f} {CURRENCY_SYMBOL}")  # Formatted Balance
        except Exception as e:
            log_error(f"    ❌ Failed to retrieve balance for {wallet_address}: {e}")
            continue

        if balance == 0:
            log_error(f"    💀 Wallet {wallet_address} has zero balance. Skipping...")
            continue

        try:
            nonce = web3.eth.get_transaction_count(wallet_address, 'pending')
        except Exception as e:
            log_error(f"    ❌ Failed to get nonce for {wallet_address}: {e}")
            continue

        success_count = 0
        sent_count = 0  # Counter to keep track of sent transactions

        for i in range(num_transactions):
            # Get recipient address based on selected option
            recipient = get_recipient_address(recipient_option, private_keys, idx, addresses, num_transactions, sent_count, pk_addresses_map)
            sent_count += 1  # Increment sent_count regardless of option

            # Adjusted Amount Range: Changed from 0.00001-0.00005 to 0.0001-0.0010
            amount = random.uniform(0.0001, 0.0010)  # Amount in HAUST  # **Modified Line**
            # amount = 0.2
            gas_price = web3.eth.gas_price + web3.to_wei(1, 'gwei')

            tx = {
                'chainId': CHAIN_ID,
                'from': wallet_address,
                'to': recipient,
                'value': web3.to_wei(amount, 'ether'),
                'gasPrice': gas_price,
                'nonce': nonce
            }

            try:
                gas_limit = web3.eth.estimate_gas(tx)
                total_cost = web3.to_wei(amount, 'ether') + (gas_limit * gas_price)

                if balance < total_cost:
                    log_kuning(
                        f"    💀 Balance Tidak Cukup {CURRENCY_SYMBOL}"
                    )
                    break

                tx['gas'] = gas_limit
                signed_tx = web3.eth.account.sign_transaction(tx, key)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

                # Formatted Amount Display: 4 decimal places
                log_info(f"    🎁 Transaction {i+1} Sending {amount:.4f} HAUST to {recipient}...")  # **Modified Line**

                try:
                    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if tx_receipt.status == 1:
                        success_count += 1
                        log_success(f"    🚀 Transaction {i+1} successful with hash: {tx_hash.hex()}")
                    else:
                        log_error(f"    ❌ Transaction {i+1} failed.")
                except Exception as e:
                    log_error(f"    ❌ Failed to get receipt for transaction {i+1}: {e}")

                nonce += 1
                balance -= total_cost  # Update balance after successful transaction
                delay(1)  # Optional: Delay between transactions to avoid rate limits

            except ValueError as e:
                if 'replacement transaction underpriced' in str(e):
                    gas_price += web3.to_wei(2, 'gwei')  # Increment gas price
                    tx['gasPrice'] = gas_price
                    try:
                        signed_tx = web3.eth.account.sign_transaction(tx, key)
                        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        log_success(f"    ⚠️ Retried transaction {i+1} successful with hash: {tx_hash.hex()}")
                        nonce += 1
                        success_count += 1
                    except Exception as retry_e:
                        log_error(f"    ❌ Retry failed for transaction {i+1}: {retry_e}")
                elif 'insufficient funds for transfer' in str(e):
                    log_error(f"    💀 Balance Tidak Cukup")
                    break
                else:
                    log_error(f"    ❌ Transaction {i+1} error: {e}")
            except Exception as e:
                log_error(f"    ❌ Unexpected error during transaction {i+1}: {e}")
                break

        log_info(f"✨ Completed transfers from wallet {wallet_address}. Successful transactions: {success_count}/{num_transactions}")

def main():
    try:
        print_welcome_message()
        transfer_eth()
    except Exception as e:
        log_error(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
