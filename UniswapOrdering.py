import json
import hexbytes
from web3 import Web3
import time
import credentials


""" swapExactEthForTokens: uses the swapExactEthForTokens function from the uniswapv2RouterABI
    params:
        notEthTokenAddress (str): the token address for the asset that is not eth in the pair (i.e. for matic/weth, matic == notEthToken)
        pairAddress (str): the contract address for the actual liquidity pool of the pair (is often found with the UNI-V2 prefix on etherscan)
        walletAddress (str): the wallet address of the account wishing to use the swapExactEthForTokens function
        slippage (float): slippage in decimal (i.e. 0.003 = 0.3% slippage)
        web3Client: web3Client used for web3 methods
        uniswapv2RouterAddress: router address of the uniswapv2 router
        uniswapv2RouterABI: abi needed to create the web3.contract object 
        pairABI: simple ABI that allows for erc20 data querying (i.e. getReserves for slippage calculations)
        privateKey: private key of the wallet making the transaction, used to sign the transaction.
"""
def swapExactEthForTokens(notEthTokenAddress, pairAddress, ethAmountToSwap, walletAddress, slippage, web3Client, uniswapv2RouterAddress, uniswapv2RouterABI, pairABI,privateKey):

    # NOTE: WEB3 REQUIRES THESE TO BE CHECKSUM ADDRESSES, NOT NECESSARY WITH OUT LANGUAGES, BUT YOU GET ERRORS IF THEY ARE NOT INCLUDED

    walletAddress = web3Client.toChecksumAddress(walletAddress)
    notEthTokenAddress = web3Client.toChecksumAddress(notEthTokenAddress)
    if notEthTokenAddress != None:
        tokenToBuy = web3Client.toChecksumAddress(notEthTokenAddress)
        ethToSpend = web3Client.toChecksumAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")  # WETH
        
        # UNISWAP ROUTER CONTRACT INITIALIZATION

        uniContract = web3Client.eth.contract(address=web3Client.toChecksumAddress(uniswapv2RouterAddress),abi=uniswapv2RouterABI)

        # ONE TIME CODE FOR TRANSACTIONS

        nonce = web3Client.eth.get_transaction_count(walletAddress)
        start = int(time.time())
        
        # PAIR CONTRACT INITILIZATION, USED TO CALCULATE RESERVES AND GET CURRENT RATIO OF POOL TO CALCULCATE EXPECTED AMOUNT OF TOKENS PER SWAPEXACTETHFORTOKENS FUNC.

        pairContract = web3Client.eth.contract(address=web3Client.toChecksumAddress(pairAddress), abi=pairABI)
        
        # CURRENT RESERVES OF THE LIQUIDITY POOL

        getReserves = pairContract.functions.getReserves().call()

        #CHECK IF TOKEN0 == WETH, IF IT IS > MAKE SURE TO SPECIFY TOKEN0 AS PEGGED ASSET. (FOR EXAMPLE, NOTETH/WETH FOR GETRESERVES FUNC)

        isReversed = pairContract.functions.token0().call() == ethToSpend
        if isReversed:
            ethReserve = getReserves[0]
            notEthReserve = getReserves[1]
        else:
            ethReserve = getReserves[1]
            notEthReserve = getReserves[0]
        
        # UNISWAP ROUTER ABI TO CALCULATE EXPECTED AMOUNT OF NOTETHTOKEN TO RECEIVE GIVEN X AMOUNT OF ETH

        notEthAmountOut = uniContract.functions.getAmountOut(web3Client.toWei(ethAmountToSwap, 'ether'), ethReserve, notEthReserve).call()

        # CALCULATE MINIMUM AMOUNT OUT, IF SLIPPAGE TOLERANCE IS INCURRED.
        minTokenAmountOut = int(notEthAmountOut * (1-slippage))
        
        # ESTIMATE GAS FEES
        gasEstimate = uniContract.functions.swapExactETHForTokens(
            minTokenAmountOut, 
            [ethToSpend, tokenToBuy],
            walletAddress,
            (start + 150)
        ).estimateGas({'from':walletAddress, 'value': hex(web3Client.toWei(ethAmountToSwap, 'ether'))})
        
        # CONSTRUCT TRANSACTION USING THE INFORMATION CALCULATED AND NECESSARY SWAPEXACTETHFORTOKENS PARAMS.

        transaction = uniContract.functions.swapExactETHForTokens(
            minTokenAmountOut,
            [ethToSpend, tokenToBuy],
            walletAddress,
            (start + 150)).buildTransaction({
            'from': walletAddress,
            'value': 0,
            'gas': hex(gasEstimate), 
            'gasPrice': hex(web3Client.eth.gas_price),
            'nonce': nonce,
        })
        
        # SIGN TRANSACTION WITH PRIVATE KEY

        signedTransaction = web3Client.eth.account.sign_transaction(transaction, privateKey)

        # SEND SIGNED TRANSACTION, AND LOG THE TRANSACTION TOKEN

        transactionToken = web3Client.eth.send_raw_transaction(signedTransaction.rawTransaction) 
        
        # TRANSACTIONTOKEN INITIALY IN BYTE ARRAY (IIRC) > CONVERT TO HEX TO GET READABLE TRANSACTION HASH.

        transactionHash = '0x'+transactionToken.hex()

    return transactionHash

# CHECK BALANCE OF NOTETHTOKEN RECEIVED FROM SWAPPING ETH > NOTETHTOKEN. THIS IS USED WHEN WE SWAP TOKEN BACK TO ETH.

def retrieveNotEthAmount(tokenAddress, walletAddress, web3Client, erc20ABI):

    erc20Contract = web3Client.eth.contract(web3Client.toChecksumAddress(tokenAddress), abi=erc20ABI)
    currentBalance = erc20Contract.functions.balanceOf(web3Client.toChecksumAddress(walletAddress)).call()
    return currentBalance

# FUNCTION TO APPROVE ROUTER TO TRADE NOTETHTOKEN FOR US. PARAMS ARE SAME AS UNISWAPROUTER FUNC.

def approveContract(notEthAddress, walletAddress, web3Client, uniswapv2RouterAddress, pairABI, erc20ABI, privateKey):

    walletAddress = web3Client.toChecksumAddress(walletAddress)
    uniswapv2RouterAddress = web3Client.toChecksumAddress(uniswapv2RouterAddress)
    if notEthAddress != None:
        notEthAddress = web3Client.toChecksumAddress(notEthAddress)
        notEthERC20Contract = web3Client.eth.contract(address=notEthAddress, abi=erc20ABI)
        notEthTotalSupply = int(notEthERC20Contract.functions.totalSupply().call())

        notEthContract = web3Client.eth.contract(address=notEthAddress, abi=pairABI)
        nonce = web3Client.eth.get_transaction_count(walletAddress)

        gasEstimate = notEthContract.functions.approve(uniswapv2RouterAddress, notEthTotalSupply).estimateGas({'from':walletAddress,'nonce':nonce})

        approvalTransaction = notEthContract.functions.approve(uniswapv2RouterAddress, notEthTotalSupply).buildTransaction({
            'from':walletAddress,
            'value':0,
            'gas':hex(gasEstimate),
            'gasPrice':hex(web3Client.eth.gas_price),
            'nonce':nonce
        })

        signedTransaction = web3Client.eth.account.sign_transaction(approvalTransaction, privateKey)
        transactionToken = web3Client.eth.send_raw_transaction(signedTransaction.rawTransaction) 

        transactionHash = '0x'+transactionToken.hex()

    return transactionHash
    
# INVERSE FUNCTION OF SWAPEXACTETHFORTOKENS. FUNCTIONALITY IS IDENTICAL, EXCEPT NOW IT IS NOTETHTOKEN > ETH.

def swapExactTokensForEth(notEthTokenAddress, pairAddress, walletAddress,slippage, web3Client, erc20ABI, uniswapv2RouterAddress, uniswapv2RouterABI, privateKey):

    walletAddress = web3Client.toChecksumAddress(walletAddress)
    if notEthTokenAddress != None:
        tokenToSell = web3Client.toChecksumAddress(notEthTokenAddress)
        ethToReceive = web3Client.toChecksumAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")  # weth
        uniContract = web3Client.eth.contract(address=web3Client.toChecksumAddress(uniswapv2RouterAddress),abi=uniswapv2RouterABI)
        nonce = web3Client.eth.get_transaction_count(walletAddress)
        start = int(time.time())
        
        pairContract = web3Client.eth.contract(address=web3Client.toChecksumAddress(pairAddress), abi=pairABI)

        getReserves = pairContract.functions.getReserves().call()

        # CHECK IF TOKEN0 == WETH, IF IT IS, SPECIFY TOKEN0 NEEDS TO BE PEGGED ASSET.

        isReversed = pairContract.functions.token0().call() == ethToReceive
        if isReversed:
            ethReserve = getReserves[0]
            notEthReserve = getReserves[1]
        else:
            ethReserve = getReserves[1]
            notEthReserve = getReserves[0]

        exactNotEthTokenAmount = retrieveNotEthAmount(tokenAddress=notEthTokenAddress,
                                                      walletAddress=walletAddress,
                                                      web3Client=web3Client,
                                                      erc20ABI=erc20ABI)

        maxEthAmountOut = uniContract.functions.getAmountOut(exactNotEthTokenAmount, notEthReserve, ethReserve).call()
        minEthAmountOut = int(maxEthAmountOut * (1-slippage))
        
        gasEstimate = uniContract.functions.swapExactTokensForETH(
            int(exactNotEthTokenAmount),
            minEthAmountOut, 
            [tokenToSell, ethToReceive],
            walletAddress,
            (start + 150)
        ).estimateGas({'from':walletAddress, 'value':0, 'nonce':nonce})
        
        transaction = uniContract.functions.swapExactTokensForETH(
            exactNotEthTokenAmount, # CALCULATED FROM WALLET BALANCE
            minEthAmountOut,
            [tokenToSell, ethToReceive],
            walletAddress,
            (start + 150)
        ).buildTransaction({
            'from': walletAddress,
            'value':0,
            'gas': hex(gasEstimate), 
            'gasPrice': hex(web3Client.eth.gas_price),
            'nonce': nonce,
        })

        signed_txn = web3Client.eth.account.sign_transaction(transaction, privateKey)
        transactionToken = web3Client.eth.send_raw_transaction(signed_txn.rawTransaction) 

        transactionHash = '0x'+transactionToken.hex()

    return transactionHash


# STANDALONE FUNCTION: GET RATIO OF NOTETH / ETH. NOT IMPLEMENTED, POTENTIALLY USEFULL IN THE FUTURE.
def getCurrentPoolRatio(notEthTokenAddress, pairAddress, web3Client, erc20ABI):
    
    notEthTokenAddress = web3Client.toChecksumAddress(notEthTokenAddress)
    pairAddress = web3Client.toChecksumAddress(pairAddress)
    
    notEthContract = web3Client.eth.contract(address=notEthTokenAddress, abi=erc20ABI)
    ethContract = web3Client.eth.contract(address=web3Client.toChecksumAddress('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'), abi=erc20ABI)

    ethDecimals = 18
    notEthDecimals = notEthContract.functions.decimals().call()
    
    notEthAmountInPool = notEthContract.functions.balanceOf(pairAddress).call() 
    ethAmountInPool = ethContract.functions.balanceOf(pairAddress).call() 

    notEthAmountInPool = notEthContract.functions.balanceOf(pairAddress).call() / (10**(notEthDecimals-1))
    ethAmountInPool = ethContract.functions.balanceOf(pairAddress).call() / (10**(ethDecimals-1))

    ratio = notEthAmountInPool / ethAmountInPool

    return ratio

if __name__ == '__main__':

    mainnetEndpoint = credentials.INFURA_ENDPOINT
    web3Client = Web3(Web3.HTTPProvider(mainnetEndpoint))

    # LOADING APIS, ROUTER ADDRESSES, PRIVATEKEYS ALL INTO MEMORY

    with open('contractABIs/erc20ABI.json') as f:
        erc20ABI = json.loads(f.read())

    with open('contractABIs/uniswapv2RouterABI.json') as f:
        uniswapv2RouterABI = json.loads(f.read())

    with open('contractABIs/pairABI.json') as f:
        pairABI = json.loads(f.read())

    # PRIVATE KEYS IN JSON STRUCTURED AS {'KEY': PRIVATE KEY HERE, 'ADDRESS': COPY ACCOUNT ADDRESS HERE}
    with open('privateKeys/PRIVATEKEYS.txt') as f:
        fileData = json.loads(f.read())   
        privateKey = fileData['key']
        walletAddress = fileData['address']