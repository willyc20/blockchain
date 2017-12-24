# -*- coding: utf-8 -*-
import ecdsa
import time
import copy

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
            print("node %d:抱歉，這筆交易有人先做了，不能重複交易" % i)

# 將交易加入區塊中
def add_tran(tran, block = None):
    if block == None:
        block = {
            'prev_Hash': '', # 明天才用到 先放著
            'nonce': '', # 明天才用到 先放著
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
        

# 延續上面的python code來演示操作

# 小華
owner2_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner2_vk = owner2_sk.get_verifying_key()

transaction2 = trade(blockchain[0]['Txs'][0], '1000萬拿去收好', owner1_sk, owner2_vk)

# 小明黨羽(也可能是小明自導自演)
owner_other_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner_other_vk = owner_other_sk.get_verifying_key()

transaction_other = trade(blockchain[0]['Txs'][0], '同一個1000萬拿去收好', owner1_sk, owner_other_vk)


# 小明黨羽的交易被加入某個區塊並廣播了
block1_other = add_tran(transaction_other)
broadcast(block1_other)
'''
node 0:紀錄了新block中的所有交易
node 1:紀錄了新block中的所有交易
node 2:紀錄了新block中的所有交易
node 3:紀錄了新block中的所有交易
node 4:紀錄了新block中的所有交易
....
'''

# 小華的交易被加入某個區塊並廣播了
# 假設這隻程式是循序執行的
# 小華晚了一步 不過也只是交易沒成功罷了
# 嚴格說起來也沒有損失
block1 = add_tran(transaction2)
broadcast(block1)
'''
node 0:抱歉，這筆交易有人先做了，不能重複交易
node 1:抱歉，這筆交易有人先做了，不能重複交易
node 2:抱歉，這筆交易有人先做了，不能重複交易
node 3:抱歉，這筆交易有人先做了，不能重複交易
node 4:抱歉，這筆交易有人先做了，不能重複交易
....
'''


