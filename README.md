# sup
Erixen Cruz ec622@drexel.edu
13 March 2020

The server and client are implemented in server.py and client.py. To use
openssl, I followed https://carlo-hamalainen.net/2013/01/24/python-ssl-socket-echo-test-with-self-signed-certificate/.
The certificate and keys I created are included here as server.crt, server.csr,
server.key, and server.orig.key.

To run the server, call "python3 server.py". It must be running before the
client can run.

To run the client, call "python3 client.py prodKey opSys softVer serverIP/hostname".
I have hard coded two valid product keys: 123456789 and 123456799. softVer
should be 1.0 as well. In practice, more valid keys and previous software
versions can be included. Operating systems are either "windows", "mac", or "linux".
The examples that I have come up with are only for windows and linux, though.
These are just nominal to show that the program can differentiate between them
and send the correct update based on operating system. The update examples are
toys to check that the protocol is working correctly.

The bash scripts are examples of clients updating from localhost. defaultClient
asks for a linux update that has no checkpoints. To test for checkpoints,
I have windowsClient. I hardcode delays in the writing of chunks to be able to
pause and restart the download. Pause with control-c. Resume with windowsResume.
client.py saves the update in update.exe and the checkpoint in
updateCheckpointNumber.txt.
The update chunks are kept in a folder "windows1.2". They are just 10 files of
one byte each counting from 0 to 9. I assume for this implementation that
another program splits the update into files and puts them in one directory
to send out to clients. To test the checkpoint recovery, do "bash windowsClient.bash"
and contol-c after a few seconds. If you look in update.exe, you will see that 
the client has downloaded a byte each second. It has also saved the last checkpoint
in updateCheckpointNumber.txt. Finish the download with "bash windowsResume.bash".

Each time you want to test it out, you must rm update.exe.

updateInfo.json contains information about the software to be updated: the
versions for each OS, previous versions, and whether the updates are split
into chunks and locations of the executables. This is the way that a server 
admin could control how the server protocol updates its clients.

I think the server is hard to crack through fuzzing becuase it thoroughly checks
all messages to make sure that they have the correct syntax, that they make sense
and are appropriate for the current state.

I did not implement the extra credit.
