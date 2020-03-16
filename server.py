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

port = cf.port
maxField = cf.maxField

validKeys=['123456789','123456799'] # Valid keys hardcoded for now
updateInfoFile = 'updateInfo.txt' # software versions and update executable
                                  # locations.

OSs=['windows','linux','mac']
supVers = ['1.0']
supVer = supVers[0]
# clientRecords = {} 
clientRecords = mp.Manager().dict() # So that all processes can read and write
                                    #  to the dictionary.

def verifyMsg(msg,state, validKey=None):
    '''
    verifyMsg takes a message from the client and makes sure that it has proper
        syntax and is appropriate for the state that we are in. STATEFUL.

    Usage:
    fields = verifyMsg(msg,state)

    Params:
    msg - The bytes object that comes straight from the client socket.
    state - A string, the current state of the protocol.
    validKey - optional, a string of the key that you need the message to
        have in order to be valid. Used when in update termination state.

    Returns:
    The fields of the msg as a list. If the message is no good, returns an
        empty list.
    '''
    # Message does not end with carriage return line feed
    #client.send(cf.encode('Improper syntax.'))
    #client.close()
    #state='idle'
    #break
    fields = cf.decode(msg).split(' ') # split into field list
    if fields[-1][-2:]!=cf.crlf:
    # The message does not end with carriage return line feed, a syntax error
       return [] 
    fields[-1]=''.join(fields[-1].split()) # remove CRLF from last field

    # Check that number of characters in each field is below the maximum.
    for field in fields:
        if len(field)>maxField:
            return []

    if state=='idle':
        if len(fields)==3: # 3 fields from idle means checkpoint recovery msg
            prodKey,checkpoint,clientSupVer=fields
            if prodKey not in clientRecords.keys() or\
                not clientRecords[prodKey]['isFragmented']:
                # Check that the product key is valid.
                # If the update is not fragmented, then it would be sent
                #  in one chunk, so checkpoint recovery is inappropriate
                return []
            if not exists(join(clientRecords[prodKey]['upPath'],checkpoint+'.exe')):
                # The checkpoint number given does not correspond to 
                #  a real chunk. Fuzzing.
                return []
            # the message is valid
        elif len(fields) == 4:
        # For fields from idle is an update ping
            state='checking'
            prodKey, softVer, opSys, clientSupVer = fields

            if clientSupVer not in supVers or \
                prodKey not in validKeys or \
                opSys not in OSs: 
            # The given SUP version is not a valid previous version or
            # the product key is not valid or
            # the operating system is not mac, windows, or linux.
                return []

            # Load update information for the given operating system from file.
            #  This file would be maintained by a server admin.
            with open('updateInfo.json','r') as f:
                updateInfo = json.load(f)
            # Is the given software version a valid previous version?
            if softVer not in updateInfo[opSys]['prevVersions']:
                return []

            if softVer == updateInfo[opSys]['softVer']: # client already has the latest version
                return []

            #The message is a valid update ping from a client that needs an update.
        elif len(fields)==2:
            prodKey,yesNo = fields
            if prodKey not in clientRecords.keys() or\
                yesNo != '1':
            # no record of communicating with this product key
            # or the second field is not 1, as it should be when coming from
            # idle and sending a space OK message.
                return []
        # if you made it this far, the message is valid
    elif state=='space check':
        if len(fields)!=2:
        # Space check message is 2 fields only.
            return []
        prodKey,yesNo = fields
        if prodKey not in clientRecords.keys() or\
            yesNo not in ['0','1']:
        # no record of communicating with this product key
        # or the second field is not 1 or 0, as it should be when in space check
            return []
    elif state == 'update termination': 
    # we are checking for an update done ack message
        if len(fields)!= 3:
        # update ack message has 3 fields
            return []
        if fields[0] != validKey or fields[1] != 'update' or fields[2] != 'done':
        # The product key is not valid or the next two fields are update done
            return []
    return fields
            

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
    client=ssl.wrap_socket(client,server_side=True,\
            certfile="server.crt",keyfile="server.key")

    # secure the socket
    checkpointNumber=0 # begin at the beginning of the update
    state='idle' # on connection establishment, we are idle
    prodKey=None
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

        fields=verifyMsg(client.recv(1024),state,prodKey)
        if not fields:
        # if the message violates the DFA, close the connection
            client.close()
            state='idle'
            break

        if state == 'update termination':
            client.close()
            state = 'idle'
            prodKey = None
            clientRecords.pop(fields[0])
            # Transaction removed from the record, completed successfully.
            #  This can be saved in a historical record instead.
            break
        elif state == 'idle':
            if len(fields)==3: # checkpoint recovery message
                prodKey,checkpoint,clientSupVer = fields
                checkpointNumber = int(checkpoint)
                state = 'updating'
                continue
                # When the infinite while loop comes back around, it will
                #  enter the 'updating' block now. The checkpointNumber
                #  and prodKey variables ensure that the chunk from the
                #  next checkpoint will be sent.
            elif len(fields)==4:
            # we have a client that needs an update. Create a record of
            #  the transaction.
                state = 'checking'
                prodKey, softVer, opSys, clientSupVer = fields
                with open('updateInfo.json','r') as f:
                    updateInfo = json.load(f)
                clientRecords[prodKey]={'supVer':clientSupVer, 'opSys': opSys,\
                    'softVer':softVer,'spaceOK':False,'upPath':updateInfo[opSys]['loc'],\
                    'isFragmented':updateInfo[opSys]['isFragmented']}

                # get update size in megabytes
                upSize = getsize(updateInfo[opSys]['loc'])/10.**6.
                
                # send SUP version and update size to the client
                state='space check'
                upSizeMsg = cf.encode(' '.join([str(supVer),'{:f}'.format(upSize)]))
                client.send(upSizeMsg)
        elif state=='space check':
            prodKey,yesNo = fields
            if yesNo=="0":
                client.close()
                state='idle'
                break
            else: # The client has the necessary space and is ready for update
                state = 'updating'
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
    #https://gist.github.com/micktwomey/606178
    process = mp.Process(target=handleClient,args=(client,))
    process.daemon = True
    process.start()
    # handleClient copied from here down
