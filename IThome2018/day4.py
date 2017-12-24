# -*- coding: utf-8 -*-
import ecdsa

'''
這裡用個簡單的結構當作一個transaction

transaction = {
    'owner_vk': # 該transaction擁有者的公鑰
    'data': # 先隨便放資料當作交易內容
    'signature': # 數位簽章
}

'''

owner0_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner1_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner1_vk = owner1_sk.get_verifying_key()
owner2_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner2_vk = owner2_sk.get_verifying_key()
owner_other_sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
owner_other_vk = owner_other_sk.get_verifying_key()

# 第一個transaction
transaction1 = {
    'owner_vk': owner1_vk,
    'data': '隨便，先當作owner0給了owner1 1000萬，重點在於他是不是上個owner同意後簽名的內容',
    'signature': owner0_sk.sign('假設中的transaction0' + owner1_vk.to_pem())
}


# 上一個transaction的擁有者同意交易的內容後簽章證明
# 因為當前owner的公鑰也在裡面
# 所以當前owner要基於這次的交易結果去跟別人進行下一次交易的時候
# 就可以證明這個transaction是他的
#
def trade(pre_tran, data, pre_sk, now_vk):
    
    transaction = {
        'owner_vk': now_vk,
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

        
# owner1 跟 owner2 談好交易了
# 也確認owner1之前的transaction是他的也沒被竄改     
transaction2 = trade(transaction1, '1000萬拿去收好', owner1_sk, owner2_vk)

# owner1 把給同一筆交易內容也拿去給別人做新交易 騙子！！！！
transaction_other = trade(transaction1, '同一個1000萬拿去收好', owner1_sk, owner_other_vk)

