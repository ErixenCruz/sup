# server.py - Listens to and responds to update requests.
#
# Python 3.6.9 on Ubuntu 18.04.4 LTS
#
# Last modified 25 February 2020
# Erixen Cruz ec622@drexel.edu
import socket
import commonFuncs as cf
port = 8492

validKeys=['123456789']

# Following tutorial from https://www.geeksforgeeks.org/socket-programming-python/

s=socket.socket()
s.bind(('',port))
s.listen(5)

while True:
    client, addr = s.accept()
    prodKey, softVer, opSys, supVer = cf.decode(client.recv(1024)).split(' ')
    if prodKey not in validKeys:
        client.send(cf.encode('0'))
        client.close()
    else:
        print("The key is valid!")
    #client.send(b'Your mom.')
    client.close()
