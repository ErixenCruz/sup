# client.py - Periodically pings server for updates.
#
# Python 3.6.9 on Ubuntu 18.04.4 LTS
#
# Last modified 25 February 2020
# Erixen Cruz ec622@drexel.edu
import socket
from time import sleep
import commonFuncs as cf

supVer = '1.0'
port = 8492
opSys = 'linux'
prodKey = '123456799'
softVer = '1.0'

# Following tutorial from https://www.geeksforgeeks.org/socket-programming-python/

'''
while True:
    sleep(5)
'''
# idle
# Connect locally for now
s = socket.socket()
s.connect(('127.0.0.1',port))
# create the message to ping server for updates and move to "checking" state
msg = cf.encode(' '.join([prodKey,softVer,opSys,supVer]))

# in checking state now
s.send(msg)

if cf.decode(s.recv(1024)) == '0':
    print('The key is invalid!')
s.close()
