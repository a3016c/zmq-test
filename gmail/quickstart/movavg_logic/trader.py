import ezibpy
import time
from qtpylib import futures
import zmq_constants

constants = zmq_constants.constants()
size = constants.standard_size

def ibpy(size, contractString):
    """
    Method to place orders
    :param size: Size of order, -ve if Shorting, +ve if Buying
    :param contractString: String format for Contract name , ex: MES, MNQ, NQ
    :return: bool
    """
    global constants

    try:
        ibConn = ezibpy.ezIBpy()
        exchange = 'GLOBEX'
        ibConn.connect(host=constants.host, port=constants.port,
                       account=constants.account)

        # subscribe to account/position updates
        ibConn.requestPositionUpdates(subscribe=True)
        ibConn.requestPositionUpdates(subscribe=False)
        # ibConn.requestAccountUpdates(subscribe=True)
        # time.sleep(3)

        active_month = futures.get_active_contract(contractString)
        if contractString in ['CL', 'QM', 'GC']:
            exchange = 'NYMEX'
        contract = ibConn.createFuturesContract(contractString,
                                                exchange=exchange,
                                                expiry=constants.expiry)
        # Get symbol_string
        # e.g. sym value GCQ2019_FUT
        symbol_string = ibConn.contractString(contract)
        new_size = size

        if check_active_position(ibConn, symbol_string):
            position_size = get_position_size(ibConn, symbol_string)
            new_size = - position_size * 2

        order = ibConn.createOrder(quantity=new_size)
        orderId = ibConn.placeOrder(contract, order)
        time.sleep(3)

        # subscribe to account/position updates
        # ibConn.requestPositionUpdates(subscribe=False)
        # ibConn.requestAccountUpdates(subscribe=False)

        # disconnect
        ibConn.disconnect()
        time.sleep(2)
    except Exception as e:
        print('Exception occurred.')
        print(e)
        return False

    return True




def check_active_position(ibConn, symbol_string):

    for sym, value in ibConn.positions.items():
        # e.g. sym value GCQ2019_FUT
        # print(sym, '****', value['position'])
        if symbol_string == sym and value['position'] != 0:
            print('Open Positions for %s : %s' % (sym, value['position']))
            return True
    print('No active positions for %s' % symbol_string)
    return False

def get_position_size(ibConn, symbol_string):
    for sym, value in ibConn.positions.items():
        if symbol_string == sym and value['position'] != 0:
            return int(value['position'])
        else:
            return 0
