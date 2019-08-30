import argparse
import regex as re
import sys
import time
import zmq
from trader import ibpy
import logging
from logging.handlers import RotatingFileHandler
import zmq_constants
from read_email import read_unread_mail
#logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.WARNING)

# our local zeromq endpoints
zmq_events_addr = 'tcp://127.0.0.1:8008'
zmq_buy_filter = 'BUY'
zmq_sell_filter = 'SELL'



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
            #print('Trying to check email now.')
            try:
                mail_return = r_email.read()
            except ServerNotFoundError as e:
                print('Unable to check email')
                print(e)
                sys.exit(2)

            if mail_return == zmq_constants.constants().unread_message:
                # print('No unread messages found.Going to sleep...')
                # time.sleep(10.0 - ((time.time() - self.stime) % 10.0))
                time.sleep(30)
                continue
            else:
                for msg in mail_return:
                    msg_body = r_email.get_msg_body(msg=msg)
                    contract_list = regex.findall(msg_body)  # example ['/MES','/CL','/6E']

                    if constants.msg_scope in msg_body:
                        if constants.BUY_SEARCH in msg_body:
                            for _eachcontract in contract_list:
                                if _eachcontract in constants.allowed_contracts:
                                    size = int(zmq_constants.constants().standard_size)
                                    contractString = _eachcontract.split('/')[1]
                                    trade = trade_bucket(contract=_eachcontract, size=size)
                                    ibpy(size, contractString)
                                    # msg = constants.zmq_buy_filter + ' ' + _eachcontract
                                    # self.publish_to_zmq(msg)
                                else:
                                    print('Not trading %s at this point in time.' % _eachcontract)
                        elif constants.SELL_SEARCH in msg_body:
                            for _eachcontract in contract_list:
                                if _eachcontract in constants.allowed_contracts:
                                    size = (0 - int(zmq_constants.constants().standard_size))
                                    contractString = _eachcontract.split('/')[1]
                                    trade = trade_bucket(contract=_eachcontract, size=size)
                                    ibpy(size, contractString)
                                    # msg = constants.zmq_sell_filter + ' ' + _eachcontract
                                    # self.publish_to_zmq(msg)
                                else:
                                    logger.warning('Not trading %s at this point in time.' % _eachcontract)

            time.sleep(30)
            # time.sleep(10.0 - ((time.time() - self.stime) % 10.0))


class trade_bucket():
    def __init__(self, contract, size=0):
        self.size = 0
        self.contract = contract


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
                logger.info('Trade:', s.split()[1].split('/')[1])
            except KeyboardInterrupt as e:
                logger.debug('Keyboard Interrupted.')
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
                size = (int(zmq_constants.constants().standard_size))
                contractString = s.split()[1].split('/')[1]
                logger.info('Trade %s %s' % (size, contractString))
                ibpy(size, contractString)
            except KeyboardInterrupt as e:
                logger.debug('Keyboard Interrupted.')
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
                size = (0 - int(zmq_constants.constants().standard_size))
                contractString = s.split()[1].split('/')[1]
                logger.info('Trade %s %s' % (size, contractString))
                ibpy(size, contractString)
            except KeyboardInterrupt as e:
                logger.debug('Keyboard Interrupted.')
                sys.exit(1)

    if args.server:
        # Publish Emails
        try:
            srv = server(args.server, zmq_constants.constants().zmq_events_addr)
            srv.readmail()
        except KeyboardInterrupt as e:
            logger.debug('Keyboard Interrupted.')
            sys.exit(1)


if __name__ == '__main__':
    format = "%(asctime)s %(levelname)s : %(message)s"
    logging.basicConfig(format=format, level=logging.DEBUG, datefmt='%D : %H-%M-%S',
                        filename='email_trader_ib.log',filemode='w')
    logging.info("Main : before creating thread")
    #log = RotatingFileHandler(filename='email_trader_ib.log', mode='a', maxBytes=5 * 1024 * 1024,
    #                         backupCount=1, encoding=None, delay=0)
    logger = logging.getLogger(__name__)
    #logger.addHandler(log)

    main()
