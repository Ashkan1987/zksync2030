import random

from loguru import logger
from web3 import Web3
from config import WOOFI_CONTRACTS, WOOFI_ROUTER_ABI, ZKSYNC_TOKENS
from .account import Account


class WooFi(Account):
    def __init__(self, private_key: str, proxy: str) -> None:
        super().__init__(private_key=private_key, proxy=proxy, chain="zksync")

        self.swap_contract = self.get_contract(WOOFI_CONTRACTS["router"], WOOFI_ROUTER_ABI)

        self.tx = {
            "from": self.address,
            "gas": random.randint(2900000, 3100000),
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.address)
        }

    def get_min_amount_out(self, from_token: str, to_token: str, amount: int, slippage: float):
        min_amount_out = self.swap_contract.functions.querySwap(
            Web3.to_checksum_address(from_token),
            Web3.to_checksum_address(to_token),
            amount
        ).call()
        return int(min_amount_out - (min_amount_out / 100 * slippage))

    def swap(
            self,
            from_token: str,
            to_token: str,
            min_amount: float,
            max_amount: float,
            decimal: int,
            slippage: int,
            all_amount: bool
    ):
        amount_wei, amount, balance = self.get_amount(from_token, min_amount, max_amount, decimal, all_amount)

        logger.info(f"[{self.address}] Swap on WooFi – {from_token} -> {to_token} | {amount} {from_token}")

        if amount_wei <= balance != 0:
            if from_token == "ETH":
                from_token_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                to_token_address = Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
                self.tx.update({"value": amount_wei})
            else:
                from_token_address = Web3.to_checksum_address(ZKSYNC_TOKENS[from_token])
                to_token_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

                self.approve(amount_wei, from_token_address, WOOFI_CONTRACTS["router"])
                self.tx.update({"nonce": self.w3.eth.get_transaction_count(self.address)})

            min_amount_out = self.get_min_amount_out(from_token_address, to_token_address, amount_wei, slippage)

            contract_txn = self.swap_contract.functions.swap(
                from_token_address,
                to_token_address,
                amount_wei,
                min_amount_out,
                self.address,
                self.address
            ).build_transaction(self.tx)

            signed_txn = self.sign(contract_txn)

            txn_hash = self.send_raw_transaction(signed_txn)

            self.wait_until_tx_finished(txn_hash.hex())
        else:
            logger.error(f"[{self.address}] Insufficient funds!")
