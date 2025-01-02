import json
import random
import time
import sys
from typing import List
from pathlib import Path
from web3 import Web3
from colorama import init, Fore, Style
import requests
from datetime import datetime, timedelta

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

def countdown_timer(target_time):
    while True:
        current_time = datetime.now()
        if current_time >= target_time:
            break
        
        time_left = target_time - current_time
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        sys.stdout.write(f"\r⏳ Cooldown: {hours:02d}:{minutes:02d}:{seconds:02d} remaining until next cycle")
        sys.stdout.flush()
        time.sleep(1)
    print("\n✨ Cooldown complete! Starting new cycle...")

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
                return False  
            elif "msg" in result and "nonce too high" in result["msg"]:
                log_kuning(f"    ⚠️ Failed to claim faucet. Nonce too high {address}")
                return False  
            elif "msg" in result and "exceeded" in result["msg"]:
                log_error(f"    ❌ Limit claim faucet for {address}. Waiting 60 seconds.")
                time.sleep(65)
                return False  
            else:
                log_error(f"    ❌ Unexpected response for {address}: {result}")
                time.sleep(60)
                return False  
        except (requests.exceptions.ProxyError, 
                requests.exceptions.ConnectTimeout, 
                requests.exceptions.ReadTimeout):
            log_error(f"    ❌ Connection issue with proxy {proxy_dict['http']}. Trying another proxy...")
            continue
        except Exception as e:
            log_error(f"    ❌ An unexpected error occurred while claiming faucet for {address}: {e}")
            time.sleep(60)
            return False  

def process_wallets(private_keys: List[str], num_transactions: int, recipient_option: int, 
                   addresses: List[str], pk_addresses_map: dict, proxies: List[str]):
    """Process wallets with retry logic for failed claims after full cycle"""
    last_tx_times = {}
    failed_claims = set()  
    successful_claims = set()  
    
    while True:  

        for current_wallet_idx, key in enumerate(private_keys):
            try:
                account = web3.eth.account.from_key(key)
            except ValueError:
                log_error(f"❌ Invalid private key at index {current_wallet_idx}")
                continue

            wallet_address = account.address
            
            if wallet_address in successful_claims:
                log_info(f"⏭️ Skipping {wallet_address} - already claimed successfully")
                continue
                
            if wallet_address in last_tx_times and last_tx_times[wallet_address] is not None:
                next_cycle_time = last_tx_times[wallet_address] + timedelta(hours=24)
                if datetime.now() < next_cycle_time:
                    log_kuning(f"💤 Wallet {wallet_address} is in cooldown period")
                    continue

            log_putih(f"💎 Processing wallet: {wallet_address} ===========")

            claim_success = claim_faucet(wallet_address, proxies)
            
            if claim_success:
                successful_claims.add(wallet_address)
                last_tx_time = process_wallet_transactions(
                    wallet_address,
                    key,
                    num_transactions,
                    recipient_option,
                    private_keys,
                    addresses,
                    current_wallet_idx,
                    pk_addresses_map,
                    proxies
                )

                if last_tx_time:
                    last_tx_times[wallet_address] = last_tx_time
                    next_cycle_time = last_tx_time + timedelta(hours=24)
                    log_info(f"⏰ Next cycle for {wallet_address} will start at: {next_cycle_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                failed_claims.add(wallet_address)
                log_error(f"❌ Failed to claim faucet for {wallet_address}, will retry later")
                continue

       
        if failed_claims:
            log_info(f"🔄 Starting retry cycle for {len(failed_claims)} failed claims...")
            retry_failed_claims = failed_claims.copy()  
            
            for wallet_address in retry_failed_claims:
                key = None
                for pk in private_keys:
                    try:
                        if web3.eth.account.from_key(pk).address == wallet_address:
                            key = pk
                            break
                    except ValueError:
                        continue
                
                if not key:
                    log_error(f"❌ Could not find private key for {wallet_address}")
                    continue
                
                log_putih(f"🔄 Retrying wallet: {wallet_address} ===========")
                
                claim_success = claim_faucet(wallet_address, proxies)
                
                if claim_success:
                    failed_claims.remove(wallet_address)
                    successful_claims.add(wallet_address)
                    
                    last_tx_time = process_wallet_transactions(
                        wallet_address,
                        key,
                        num_transactions,
                        recipient_option,
                        private_keys,
                        addresses,
                        private_keys.index(key),
                        pk_addresses_map,
                        proxies
                    )

                    if last_tx_time:
                        last_tx_times[wallet_address] = last_tx_time
                        next_cycle_time = last_tx_time + timedelta(hours=24)
                        log_info(f"⏰ Next cycle for {wallet_address} will start at: {next_cycle_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    log_error(f"❌ Retry failed for {wallet_address}, will try again in next cycle")
        
        if not failed_claims or len(successful_claims) == len(private_keys):
            log_info("📝 Completed cycle for all wallets, starting new cycle...")
            successful_claims.clear()
            failed_claims.clear()
            time.sleep(30) 

def select_recipient_option(private_keys: List[str], addresses: List[str]) -> int:
    print("\nSelect address to send:")
    print("1. Random address")
    print("2. Load from address.txt")
    print("3. Get address from next private key")
    print("4. Send to all address.txt with 1 private key")
    print("5. Send to all address.txt with all private key (skip sender's address)") 
    
    while True:
        choice = input(f"{Fore.CYAN}Enter your choice (1/2/3/4/5): {Style.RESET_ALL}")
        if choice in ['1', '2', '3', '4', '5']:
            return int(choice)
        else:
            log_error("❗ Invalid choice. Please select 1, 2, 3, 4, or 5.")

def get_recipient_address(option: int, private_keys: List[str], current_index: int, addresses: List[str], total_transactions: int, sent_count: int, pk_addresses_map: dict, current_address: str = None) -> str:
    if option == 1:
        return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])
    elif option == 2:
        return addresses[sent_count % len(addresses)]
    elif option == 3:
        next_index = (current_index + 1) % len(private_keys)
        next_pk = private_keys[next_index]
        try:
            account = web3.eth.account.from_key(next_pk)
            return account.address
        except ValueError:
            log_error(f"❌ Invalid private key at index {next_index}. Using random address instead.")
            return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])
    elif option == 4:
        pk = private_keys[0]
        if pk not in pk_addresses_map:
            pk_addresses_map[pk] = 0
        address_index = pk_addresses_map[pk] % len(addresses)
        recipient = addresses[address_index]
        pk_addresses_map[pk] += 1
        return recipient
    elif option == 5:
        valid_addresses = [addr for addr in addresses if addr.lower() != current_address.lower()]
        if not valid_addresses:
            log_error(f"❌ No valid recipient addresses found (excluding sender)")
            return None
            
        if current_address not in pk_addresses_map:
            pk_addresses_map[current_address] = 0
            
        current_index = pk_addresses_map[current_address]
        recipient = valid_addresses[current_index % len(valid_addresses)]
        pk_addresses_map[current_address] += 1
        
        return recipient
    else:
        return Web3.to_checksum_address(Web3.keccak(random.getrandbits(256).to_bytes(32, 'big'))[:20])

def print_welcome_message():
    print(Fore.WHITE + r"""
          
█▀▀ █░█ ▄▀█ █░░ █ █▄▄ █ █▀▀
█▄█ █▀█ █▀█ █▄▄ █ █▄█ █ ██▄
          """)
    print(Fore.GREEN + Style.BRIGHT + "HAUST Network Testnet Tools\n")
    print(Fore.YELLOW + Style.BRIGHT + "Join Telegram Channel: @gsc_lobby | @sirkel_testnet\n")

def process_wallet_transactions(wallet_address: str, key: str, num_transactions: int, recipient_option: int, private_keys: List[str], addresses: List[str], idx: int, pk_addresses_map: dict, proxies: List[str]) -> datetime:
    try:
        balance = web3.eth.get_balance(wallet_address)
        eth_balance = web3.from_wei(balance, 'ether')
        log_info(f"    💲 Balance : {eth_balance:.6f} HAUST")
    except Exception as e:
        log_error(f"    ❌ Failed to retrieve balance for {wallet_address}: {e}")
        return None

    if balance == 0:
        log_error(f"    💀 Wallet {wallet_address} has zero balance. Skipping...")
        return None

    try:
        nonce = web3.eth.get_transaction_count(wallet_address, 'pending')
    except Exception as e:
        log_error(f"    ❌ Failed to get nonce for {wallet_address}: {e}")
        return None

    success_count = 0
    sent_count = 0
    last_tx_time = None

    for i in range(num_transactions):
        recipient = get_recipient_address(
            recipient_option, 
            private_keys, 
            idx, 
            addresses, 
            num_transactions, 
            sent_count, 
            pk_addresses_map,
            wallet_address  
        )
        
        if recipient is None:
            log_error(f"    ❌ Could not find valid recipient address. Skipping transaction.")
            continue
            
        sent_count += 1

        amount = random.uniform(0.0001, 0.0010)
        gas_price = web3.eth.gas_price + web3.to_wei(1, 'gwei')

        tx = {
            'chainId': 1570754601,
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
                log_kuning(f"    💀 Insufficient Balance HAUST")
                break

            tx['gas'] = gas_limit
            signed_tx = web3.eth.account.sign_transaction(tx, key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            log_info(f"    🎁 Transaction {i+1} Sending {amount:.4f} HAUST to {recipient}...")

            try:
                tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if tx_receipt.status == 1:
                    success_count += 1
                    last_tx_time = datetime.now()
                    log_success(f"    🚀 Transaction {i+1} successful with hash: {tx_hash.hex()}")
                else:
                    log_error(f"    ❌ Transaction {i+1} failed.")
            except Exception as e:
                log_error(f"    ❌ Failed to get receipt for transaction {i+1}: {e}")

            nonce += 1
            balance -= total_cost
            delay(1)

        except ValueError as e:
            if 'replacement transaction underpriced' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                tx['gasPrice'] = gas_price
                try:
                    signed_tx = web3.eth.account.sign_transaction(tx, key)
                    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    log_success(f"    ⚠️ Retried transaction {i+1} successful with hash: {tx_hash.hex()}")
                    nonce += 1
                    success_count += 1
                    last_tx_time = datetime.now()
                except Exception as retry_e:
                    log_error(f"    ❌ Retry failed for transaction {i+1}: {retry_e}")
            elif 'insufficient funds for transfer' in str(e):
                log_error(f"    💀 Insufficient Balance")
                break
            else:
                log_error(f"    ❌ Transaction {i+1} error: {e}")
        except Exception as e:
            log_error(f"    ❌ Unexpected error during transaction {i+1}: {e}")
            break

    log_info(f"✨ Completed transfers from wallet {wallet_address}. Successful transactions: {success_count}/{num_transactions}")
    return last_tx_time

def transfer_eth():
    NETWORK_URL = "https://rpc-test.haust.network"
    
    global web3
    web3 = Web3(Web3.HTTPProvider(NETWORK_URL))

    if not web3.is_connected():
        log_error("❌ Failed to connect to the Haust Testnet.")
        sys.exit(1)
    else:
        log_success("🌐 Successfully connected to the Haust Testnet.")

    num_transactions = prompt_user('📊 How many transactions would you like to send per wallet (ex. 100):')
    
    private_keys = load_private_keys()
    proxies = load_proxies()
    addresses = load_addresses()
    
    recipient_option = select_recipient_option(private_keys, addresses)
    log_info(f"📁 Selected recipient option: {recipient_option}")
    
    pk_addresses_map = {}
    
    try:
        process_wallets(private_keys, num_transactions, recipient_option, 
                       addresses, pk_addresses_map, proxies)
    except KeyboardInterrupt:
        print("\n")
        log_info("👋 Script terminated by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        log_error(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)
        
def main():
    try:
        print_welcome_message()
        transfer_eth()
    except KeyboardInterrupt:
        print("\n")
        log_info("👋 Script terminated by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        log_error(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
