# commonFuncs - Functions and constants used by both client and server 
#   processes.


crlf='\r\n'
def encode(string):
    '''
    encode - Takes a string and encodes it into binary using ASCII

    Usage:
    encodedString = encode(stringToEncode)

    Params:
    string - a string

    Output:
    A python bytes object, the given string encoded with ASCII.
    '''
    #return string.encode('ascii')
    return bytes(string+crlf, 'ascii')

def decode(bytess):
    '''
    decode - Takes a bytes object and decodes it into a string with ASCII

    Usage:
    decodedString = decode(bytesToDecode)

    Params:
    bytess - a bytes object of ASCII encoded string. For example, a message 
        from client/server.

    Output:
    A string, the message from the given bytess object.
    '''
    return bytess.decode('ascii')

