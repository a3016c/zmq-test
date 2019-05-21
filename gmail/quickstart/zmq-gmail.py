import zmq
import requests
import argparse
from requests.exceptions import ConnectionError
import sys
import time, sched
from read_email import read_email as re
import signal
import zmq_constants

#our local zeromq endpoints
zmq_events_addr = 'tcp://127.0.0.1:8008'
zmq_buy_filter = 'BUY'
zmq_sell_filter = 'SELL'
#zmq_prices_addr = 'tcp://127.0.0.1:8009'
#zmq_prices_filter = 'TCK'

def signal_handler(sig, frame):
    print('You pressed CTRL+C!!')
    sys.exit(0)


class server():

    def __init__(self, mode, zmq_addr):
        self.mode = mode
        self.zmq_addr = zmq_addr
        self.zmq_filter = zmq_buy_filter
        self.stime = time.time()
        self.zmq_sock = None

    def publisher(self):
        """Create the ZMQ public socket"""
        sock = zmq.Context().socket(zmq.PUB)
        print("ZMQ: opening %s" % self.zmq_addr)
        sock.bind(self.zmq_addr)
        return sock

    def publish_to_zmq(self, msg):
        print(msg)
        self.zmq_sock.send_string(msg)

    def readmail(self):
        self.zmq_sock = self.publisher()
        while True:
            mail_return = re()
            #Set the ZMQ filter to the side of the trade recvd from read_email()
            self.zmq_filter = mail_return.split()[0]
            msg = self.zmq_filter+' : '+mail_return
            self.publish_to_zmq(msg)
            time.sleep(10.0 - ((time.time() - self.stime) % 10.0))

def main():
    parser = argparse.ArgumentParser(description='VWAP strategy BUY/SELL ZMQ')
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--buy_client',help='Client for Buy side',action='store_true')
    g.add_argument('--sell_client',help='Client for Sell side', action='store_true')
    g.add_argument('--server',help='Server to read emails',action='store_true')
    args = parser.parse_args()

    # Buy side client
    if args.buy_client:
        #Subscribe to Emails
        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.connect(zmq_constants.constants().zmq_events_addr)
        try:
            sock.setsockopt_string(zmq.SUBSCRIBE, zmq_constants.constants().zmq_buy_filter.encode())
        except:
            sock.setsockopt(zmq.SUBSCRIBE, zmq_constants.constants().zmq_buy_filter.encode())

        while True:
            try:
                s = sock.recv_string()
                print(s)
            except KeyboardInterrupt as e:
                print('Keyboard Interrupted.')
                sys.exit(1)

    #Sell side client
    if args.sell_client:
        #Subscribe to Emails
        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.connect(zmq_constants.constants().zmq_events_addr)
        try:
            sock.setsockopt_string(zmq.SUBSCRIBE, zmq_constants.constants().zmq_sell_filter.encode())
        except:
            sock.setsockopt(zmq.SUBSCRIBE, zmq_constants.constants().zmq_sell_filter.encode())

        while True:
            try:
                s = sock.recv_string()
                print(s)
            except KeyboardInterrupt as e:
                print('Keyboard Interrupted.')
                sys.exit(1)

    if args.server:
        #Publish Emails
        try:
            srv = server(args.server, zmq_constants.constants().zmq_events_addr)
            srv.readmail()
        except KeyboardInterrupt as e:
            print('Keyboard Interrupted.')
            sys.exit(1)

if __name__ =='__main__':
    main()
