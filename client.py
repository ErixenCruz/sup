# client.py - Periodically pings server for updates.
#
# Python 3.6.9 on Ubuntu 18.04.4 LTS
#
# Last modified 13 March 2020
# Erixen Cruz ec622@drexel.edu
# CS 544 Professor Michael Kain
import socket
import ssl
from time import sleep
import commonFuncs as cf
from shutil import disk_usage
import argparse

supVer = '1.0'
port = 8492
bogusKey = '123' # for testing
buffMax = 4096 # maximum message size in bytes

''' Hard coded user input used for testing and debugging
opSys = 'linux'
prodKey = '123456789'
softVer = '1.0'
servIP = '127.0.0.1'
'''
# Command line interface
parser = argparse.ArgumentParser(description='Client for software update protocol.')
parser.add_argument('prodKey', metavar = 'prodKey',type = str,help = \
        'Valid product key for the software you want to update')
parser.add_argument('opSys', metavar='opSys',type=str, help=\
        'Your operating system (linux, windows, or mac)')
parser.add_argument('softVer', metavar = 'softVer', type =str, help=\
        'Current software version of the software you want to update')
parser.add_argument('servIP',metavar='servIP',type=str,help = \
        'IP address of the update server.')
parser.add_argument('-recover',action='store_true',help = \
        'Recover download from the last checkpoint.')
args = parser.parse_args()
opSys = args.opSys
prodKey = args.prodKey
softVer = args.softVer
servIP = args.servIP
recover = args.recover

# Following tutorial from https://www.geeksforgeeks.org/socket-programming-python/

state = 'idle'
try:
# put in try block to make sure the socket is closed no matter what
    s = socket.socket()
    with ssl.wrap_socket(s,ca_certs="server.crt",cert_reqs=ssl.CERT_REQUIRED) as s:
        s.connect((servIP,port))
        if recover:
        # Recover from last checkpoint.
            # Get the last checkpoint number saved
            with open('updateCheckpointNumber.txt','r') as f:
                checkpoint = f.read()
            # create and send checkpoint recovery message
            msg = cf.encode(' '.join([prodKey,checkpoint,supVer]))
            s.send(msg)
            state = 'updating'
        else:
            # create the message to ping server for updates and move to "checking" state
            msg = cf.encode(' '.join([prodKey,softVer,opSys,supVer])+cf.crlf) 
            #msg = cf.encode(' '.join([bogusKey,softVer,opSys,supVer])) 
            state = 'checking'

            s.send(msg)
        if state=='checking':
            checkReply = cf.decode(s.recv(1024))
            if checkReply =='': # Connection closed by server, no updates
                s.close()
            elif checkReply.strip() == '0': # invalid product key
                print('The key is invalid!')
                state='idle'
            else: # move to space check
                servSupVer,upSize = checkReply.split(' ')
                state = 'space check'
                # find free space
                _,_,freeSpace = disk_usage('/')
                freeSpace /= 10.**6. # convert to megabytes
                #freeSpace=0.
                if freeSpace<float(upSize): # not enough disk space for update
                    msg = s.send(cf.encode(' '.join([prodKey,'0'])))
                    state = 'idle'
                else:
                    #print('We have the space for the update.')
                    msg = s.send(cf.encode(' '.join([prodKey,'1'])))
                    state = 'updating'

        if state == 'updating':
            try: # catch a keyboard interrupt to initiate pausing
                updateMsg = s.recv(buffMax)
                while cf.decode(updateMsg) != 'update done'+cf.crlf:
                # continue accepting chunks until update termination
                    #print(updateMsg)
                    checkpoint,upChunk = updateMsg[:1],updateMsg[1:]
                    checkpoint=str(int.from_bytes(checkpoint,byteorder='big'))
                    with open('updateCheckpointNumber.txt','w') as f:
                    # save the checkpoint we are at
                        f.write(checkpoint)
                    with open('update.exe','ab') as f:
                    # Add the chunk to the update file
                        #print('Writing '+str(upChunk)+' to file,')
                        f.write(upChunk)
                    # Chunk receipt ack
                    s.send(updateMsg[:1]+b'\x01')
                    updateMsg=s.recv(buffMax)
                    sleep(1)
                        
            except KeyboardInterrupt: # user wants to pause download
                #s.send(cf.encode(' '.join([prodKey,'pause'])))
                # send pause message
                s.send(updateMsg[:1]+b'\x00')
                state = 'idle'
                s.close()
                exit()
            state = 'update termination'
            s.send(cf.encode(' '.join([prodKey,'update done'])))
            s.close()
            state = 'idle'
finally:
    s.close()
