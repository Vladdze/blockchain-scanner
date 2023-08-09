import websockets
import asyncio
from web3 import Web3, HTTPProvider
import json
import aiohttp
import orjson
import collections
import credentials

web3Client = Web3(HTTPProvider(credentials.INFURA_ENDPOINT))

TOPIC_IDS = {
    '0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9': 'PairCreated',
    '0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118': 'PoolCreated',
    '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef': 'Transfer',
    '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1': 'Sync',
    '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c': 'Deposit',
    '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925': 'Approval'
}

async def get(url,params):
    async with aiohttp.ClientSession(json_serialize=orjson.dumps) as session:
        async with session.get(url,params=params) as resp:
            data = await resp.json(loads=orjson.loads)
            return data

async def getAdressNormalTransactionHistory(createrAddr,startingBlock,endingBlock,exchAddrs,url,key):


    params={
        'module':'account',
        'action':'txlist',
        'address': createrAddr,
        'startblock':startingBlock,
        'endblock': endingBlock,
        'page':1,
        'offset':10000,
        'sort':'desc',
        'apikey':key
    }

    data=await get(url=url,params=params)

    InitialCreationTransactionList = []

    if data is not None and 'result' in data:
        for i in data['result']:
            if len(i['input']) == 2:
                if i['from'] in exchAddrs:
                    method = "Transfer from " + exchAddrs[i['from']]
                else:
                    method = "Transfer from wallet"
                transactionDict = {
                    'method': method,
                    'block': i['blockNumber'],
                }
            else:
                mID = i['input'][:10]
                method = TOPIC_IDS.get(mID, mID)
                transactionDict = {
                    'method': method,
                    'block': i['blockNumber'],
                }
            InitialCreationTransactionList.append(transactionDict)

    return InitialCreationTransactionList

async def getFrom(transactionHash,web3Client):
    hHash=web3Client.eth.get_transaction_receipt(transactionHash)
    return hHash['from']

async def ContractVerficationFilter(contractAddr,url,key):
    params={
        'module':'contract',
        'action':'getabi',
        'address':contractAddr,
        'apikey':key
    }
    verfC= await get(url,params)
    return verfC['status'] == '1'

async def PriorRemovalOfLiquidityFilter(transactionArray):
    counter=collections.Counter(transactionArray)
    return not counter.get('removeLiquidity', 0)

async def getInitialEthLiquidity(transactionHash, web3Client):
    transactionLogs = web3Client.eth.get_transaction_receipt(transactionHash)['logs']
    for e in transactionLogs:
        if TOPIC_IDS.get(e['topics'][0].hex(), '') =='Deposit':
            try:
                data_bytes = e['data'] 
                data_hex = data_bytes.lstrip(b'\x00').hex()  # Strip leading zeroes and convert to hexadecimal
                return int(data_hex, 16)/1e18
            except ValueError:
                return 0
    return 0

async def backwardsFilters(createrAddr,contractAddr,startingBlock,endingBlock,InitialEthLiquidity,exchAddrs,url,key):
    transactionListOfDicts=await getAdressNormalTransactionHistory(
        createrAddr,startingBlock,endingBlock,exchAddrs,url,key)
    
    transactionArray=[e['method']for e in transactionListOfDicts]
    priorRemovalOfLiquidity=await PriorRemovalOfLiquidityFilter(transactionArray=transactionArray)
    ContractVerification=await ContractVerficationFilter(contractAddr,url,key)

    filterResults = sum([
        InitialEthLiquidity > 5,
        priorRemovalOfLiquidity,
        ContractVerification
    ])
    
    if filterResults == 3:
        return transactionListOfDicts

    return []

async def transactionHistoryChecker(createrAddr,contractAddr,transactionHash,web3Client,url,key,startingBlock=0,endingBlock=99999999):
    InitialEthLiquidity= await getInitialEthLiquidity(transactionHash,web3Client)
    exchAddrs={await getFrom(transactionHash,web3Client):'exchange'}
    filterResults= await backwardsFilters(
        createrAddr,contractAddr,startingBlock,endingBlock,InitialEthLiquidity,exchAddrs,url,key)
    
    return filterResults

async def getCreater(contractAddr, url, key):
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': contractAddr,
        'sort': 'asc',
        'page': 1,
        'offset': 1,
        'apikey': key
    }
    
    data = await get(url=url, params=params)
    
    # ASSUMING CREATOR IS THE SENDER OF THE FIRST TRANSACTION

    if data['result']:
        return data['result'][0]['from']
    else:
        return None

async def getFirstTransaction(contractAddr, url, key):
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': contractAddr,
        'sort': 'asc',
        'page': 1,
        'offset': 1,
        'apikey': key
    }
    
    data = await get(url=url, params=params)
    
    # RETURN FIRST TRX HASH
    if data['result']:
        return data['result'][0]['hash']
    else:
        return None

async def main():
    wssEndpoint = credentials.wssEndpoint
    url = credentials.ETHERSCAN_API_URL
    key = credentials.ETHERSCAN_API_KEY

    UniswapV2FactoryPairCreated= json.dumps(
        {
            "jsonrpc":"2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["logs",
            {"topics":['0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9']}
            ]
        }
    )
    
    async with websockets.connect(wssEndpoint) as websocket:
        with open('exchange_addrs.json') as f:
            exchAddrs = json.loads(f.read())
        payload = UniswapV2FactoryPairCreated
        await websocket.send(payload)

        while True:
            pkg = json.loads(await websocket.recv())
            try:
                Block = pkg['params']['result']['blockNumber']
                createrAddr = await getFrom(pkg['params']['result']['transactionHash'], web3Client)
                contractAddr = '0x' + pkg['params']['result']['data'][26:66]

                transactionHash = pkg['params']['result']['transactionHash']
                print('transactionHash:', transactionHash)

                InitialEthLiquidity = await getInitialEthLiquidity(transactionHash, web3Client)

                if InitialEthLiquidity == 0:
                    print('PairCreated, but no Liquidity Addition Event.')
                else:
                    print('Initial ETH Liquidity:', InitialEthLiquidity, '\n')
                    topics = pkg['params']['result']['topics']
                    topic1 = '0x' + topics[1][26:]
                    topic2 = '0x' + topics[2][26:]

                    if topic1 == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':  # WETH ADDRS
                        tokenAddr = topic2
                    else:
                        tokenAddr = topic1

                    print('Block:', int(Block, 16))
                    print('Token Address:', tokenAddr)
                    print('Contract Address:', contractAddr)
                    print('Contract Creator:', createrAddr)

                    await backwardsFilters(
                        createrAddr=createrAddr,
                        contractAddr=contractAddr,
                        startingBlock=0,
                        endingBlock=int(Block, 16),
                        InitialEthLiquidity=InitialEthLiquidity,
                        exchAddrs=exchAddrs,
                        url=url,
                        key=key)
            except Exception as error:
                print(error)
                pass

if __name__ == "__main__":
    asyncio.run(main())