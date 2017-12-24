# -*- coding: utf-8 -*-
import ecdsa
import time
import copy
import hashlib
import random
import threading

# 小明
owner1_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner1_vk = owner1_sk.get_verifying_key()

# 區塊鏈的第一個區塊在術語中叫做創世區塊(Genesis block)
# 一開始就要有了 不然後面加進來的區塊沒東西連
Genesis_block = {
    'prev_Hash': '', # 明天才用到 先放著
    'nonce': '', # 明天才用到 先放著
    'timestamp': int(time.time()), # 區塊的產生時間，使用uinx timestamp，精確到秒
    'Txs': [ # 一個block裡面會有很多個transaction紀錄
        # 假設一筆transaction
        # 有個叫小明的一開始有1000萬
        {  
            'owner_vk': owner1_vk, # 小明的公鑰
            'preowner_vk': '先假設整個網路都認可',
            'data': '放了1000萬',
            'signature': '先假設整個網路都認可'
        }
    ] 
}

# 假設網路上有100個節點好了
# 先模擬一下
nodes = []
blockchain = [Genesis_block]
for i in range(100):
    nodes.append(copy.copy(blockchain))

# 將區塊昭告天下
def broadcast(new_block):

    # trace block看裡面的transaction跟前面的能不能對上
    # 不過後面的章節才會講到實際的transaction中的內容
    # 我們先假設一個transaction的內容只能跟之後的交易一次
    # 第i個node的第j的區塊的第k個transaction
    for i in range(len(nodes)):

        # 先確定區塊的合法性
        # 才能確定區塊是不是算力大的一方來的
        if new_block['timestamp'] < blockchain[-1]['timestamp']:
            print("node %d:區塊不合法，應按照時間生成" % i)
            continue

        if new_block['pre_Hash'] != hashlib.sha256(str(blockchain[-1])).hexdigest():
            print("node %d:區塊不合法，前一個hash值對不起來" % i)
            continue

        if hashlib.sha256(str(new_block)).hexdigest()[0:4] != '0000':
            print("node %d:區塊不合法，hash值不符合proof of work的規定" % i)
            continue

        check_legel = True
        for j in range(len(nodes[i])):
            for k in range(len(nodes[i][j]['Txs'])):
                for l in range(len(new_block['Txs'])):
                    if nodes[i][j]['Txs'][k]['preowner_vk'] == new_block['Txs'][l]['preowner_vk']:
                        check_legel = False
        if check_legel == True:
            nodes[i].append(new_block)
            print("node %d:紀錄了新block中的所有交易" % i)
        else:
            print("node %d:抱歉，這筆交易不合規定，不能重複交易" % i)

# try到適合的Nonce來讓該區塊合法
def proof_of_work(blockchain, block):

    # 區塊的產生時間應該按照順序
    if block['timestamp'] < blockchain[-1]['timestamp']:
        print('區塊不合法')
        return None

    block['pre_Hash'] = hashlib.sha256(str(blockchain[-1])).hexdigest()
    # 這裡都當作required zero有32bit
    # required zero只是論文中為了說明概念使用
    # 真正的難度在現實應用中會根據前一個block的計算時間之類的動態調整
    # 實際應用上是要讓hsah小於某個值才算合法 不然真的都用required zero難度只能一次調2的次方
    while True:
        block['nonce'] = random.randint(-214783648, 2147483647)
        if hashlib.sha256(str(block)).hexdigest()[0:4] == '0000':
            print(hashlib.sha256(str(block)).hexdigest())
            print('計算合法區塊成功')
            return block

# 將交易加入區塊中
def add_tran(tran, block = None):
    if block == None:
        block = {
            'prev_Hash': None,
            'nonce': None,
            'timestamp': int(time.time()), 
            'Txs': []
    }
    block['Txs'].append(tran)
    return block

# 談好一筆交易了
def trade(pre_tran, data, pre_sk, now_vk):
    
    transaction = {
        'owner_vk': now_vk,
        'preowner_vk': pre_tran['owner_vk'],
        'data': data,
        'signature': pre_sk.sign(str(pre_tran) + now_vk.to_pem())
    }      

    # 交易談好了
    # 現在確認上一個transaction的擁有者有沒有偷改他以前的交易內容
    try:
        pre_tran['owner_vk'].verify(transaction['signature'], str(pre_tran) + now_vk.to_pem())
        return transaction
    except:
        print('有騙子?!')
        

# 小華
owner2_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner2_vk = owner2_sk.get_verifying_key()

transaction2 = trade(blockchain[0]['Txs'][0], '1000萬拿去收好', owner1_sk, owner2_vk)
block1 = add_tran(transaction2)


# 小明黨羽(也可能是小明自導自演)
owner_other_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner_other_vk = owner_other_sk.get_verifying_key()

transaction_other = trade(blockchain[0]['Txs'][0], '同一個1000萬拿去收好', owner1_sk, owner_other_vk)
block1_other = add_tran(transaction_other)

lock = threading.Lock()
done = False
def thread_pow(block_unpow):
    global done
    block_pow = proof_of_work(blockchain, copy.copy(block_unpow))
    if block_pow != None:
        lock.acquire()
        # 為了簡化流程
        # 這裡有人開始廣播就了其他算完的執行緒就停了
        if done != True:          
            done = True
            broadcast(block_pow)
        lock.release()


threads = []
for i in range(9):
    threads.append(threading.Thread(target=thread_pow, args = (block1,)))
    
threads.append(threading.Thread(target=thread_pow, args = (block1_other,)))
    
for t in threads:
    t.start()

time.sleep(10)

print(owner2_vk.to_pem())
'''
-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEbDNA4hzQN7iTbnHXvXaHsAxBk9AAOgfd
5j5/KF7dwVK7NsaMSLl1V7EYPWSvGr2P84pGT6UNFTYSLVKodeI+KA==
-----END PUBLIC KEY-----

'''

print(owner_other_vk.to_pem())
'''
-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEVM203oPz+Gab6jsWrMCQGTM1947TUY/1
xbYOdu79LsWlgVeJynwgWsIznEL0NokC5iDqJA9wWouFnZISSoLeVw==
-----END PUBLIC KEY-----

'''

print(nodes[0][-1]['Txs'][0]['owner_vk'].to_pem())
'''
假設執行緒數量對應算力成立的話
的確算力多的那一方決定哪個區塊被塞入區塊鏈
-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEbDNA4hzQN7iTbnHXvXaHsAxBk9AAOgfd
5j5/KF7dwVK7NsaMSLl1V7EYPWSvGr2P84pGT6UNFTYSLVKodeI+KA==
-----END PUBLIC KEY-----


'''

