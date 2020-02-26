# commonFuncs - Functions used by both client and server processes.

def encode(string):
    #return string.encode('ascii')
    return bytes(string, 'ascii')

def decode(bytess):
    return bytess.decode('ascii')
