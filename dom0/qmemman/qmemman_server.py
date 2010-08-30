#!/usr/bin/python
import SocketServer
import thread
import time
import xen.lowlevel.xs
import sys
import os
from qmemman import SystemState

system_state = SystemState()
global_lock = thread.allocate_lock()
additional_balance_delay = 0

def only_in_first_list(l1, l2):
    ret=[]
    for i in l1:
        if not i in l2:
            ret.append(i)
    return ret

def get_req_node(domain_id):
    return '/local/domain/'+domain_id+'/memory/meminfo'

                    
class WatchType:
    def __init__(self, fn, param):
        self.fn = fn
        self.param = param

class XS_Watcher:
    def __init__(self):
        self.handle = xen.lowlevel.xs.xs()
        self.handle.watch('/local/domain', WatchType(XS_Watcher.dom_list_change, None))
        self.watch_token_dict = {}

    def dom_list_change(self, param):
        curr = self.handle.ls('', '/local/domain')
        if curr == None:
            return
        global_lock.acquire()
        for i in only_in_first_list(curr, self.watch_token_dict.keys()):
            watch = WatchType(XS_Watcher.request, i)
            self.watch_token_dict[i] = watch
            self.handle.watch(get_req_node(i), watch)
            system_state.add_domain(i)
        for i in only_in_first_list(self.watch_token_dict.keys(), curr):
            self.handle.unwatch(get_req_node(i), self.watch_token_dict[i])
            self.watch_token_dict.pop(i)
            system_state.del_domain(i)
        global_lock.release()

    def request(self, domain_id):
        ret = self.handle.read('', get_req_node(domain_id))
        if ret == None or ret == '':
            return
        global_lock.acquire()
        system_state.refresh_meminfo(domain_id, ret)
        global_lock.release()

    def watch_loop(self):
#        sys.stderr = file('/var/log/qubes/qfileexchgd.errors', 'a')
        while True:
            result = self.handle.read_watch()
            token = result[1]
            token.fn(self, token.param)


class QMemmanReqHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        while True:
            self.data = self.request.recv(1024).strip()
            if len(self.data) == 0:
                print 'EOF'
                return
            if self.data == "DONE":
                return
            global_lock.acquire()
            if system_state.do_balloon(int(self.data)):
                resp = "OK\n"
                additional_balance_delay = 5
            else:
                resp = "FAIL\n"
            global_lock.release()
            self.request.send(resp)


def start_server():
    SOCK_PATH='/var/run/qubes/qmemman.sock'
    try:
        os.unlink(SOCK_PATH)
    except:
        pass
    os.umask(0)
    server = SocketServer.UnixStreamServer(SOCK_PATH, QMemmanReqHandler)
    os.umask(077)
    server.serve_forever()

def start_balancer():
    while True:
        time.sleep(1)
        if additional_balance_delay == 0:
            time.sleep(additional_balance_delay)
            additional_balance_delay = 0
        global_lock.acquire()
        if additional_balance_delay == 0:
            system_state.do_balance()
        global_lock.release()

class QMemmanServer:
    @staticmethod          
    def main():
        thread.start_new_thread(start_server, tuple([]))
        thread.start_new_thread(start_balancer, tuple([]))
        XS_Watcher().watch_loop()
