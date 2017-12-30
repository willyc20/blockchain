# -*- coding: utf-8 -*-
import merkletools

mt = merkletools.MerkleTools(hash_type="SHA256")

Txs = ['Sam get $100 by POW', 'Tim give Jimmy $100', 'Johb give Jimmy $100', 'Jimmy give Tom $100']

mt.add_leaf(Txs, True)
mt.make_tree()

print(mt.get_merkle_root())

