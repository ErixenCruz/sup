# server.py - Listens to and responds to update requests.
#
# Python 3.6.9 on Ubuntu 18.04.4 LTS
#
# Last modified 13 March 2020
# Erixen Cruz ec622@drexel.edu
# CS 544 Professor Michael Kain
import socket
import ssl
#https://carlo-hamalainen.net/2013/01/24/python-ssl-socket-echo-test-with-self-signed-certificate/
import commonFuncs as cf
from os.path import getsize,exists,join
import json
from glob import glob
import multiprocessing as mp

port = 8492
maxField = 12
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

validKeys=['123456789','123456799']
updateInfoFile = 'updateInfo.txt' # software versions and update executable
                                  # locations.

OSs=['windows','linux','mac']
supVers = ['1.0']
supVer = supVers[0]
# clientRecords = {} 
clientRecords = mp.Manager().dict() # So that all processes can read and write
                                    #  to the dictionary.

def handleClient(client,clientRecords=clientRecords):
    '''
    handleClient takes a socket from a client that initiated a connection and
        serves the client as the protocol states. The function is just a
        wrapper over the meat of the protocol for multiprocessing processes
        to take on multiple clients at the same time.

    Usage:
    client, addr = s.accept()
    process = mp.Process(target=handleClient,args=(client,))

    Params:
    client - A socket connected with a client.
    clientRecords - A dictionary accessible by all processes to store all
        transactions with clients for easy checkpoint recovery.

    Returns:
    None. Closes the client connection. May edit clientRecords and send updates
        to the client as appropriate.
    '''
    with ssl.wrap_socket(client,server_side=True,\
            certfile="server.crt",keyfile="server.key") as client:
        # secure the socket
        checkpointNumber=0 # begin at the beginning of the update
        state='idle' # on connection establishment, we are idle
        while True: # wait for messages
            if state == 'updating' and prodKey is not None:
                updateInfo={}

                updateInfo = clientRecords[prodKey]
                updateInfo['prodKey'] = prodKey
                if updateInfo['isFragmented']:
                # The update is fragmented into checkpoints by server admin
                    # get all update fragments
                    chunks = glob(join(updateInfo['upPath'],'*.exe'))
                    error=False
                    for i in range(checkpointNumber,len(chunks)):
                        #print('sending chunk '+str(i))
                        chunkPath = join(updateInfo['upPath'],str(i)+'.exe')
                        # convert the current chunk number to a byte to send
                        #  to client.
                        checkpoint = (i).to_bytes(1,byteorder="big")
                        with open(chunkPath,'rb') as upF:
                        # read in the update file to be sent
                            update = upF.read()
                        client.send(checkpoint+update)
                        #print('chunk sent')
                        # wait for checkpoint ack "byte 1:  checkpointNumber byte 2: 00000001"
                        msg = client.recv(2)
                        if checkpoint!=msg[:1] or b'\x00'==msg[1:]:
                        # Right checkpoint not sent back or we want to pause.
                            client.close()
                            state='idle'
                            error=True
                            break 
                    if error:
                        break
                else: # the update is sent in one chunk
                    with open(updateInfo['upPath'],'rb') as upF:
                    # read in the update file to be sent
                        update = upF.read()
                    checkpoint=b'\x00' # one byte of 8 zeros
                    # send the update with the checkpoint as the first byte
                    client.send(checkpoint+update)
                    checkpoint = '0'
                    # wait for checkpoint ack 
                    msg = cf.decode(client.recv(2))

                client.send(cf.encode('update done'))
                #print('setting state to update termination')
                state = 'update termination'

            fields = cf.decode(client.recv(1024)).split(' ') # split into field list
            if fields[-1][-2:]!=cf.crlf:
            # Message does not end with carriage return line feed
                client.send(cf.encode('Improper syntax.'))
                client.close()
                state='idle'
                break
            fields[-1]=''.join(fields[-1].split()) # remove CRLF from last field

            # Check that number of characters in each field is below the maximum.
            for field in fields:
                if len(field)>maxField:
                    print('fuzzer')
                    client.send(cf.encode('A field has more than {} characters.'\
                            .format(str(maxField))))
                    client.close()
                    state='idle'
                    break

            if len(fields)==3: # client sent a message with 3 fields
                if state == 'update termination': 
                # this is an "update done" ack message
                    if fields[0] != updateInfo['prodKey']:
                        client.send(cf.encode('Invalid product key.'))
                        client.close()
                        state='idle'
                    if fields[1] != 'update' or fields[2] != 'done':
                        client.send(cf.encode('Invalid syntax.'))
                        client.close()
                        state='idle'
                    client.close()
                    state='idle'
                    prodKey=None
                    # print('update finished successfully')
                    clientRecords.pop(fields[0]) # remove transaction from record
                    # The transaction can also be saved to a historical file, 
                    #  if desired.
                    break
                if state == 'idle': # this is a checkpoint recovery message
                    #print('initiating recovery')
                    prodKey,checkpoint,clientSupVer=fields
                    if prodKey not in clientRecords.keys() or\
                        not clientRecords[prodKey]['isFragmented']:
                        #print('invalid key or update is not fragmented')
                        # If the update is not fragmented, then it would be sent
                        #  in one chunk, so checkpoint recovery is inappropriate
                        client.close()
                        break
                    if not exists(join(clientRecords[prodKey]['upPath'],checkpoint+'.exe')):
                        #print('invald checkpoint')
                        # The checkpoint number given does not correspond to 
                        #  a real chunk. Fuzzing.
                        client.close()
                        break
                    checkpointNumber = int(checkpoint)
                    state = 'updating'
                    # When the infinite while loop comes back around, it will
                    #  enter the 'updating' block now. The checkpointNumber
                    #  and prodKey variables ensure that the chunk from the
                    #  next checkpoint will be sent.



            elif len(fields)==4: # is the message an update ping?
                if state != 'idle': # Update ping only comes when we are in idle.
                # Fuzzing
                    client.send(cf.encode('Inappropriate message.'))
                    client.close()
                    break

                state='checking'
                prodKey, softVer, opSys, clientSupVer = fields

                # Do the fields make sense? 
                
                # Is the given SUP version a valid previous version?
                if clientSupVer not in supVers:
                    client.send(cf.encode('Invalid SUP version.{}'.format(clientSupVer)))
                    client.close()
                    state='idle'
                    break

                #Check for valid product key.
                if prodKey not in validKeys:
                    # Invalid key.
                    client.send(cf.encode('0'))
                    client.close()
                    state='idle'
                    break

                # Is the given operating system a valid OS?
                if opSys not in OSs:
                    # Invalid OS
                    client.send(cf.encode('Invalid operating system.'))
                    client.close()
                    state='idle'
                    break

                # Load update information for the given operating system from file.
                #  This file would be maintained by a server admin.
                with open('updateInfo.json','r') as f:
                    updateInfo = json.load(f)
                # Is the given software version a valid previous version?
                if softVer not in updateInfo[opSys]['prevVersions']:
                    # Invalid software version
                    client.send(cf.encode('Invalid software version.'))
                    client.close()
                    state='idle'
                    break

                if softVer == updateInfo[opSys]['softVer']: # client already has the latest version
                    client.close()
                    state = 'idle'
                    break

                # The ping is legitamate and the client needs an update. Make a record.
                clientRecords[prodKey]={'supVer':clientSupVer, 'opSys': opSys,\
                        'softVer':softVer,'spaceOK':False,'upPath':updateInfo[opSys]['loc'],\
                        'isFragmented':updateInfo[opSys]['isFragmented']}
            
                # get update size in megabytes
                upSize = getsize(updateInfo[opSys]['loc'])/10.**6.
                
                # send SUP version and update size to the client
                state='space check'
                upSizeMsg = cf.encode(' '.join([str(supVer),'{:f}'.format(upSize)]))
                client.send(upSizeMsg)

            elif len(fields)==2: # Are we receiving a space check reply?
                if state != 'space check' or state !='idle': 
                # need to be in space check or idle state.
                    client.send(cf.encode('Inappropriate message.'))
                    client.close()
                    state='idle'
                    break

                prodKey,yesNo = fields
                if prodKey not in clientRecords.keys():
                # is there a record of communicating with this product key?
                    client.send(cf.encode('Inappropriate message.'))
                    client.close()
                    state='idle'
                    break

                if yesNo not in ['0','1']:
                # second field is either '0' or '1'
                    client.send(cf.encode('Invalid syntax.'))
                    client.close()
                    state='idle'
                    break
                if yesNo == '0':
                # client does not have the space required.
                    client.close()
                    state='idle'
                    break
                if yesNo=='1':
                    state='updating'
                    clientRecords[prodKey]['spaceOK']=True
                    continue # Start the update
        client.close()
# Following tutorial from https://www.geeksforgeeks.org/socket-programming-python/
s=socket.socket()
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.setblocking(1)
s.bind(('',port))
s.listen(5)

while True: # wait for a connection
    prodKey=None
    client, addr = s.accept()
    process = mp.Process(target=handleClient,args=(client,))
    process.daemon = True
    process.start()
    # handleClient copied from here down
