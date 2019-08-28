import argparse
import datetime as dt
import sys
from logging.handlers import RotatingFileHandler
from sys import platform
import ezibpy
from ib.ext.Order import Order
from order_logic import *
from qtpylib import futures
from util import *

today = dt.datetime.today().strftime("%Y-%m-%d")

# get current query time
queryTime = (dt.datetime.today() - dt.timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")


def get_historical_data(ibConn):
    # request 2 days of 30 minute data and save it to current path ./
    ibConn.requestHistoricalData(resolution="30 mins", lookback="1 D",
                                 csv_path=path)
    time.sleep(1)
    ibConn.cancelHistoricalData()

    return None


def vwap_highlow_logic(self):
    """
    Logic to check for trade entry on either previous high or previous low
    :param self: Instance of algorithm of choice
    :return: boolean
    """
    stoch(self, fast=True)
    # Enter the logic only when last 10 bars have been filled.
    if len(self.bars_history) < 10:
        log.info('Bars size is less than 10.')
        return
    print(self.bars_history.fast_k)

    # Open a new position
    if not check_active_position(self):
        log.info('Status: Looking for new trades.')
        if not is_pending_order(self):
            if prevHigh_above_upperband(self) or prevLow_below_lowerband(self):
                if not currenVwap_between_prevHighLow(self):
                    # Enter new trades with STOP
                    mainOrder = previousHighLowOrder(self)
    elif check_active_position(self):
        # get the direction
        position_size = get_position_size(self)
        if position_size > 0:
            self.direction = 'BUY'
            if vwap(self.bars_history,-1) >= self.last:
                self.towards_vwap = True
            else:
                self.away_from_vwap = True

        elif position_size < 0:
            self.direction = 'SELL'
            if vwap(self.bars_history, -1) <= self.last:
                self.towards_vwap = True
            else:
                self.away_from_vwap = True

        """ Close positions if current VWAP is between previous high and previous low """
        log.info('Status: Looking for closing trades.')
        #if currenVwap_between_prevHighLow(self):
        #    closePositionOrder(self)
        if closeOnTouchOppositeVwap(self):
            """ Close the position if price has touched either of the bands """
            closePositionOrder(self)

        # Adjust stops - NO need as per new algorithm
        #log.info('Status: Looking to adjust stops.')
        #if not moveStopOrder(self):
        #    log.info('Unable to move stops.')

class System:
    def __init__(self, symbol, contract_tuple, tradeSize, logger, port=7496, client=3016, host='localhost'):
        self.client = client
        self.host = host
        self.is_running = False
        self.port = port
        self.contract_tuple = contract_tuple
        self.tradeSize = tradeSize
        self.symbol = symbol
        self.ibConn = None
        self.inPosition = False
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.position = 0
        self.account_code = None
        self.symbol_id = 0
        self.order_ids = [-1]
        self.is_position_opened = False
        # self.secType, self.exchange, self.primary_exchange, self.currency = secType, exchange, primary_exchange, currency
        self.secType = contract_tuple[1]
        self.exchange = contract_tuple[2]
        if self.exchange is not None:
            exchange = self.exchange.upper().replace('NASDAQ', 'ISLAND')
        self.currency = contract_tuple[3]
        self.expiry = contract_tuple[4]
        self.strike = contract_tuple[5]
        self.right = contract_tuple[6]
        self.bars_history = None
        self.contract = None
        self.filename = None
        self.last = None
        self.direction = None
        self.risk, self.reward = 0.0, 0.0
        self.logger = logger
        self.pending_order = False
        self.path = path
        self.towards_vwap = False  # Flag for direction towards VWAP
        self.away_from_vwap = False  # Flag for direction away from VWAP

    def error_handler(self, msg):
        if msg.typeName == "error" and msg.id != -1:
            logger.error("Server error:", msg)

    def server_handler(self, msg):
        if msg.typeName == "nextValidId":
            self.order_id = msg.orderId
        elif msg.typeName == "managedAccounts":
            self.account_code = msg.accountsList
        elif msg.typeName == "updatePortfolio" \
                and msg.contract.m_symbol == self.symbol:
            self.unrealized_pnl = msg.unrealizedPNL
            self.realized_pnl = msg.realizedPNL
            self.position = msg.position
        elif msg.typeName == "error" and msg.id != -1:
            return

    def get_last_price(self):
        # tickerId = list(self.ibConn.marketData.keys())[1]
        # last = self.ibConn.marketData[tickerId]['last'][0]
        self.last = close(self.bars_history, -1)
        logger.info('Last price: %s' % self.last)

    def check_position_open(self):
        if check_active_position(self):
            self.is_position_opened = True
        else:
            self.is_position_opened = False

    def tick_event(self, msg):
        logger.info(msg)
        if msg.field == 1:
            self.bid_price = msg.price
        elif msg.field == 2:
            self.ask_price = msg.price

        logger.info(
            "%s - self.ask_price '%s', self.bid_price '%s', " % (dt.datetime.now(), self.ask_price, self.bid_price))

        self.trade_logic()

    def create_order(self, order_type, quantity, action):
        order = Order()
        order.m_orderType = order_type
        order.m_totalQuantity = quantity
        order.m_action = action
        return order

    def create_bracketorder(self, action, qty, limit=None, profit_price=None, stop_price=None,

                            transmit=True, parentId=None):
        # https://www.interactivebrokers.com/en/software/api/apiguide/tables/supported_order_types.htm
        # https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
        order = Order()

        # is child order?
        if parentId is not None:
            order.m_parentId = parentId

        order.m_action = action
        order.m_totalQuantity = qty

        if profit_price is not None:

            # This will set up out profit take
            order.m_orderType = 'LMT'
            if action == 'BUY':

                # Precise the LMT price to close profit
                order.m_lmtPrice = profit_price
            elif action == 'SELL':
                order.m_lmtPrice = profit_price

            print("4/Bracket order - stop profit price = '%s'" % order.m_lmtPrice)

        elif stop_price is not None:

            # This will set up out trailing stop
            order.m_orderType = 'Stop'
            if action == 'BUY':
                # Precise the Stop Loss price
                order.m_auxPrice = stop_price
            elif action == 'SELL':
                order.m_auxPrice = stop_price

            print("3/Bracket order - stop loss price = '%s'" % order.m_auxPrice)


        elif limit is not None:
            # A simple limit order
            order.m_orderType = 'STP'
            if action == 'BUY':
                # Precise the STP price to invest
                order.m_auxPrice = limit
            elif action == 'SELL':
                order.m_auxPrice = limit

            print("1/Bracket order - invest price  = '%s'" % order.m_auxPrice)


        else:
            # A simple market order
            order.m_orderType = 'MKT'

        # Important that we only send the order when all children are formed.
        order.m_transmit = transmit

        return order

    def create_contract(self):
        self.contract = self.ibConn.createContract(self.contract_tuple)
        # Generate the filename for the contract.
        self.filename = self.ibConn.contractString(self.contract) + '.csv'

    def request_historical_data(self):
        self.ibConn.requestHistoricalData(resolution='30 mins', lookback='1 D', csv_path=path)
        time.sleep(10)

    def read_historical_data(self):
        headers = ['datetime', 'O', 'H', 'L', 'C', 'V', 'OI', 'WAP']
        try:
            self.bars_history = pd.read_csv(path + self.filename, skiprows=1, header=1, names=headers)
            logger.info(self.bars_history.tail())
        except Exception as e:
            logger.exception('Unable to read historical data.')
        finally:
            self.ibConn.cancelHistoricalData()

    def request_market_data(self):

        self.ibConn.requestMarketData(contracts=self.contract,
                                      snapshot=False)
        time.sleep(1)
        self.cancel_market_data()

    def request_account_updates(self, account_code):
        self.ibConn.reqAccountUpdates(True, account_code)

    def connect_to_tws(self):
        self.ibConn = ezibpy.ezIBpy()
        self.ibConn.connect(clientId=self.client, host=self.host, port=self.port)

    def disconnect_from_tws(self):
        if self.ibConn is not None:
            self.ibConn.disconnect()

    def cancel_market_data(self):
        self.ibConn.cancelMarketData(self.contract)
        time.sleep(1)

    def trade_logic(self):
        vwap_highlow_logic(self)

    def calculate_vwap(self):
        """
        calculate vwap of entire time series
        (input can be pandas series or numpy array)
        bars are usually mid [ (h+l)/2 ] or typical [ (h+l+c)/3 ]
        """
        calculate_vwap(self.bars_history)
        vwapbands_rolling(self.bars_history)
        self.bars_history['symbol'] = self.symbol

    def _reqMktData(self, contracts=None, snapshot=False):
        """
        Register to streaming market data updates
        https://www.interactivebrokers.com/en/software/api/apiguide/java/reqmktdata.htm
        """
        if contracts == None:
            contracts = list(ibConn.contracts.values())
        elif not isinstance(contracts, list):
            contracts = [contracts]

        for contract in contracts:
            print(contract)
            if snapshot:
                reqType = ""
            else:
                pass
                #reqType = dataTypes["GENERIC_TICKS_RTVOLUME"]
                #if contract.m_secType in ("OPT", "FOP"):
                #    reqType = dataTypes["GENERIC_TICKS_NONE"]
            tickerId = self.ibConn.tickerId(self.ibConn.contractString(contract))
            print(tickerId, 'contract=', contract)

            # get market data for single contract
            # limit is 250 requests/second
            if not self.ibConn.isMultiContract(contract):
                try:
                    tickerId = self.ibConn.tickerId(self.ibConn.contractString(contract))
                    print(tickerId, 'contract=', self.ibConn.contractString(contract))
                    self.ibConn.reqMktData(tickerId, contract, reqType, snapshot)
                    time.sleep(0.0042)  # 250 = 1.05s
                except KeyboardInterrupt:
                    sys.exit()


    def start(self):
        try:
            self.connect_to_tws()
            logger.info('Connected.')
            self.create_contract()
            #self.request_historical_data()
            #self.read_historical_data()
            #self.calculate_vwap()
            # TODO: request_account_updates is not working
            #self.request_account_updates(self.account_code)
            #self._reqMktData()
            #self.request_market_data()
            self.check_position_open()
            self.get_last_price()
            self.monitor_position()
            self.trade_logic()
        except Exception as e:
            logger.error(e)
            self.cancel_market_data()
        finally:
            logger.info('Disconnected.')
            self.disconnect_from_tws()

    def monitor_position(self):
        logger.info('Position: %s UPnl: %s RPnl: %s' % (self.position, self.unrealized_pnl, self.realized_pnl))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Strategy executor.')
    parser.add_argument("-c", "--contract", help='Contract Name', required=False, type=str)
    parser.add_argument("-t", "--sleeptime", help='Sleep time in seconds', required=False, default=30, type=int)
    args = parser.parse_args()

    format = "%(asctime)s: %(message)s"
    logger = logging.getLogger(__name__)
    logging.basicConfig(format=format, level=logging.INFO, datefmt='%D : %H-%M-%S')
    logging.info("Main : before executing strategy")
    log = RotatingFileHandler(filename='MovingAverageSystems-trading.log', mode='a', maxBytes=5 * 1024 * 1024,
                              backupCount=1, encoding=None, delay=0)
    log.setLevel(logging.INFO)
    logger.addHandler(log)

    if platform == 'win32':
        path = 'C:/Users/abhis/Documents/projects/projects/ibpy/ezibpy/data/'
    elif platform == 'darwin':
        path = '/Users/abhishek.chaturvedi/Downloads/Rough/projects/ibpy/ezibpy/data/'

    symbols = ['MES', 'MNQ','QM', 'M2K', 'MYM']
    if args.contract:
        symbols = [args.contract]
    try:
        while True:

            # Get Historical data
            # create a contract

            # initialize ezIBpy
            ibConn = ezibpy.ezIBpy()
            ibConn.connect(clientId=3016, host="localhost", port=7496)
            logger.info('')

            #m2k_contract = ibConn.createContract(
            #    ("M2K", "FUT", "GLOBEX", "USD", futures.get_active_contract("M2K"), 0.0, ""))
            # eur_contract = ibConn.createContract(
            #    ("EUR", "FUT", "GLOBEX", "USD", futures.get_active_contract("EUR"), 0.0, ""))
            #mes_contract = ibConn.createContract(
            #    ("MES", "FUT", "GLOBEX", "USD", futures.get_active_contract("MES"), 0.0, ""))
            #mnq_contract = ibConn.createContract(
            #    ("MNQ", "FUT", "GLOBEX", "USD", futures.get_active_contract("MNQ"), 0.0, ""))
            #mym_contract = ibConn.createContract(
            #    ("MYM", "FUT", "GLOBEX", "USD", futures.get_active_contract("MYM"), 0.0, ""))
            # nq_contract = ibConn.createContract(
            #    ("NQ", "FUT", "GLOBEX", "USD", futures.get_active_contract("NQ"), 0.0, ""))
            # cl_contract = ibConn.createContract(
            #    ("CL", "FUT", "NYMEX", "USD", futures.get_active_contract("CL"), 0.0, ""))
            #qm_contract = ibConn.createContract(
            #    ("QM", "FUT", "NYMEX", "USD", futures.get_active_contract("QM"), 0.0, ""))
            # es_contract = ibConn.createContract(
            #    ("ES", "FUT", "GLOBEX", "USD", futures.get_active_contract("ES"), 0.0, ""))
            # rty_contract = ibConn.createContract(
            #    ("RTY", "FUT", "GLOBEX", "USD", futures.get_active_contract("RTY"), 0.0, ""))
            # gc_contract = ibConn.createContract(
            #    ("GC", "FUT", "NYMEX", "USD", futures.get_active_contract("GC"), 0.0, ""))
            # aud_contract = ibConn.createContract(
            #    ("AUD", "FUT", "GLOBEX", "USD", futures.get_active_contract("AUD"), 0.0, ""))

            # request 2 days of 30 minute data and save it to current path ./
            ibConn.requestHistoricalData(resolution="30 mins", lookback="1 D",
                                         csv_path=path)
            time.sleep(10)
            ibConn.cancelHistoricalData()
            ibConn.disconnect()

            for eachSymbol in symbols:
                # expiry_month = 201909
                exchange = "GLOBEX"
                if eachSymbol in ['QM', 'CL', 'GC']:
                    # expiry_month = 201908
                    exchange = "NYMEX"
                if eachSymbol in ['EUR', 'AUD']:
                    # expiry_month = 201908
                    exchange = "GLOBEX"
                #contract_tuple = (eachSymbol, "FUT", exchange, "USD", futures.get_active_contract(eachSymbol), 0.0, "")
                contract_tuple = (eachSymbol, "FUT", exchange, "USD", 201909, 0.0, "")
                vwapsystem = System(eachSymbol, contract_tuple, tradeSize=5, logger=logger)
                logger.info("Starting work for %s" % contract_tuple[0])
                logger.info(contract_tuple)
                vwapsystem.start()
                time.sleep(args.sleeptime)
                print('\n')
    except KeyboardInterrupt as error:
        logger.exception('CTRL+C interrupted.')
        sys.exit(2)

    # _thread = threading.Thread(target=vwapsystem.start())
    # _thread.start()
    # time.sleep(args.sleeptime)  # Sleep for 120 seconds before retrying.
