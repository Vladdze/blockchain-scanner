# Blockchain-Scanner
This script is designed to monitor and process transaction events from the Uniswap V2 smart contracts on the Ethereum blockchain. It connects to the blockchain using the WebSocket protocol, fetches transaction data from Etherscan, and provides detailed logs of certain transactions.

# Features
Web3 Connection: Establishes a connection to the Ethereum blockchain using the Web3.py library.

WebSocket Listener: Listens to PairCreated events from the Uniswap V2 Factory contract.

Backward Filters: Validates the transactions based on multiple conditions such as the amount of initial ETH liquidity, prior removal of liquidity, and contract verification.

Transaction History Checker: Retrieves a comprehensive list of previous transactions for the given address.

# Prerequisites

Python 3.x
Required Python libraries:

websockets, asyncio, web3, aiohttp, orjson, collections

# Setup

Install the required packages:

Python
```
pip install websockets asyncio web3 aiohttp orjson
```

Update your credentials.py with:
```
INFURA_ENDPOINT: Your Infura endpoint.
wssEndpoint: Your WebSocket endpoint.
ETHERSCAN_API_URL: Etherscan API URL.
ETHERSCAN_API_KEY: Your personal Etherscan API key.
```
Save the addresses of exchanges in a file named exchange_addrs.json.

# How to Use
To start monitoring and processing the transactions:

Python
```
python script_name.py
```
Replace script_name.py with the actual name of the script.

# Key Components

TOPIC_IDS: Contains known event topic IDs for ease of identifying Ethereum events.

get: A helper function for making GET requests.

getAdressNormalTransactionHistory: Retrieves the transaction history for an Ethereum address.

getFrom: Returns the sender address of a transaction.

ContractVerficationFilter: Checks if a contract is verified on Etherscan.

PriorRemovalOfLiquidityFilter: Ensures there hasn't been a prior removal of liquidity event.

getInitialEthLiquidity: Fetches the initial Ethereum liquidity from a transaction.

backwardsFilters: Validates transactions based on pre-defined conditions.

transactionHistoryChecker: Fetches and verifies the transaction history for an address.

getCreater: Returns the creator (first sender) of a contract.

getFirstTransaction: Fetches the first transaction for a contract.


# Ordering-Function
This script provides an interface to interact with Uniswap V2 smart contracts, enabling functionalities such as swapping tokens, approving transactions, and fetching current pool ratios.

# Functions:
swapExactEthForTokens: Allows users to swap Ethereum (ETH) for another ERC20 token.

retrieveNotEthAmount: Retrieves the amount of a given ERC20 token held by an Ethereum address.

approveContract: Approves the Uniswap V2 router to manage a user's ERC20 tokens.

swapExactTokensForEth: Allows users to swap an ERC20 token for Ethereum (ETH).

getCurrentPoolRatio: Retrieves the current ratio between two tokens in a Uniswap V2 liquidity pool.

Prerequisites:
Python 3.x

Web3.py library installed

JSON data structure for private keys

Uniswap V2 contract ABIs: erc20ABI, uniswapv2RouterABI, and pairABI.

Infura endpoint or another Ethereum provider endpoint

# Setup:
Install the required packages:
```
pip install web3 json hexbytes
```

Update the credentials.py file with your Infura endpoint (or another Ethereum provider endpoint).

Save your private key and corresponding address in a JSON structure in privateKeys/PRIVATEKEYS.txt. It should look like:
```
json
{
  "key": "YOUR_PRIVATE_KEY",
  "address": "YOUR_ETHER_ADDRESS"
}
```

Place the required ABIs in the contractABIs folder.


Note
Ensure that your Infura and Etherscan API limits are not exceeded. Always be cautious and perform due diligence when working with smart contracts and transaction data.

Disclaimer
This script is for educational and informational purposes only. Always do your own research when working with blockchain data and smart contracts. Ensure your API keys and sensitive information are kept confidential.
