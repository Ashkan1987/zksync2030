import random
from hashlib import sha256
from typing import Union

from loguru import logger
from web3 import Web3
from config import DMAIL_ABI, DMAIL_CONTRACT
from utils.gas_checker import check_gas
from utils.helpers import retry
from .account import Account


class Dmail(Account):
    def __init__(self, account_id: int, private_key: str, proxy: Union[None, str]) -> None:
        super().__init__(account_id=account_id, private_key=private_key, proxy=proxy, chain="zksync")

        self.contract = self.get_contract(DMAIL_CONTRACT, DMAIL_ABI)

    async def get_tx_data(self):
        tx = {
            "chainId": await self.w3.eth.chain_id,
            "from": self.address,
            "to": Web3.to_checksum_address(DMAIL_CONTRACT),
            "gasPrice": await self.w3.eth.gas_price,
            "nonce": await self.w3.eth.get_transaction_count(self.address),
        }
        return tx

    @retry
    @check_gas
    async def send_mail(self):
        logger.info(f"[{self.account_id}][{self.address}] Send email")

        email = sha256(str(1e11 * random.random()).encode()).hexdigest()
        theme = sha256(str(1e11 * random.random()).encode()).hexdigest()

        data = self.contract.encodeABI("send_mail", args=(email, theme))

        tx_data = await self.get_tx_data()
        tx_data.update({"data": data})

        signed_txn = await self.sign(tx_data)

        txn_hash = await self.send_raw_transaction(signed_txn)

        await self.wait_until_tx_finished(txn_hash.hex())
