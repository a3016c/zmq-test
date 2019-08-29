import argparse
import ezibpy
import regex as re
import requests
import sched
import signal
import sys
import time
import zmq
from qtpylib import futures
from requests.exceptions import ConnectionError

import zmq_constants
from read_email import read_unread_mail

# our local zeromq endpoints
zmq_events_addr = 'tcp://127.0.0.1:8008'
zmq_buy_filter = 'BUY'
zmq_sell_filter = 'SELL'


# zmq_prices_addr = 'tcp://127.0.0.1:8009'
# zmq_prices_filter = 'TCK'

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
        regex = re.compile('/+\w*')
        r_email = read_unread_mail(label='UNREAD')

        constants = zmq_constants.constants()
        while True:
            # Check your email from UNREAD label
            print('Trying to check email now.')
            mail_return = r_email.read()

            if mail_return == zmq_constants.constants().unread_message:
                #print('No unread messages found.Going to sleep...')
                #time.sleep(10.0 - ((time.time() - self.stime) % 10.0))
                time.sleep(30)
                continue
            else:
                for msg in mail_return:
                    msg_body = r_email.get_msg_body(msg=msg)
                    contract_list = regex.findall(msg_body) # example ['/MES','/CL','/6E']

                    if constants.msg_scope in msg_body:
                        if constants.BUY_SEARCH in msg_body:
                            for _eachcontract in contract_list:
                                if _eachcontract in constants.allowed_contracts:
                                    msg = constants.zmq_buy_filter + ' ' + _eachcontract
                                    self.publish_to_zmq(msg)
                                else:
                                    print('Not trading %s at this point in time.' % _eachcontract)
                        elif constants.SELL_SEARCH in msg_body:
                            for _eachcontract in contract_list:
                                if _eachcontract in constants.allowed_contracts:
                                    msg = constants.zmq_sell_filter + ' ' + _eachcontract
                                    self.publish_to_zmq(msg)
                                else:
                                    print('Not trading %s at this point in time.' % _eachcontract)

            #            print('sleeping')
            time.sleep(30)
            #time.sleep(10.0 - ((time.time() - self.stime) % 10.0))


def check_active_position(ibConn, symbol_string):
    for sym, value in ibConn.positions.items():
        # e.g. sym value GCQ2019_FUT
        # print(sym, '****', value['position'])
        if symbol_string == sym and value['position'] != 0:
            print('Open Positions for %s : %s' % (sym, value['position']))
            return True
    print('No active positions for %s' % symbol_string)
    return False


def ibpy(size=1, contractString=None):
    """
    Method to place orders
    :param size: Size of order, -ve if Shorting, +ve if Buying
    :param contractString: String format for Contract name , ex: MES, MNQ, NQ
    :return: bool
    """
    constants = zmq_constants.constants()

    try:
        ibConn = ezibpy.ezIBpy()
        exchange = 'GLOBEX'
        ibConn.connect(host=constants.host, port=constants.port,
                       account=constants.account)

        # subscribe to account/position updates
        ibConn.requestPositionUpdates(subscribe=True)
        ibConn.requestAccountUpdates(subscribe=True)
        time.sleep(3)

        active_month = futures.get_active_contract(contractString)
        if contractString in ['CL', 'QM', 'GC']:
            exchange = 'NYMEX'
        contract = ibConn.createFuturesContract(contractString,
                                                exchange=exchange,
                                                expiry=constants.expiry)
        # Get symbol_string
        # e.g. sym value GCQ2019_FUT
        symbol_string = ibConn.contractString(contract)

        # Create order only if no active positions
        if not check_active_position(ibConn, symbol_string):
            order = ibConn.createOrder(quantity=size)
            orderId = ibConn.placeOrder(contract, order)
            time.sleep(3)

        # subscribe to account/position updates
        ibConn.requestPositionUpdates(subscribe=False)
        ibConn.requestAccountUpdates(subscribe=False)

        # disconnect
        ibConn.disconnect()
        time.sleep(2)
    except Exception as e:
        print('Exception occurred.')
        print(e)
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description='MovingAverage strategy BUY/SELL ZMQ')
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--buy_client', help='Client for Buy side', action='store_true')
    g.add_argument('--sell_client', help='Client for Sell side', action='store_true')
    g.add_argument('--trade_client', help='Client for Trading', action='store_true')
    g.add_argument('--server', help='Server to read emails', action='store_true')
    args = parser.parse_args()

    # Trade client
    if args.trade_client:
        # Subscrive to emails
        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.connect(zmq_constants.constants().zmq_events_addr)
        try:
            sock.setsockopt_string(zmq.SUBSCRIBE, zmq_constants.constants().trade_filter.encode())
        except:
            sock.setsockopt(zmq.SUBSCRIBE, zmq_constants.constants().trade_filter.encode())

        while True:
            try:
                s = sock.recv_string()
                print('Trade:', s.split()[1].split('/')[1])
            except KeyboardInterrupt as e:
                print('Keyboard Interrupted.')
                sys.exit(1)

    # Buy side client
    if args.buy_client:
        # Subscribe to Emails
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
                size = (int(zmq_constants.constants().size))
                contractString = s.split()[1].split('/')[1]
                print('Trade %s %s' % (size, contractString))
                ibpy(size, contractString)
            except KeyboardInterrupt as e:
                print('Keyboard Interrupted.')
                sys.exit(1)

    # Sell side client
    if args.sell_client:
        # Subscribe to Emails
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
                size = (0 - int(zmq_constants.constants().size))
                contractString = s.split()[1].split('/')[1]
                print('Trade %s %s' % (size, contractString))
                ibpy(size, contractString)
            except KeyboardInterrupt as e:
                print('Keyboard Interrupted.')
                sys.exit(1)

    if args.server:
        # Publish Emails
        try:
            srv = server(args.server, zmq_constants.constants().zmq_events_addr)
            srv.readmail()
        except KeyboardInterrupt as e:
            print('Keyboard Interrupted.')
            sys.exit(1)


if __name__ == '__main__':
    main()
