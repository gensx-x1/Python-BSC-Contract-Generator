import os
from random import randint
import codecs
import ecdsa
from Crypto.Hash import keccak
from web3 import Web3, HTTPProvider
from solcx import install_solc
from solcx import compile_source
from web3.middleware import geth_poa_middleware


install_solc(version='latest')
nKeys = 115792089237316195423570985008687907852837564279074904382605163141518161494336
nodeList = open('nodeList', 'r').readlines()
for nod in nodeList:
    nodeList[nodeList.index(nod)] = nod.strip('\n')
w3 = Web3(HTTPProvider(nodeList[randint(0, len(nodeList)-1)]))
tokenTemplate = open('tokenTemplate', 'r').readlines()

# Create new wallet , save private key and public addres to file. Return address and private key
def createWallet():
    pKey = hex(randint(0, nKeys))
    if len(pKey) < 66:
        pKey = '0x'+('0'*(64-(len(pKey)-2)))+pKey[2:]
    kString = bytes.fromhex(pKey[2:])
    k = ecdsa.SigningKey.from_string(kString, curve=ecdsa.SECP256k1).verifying_key
    kBytes = k.to_string()
    publicKey = codecs.encode(kBytes, 'hex')
    hash = keccak.new(digest_bits=256)
    hash.update(kBytes)
    keccak_digest = hash.hexdigest()
    address = '0x' + keccak_digest[-40:]
    return address, pKey


# Fill source code template with data. Return formated source code
def customizeToken(tokenName, tokenSymbol, totalSupply):
    tokenTemplate[4] = tokenTemplate[4].format(tokenName)
    tokenTemplate[11] = tokenTemplate[11].format(tokenName + '{')
    tokenTemplate[12] = tokenTemplate[12].format(tokenName)
    tokenTemplate[13] = tokenTemplate[13].format(tokenSymbol)
    tokenTemplate[14] = tokenTemplate[14].format(totalSupply)
    source = ''
    for line in tokenTemplate:
        source += line
    return source


def deploy(sourceCode):
    compiledSource = compile_source(sourceCode)
    contractId, contractInterface = compiledSource.popitem()
    byteCode = contractInterface['bin']
    abi = contractInterface['abi']
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    contract = w3.eth.contract(abi=abi, bytecode=byteCode)
    transactionDict = {'chainId': 56,
                       'gas': 1000000,
                       'gasPrice': w3.toWei('5', 'gwei'),
                       'nonce': w3.eth.getTransactionCount(w3.toChecksumAddress(wallet))}
    deployHash = contract.constructor().buildTransaction(transactionDict)
    deployHash_signed = w3.eth.account.signTransaction(deployHash, private_key=pKey)
    print('Sending transaction')
    deployTXN = w3.eth.sendRawTransaction(deployHash_signed.rawTransaction)
    deployTXN_receipt = w3.eth.wait_for_transaction_receipt(deployTXN)
    if deployTXN_receipt.status == 1:
        with open('deployedContracts', 'a') as file:
            file.write(f'Contract Address:{deployTXN_receipt.contractAddress}|Create TXN: {deployTXN.hex()}')
            file.close()
        print(f'Contract deployed succesfully! Contract Address {deployTXN_receipt.contractAddress}')
    elif deployTXN_receipt.status == 0:
        print('something went wrong!')




os.system('clear')
print('Binance Smart Chain Simple Token Generator')
if os.path.isfile('wallet') is True:
    wallet = open('wallet', 'r').read().split(',')[0]
    pKey = open('wallet', 'r').read().split(',')[1].strip('\n')
    print(f'Using {wallet} wallet')
if os.path.isfile('wallet') is False:
    print('No wallet detected , creating new')
    wallet, pKey = createWallet()
    with open('wallet', 'w') as file:
        file.write(f'{wallet},{pKey}')
        file.close()
        print('wallet saved')
    print(f'Using 0x{wallet} wallet')
if w3.eth.get_balance(w3.toChecksumAddress(wallet)) < w3.toWei(0.005, 'ether'):
    print(f'Wallet balance is too low to depoloy contract, min. is 0.005 BNB')
tokenName = input('Token name?> ')
tokenSymbol = input('Token symbol?> ')
totalSupply = w3.toWei(int(input('Total supply ?> ')), 'ether')
tokenSource = customizeToken(tokenName, tokenSymbol, totalSupply)
print('\n\n')
print(f'Token name: {tokenName}\n'
      f'Token symbol: {tokenSymbol}\n'
      f'Total supply: {w3.fromWei(totalSupply,"ether")} (this amount will be minted and send to creator wallet)\n')
opt = input('Is this correct ?[yes/no] >')
if opt == 'YES' or opt == 'yes':
    deploy(tokenSource)
else:
    exit()