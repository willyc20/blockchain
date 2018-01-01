# -*- coding: utf-8 -*-
import math


def AttackerSuccessProbability(q, z):
    p = 1.0 - q
    lamb = z * (q / p)
    sum = 1.0
    for k in range(z+1):
        poisson = math.exp(-lamb)
        for i in range(1, k+1):
            poisson *= lamb / i
        sum -= poisson * (1 - math.pow(q / p, z - k))
    
    return sum

q = 0
while True:
    prob = AttackerSuccessProbability(q, 6)
    if prob > 0.3:
        break
    q += 0.01

print("攻擊者至少需掌握%.2f%%算力才能有30%%可能性攻擊成功" % q)
