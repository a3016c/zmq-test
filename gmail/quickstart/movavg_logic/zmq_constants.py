class constants():
    def __init__(self):
        self.zmq_sell_filter = 'SELL'
        self.zmq_buy_filter = 'BUY'
        self.trade_filter = 'TRADE'
        self.msg_scope = 'Alert:'
        self.zmq_events_addr = 'tcp://127.0.0.1:8008'
        self.BUY_SEARCH = 'added to 2Mov2Lines_buy'
        self.SELL_SEARCH = 'added to 2Mov2Lines_Sell'
        self.unread_message = 'UNREAD'
        self.client_id = 3016
        self.standard_size = 1
        self.host = 'localhost'
        self.account = 'DU1314277'
        self.port = 7496
        self.allowed_contracts = ['/ES', '/NQ', '/YM', '/RTY']#, '/CL', '/QM', '/6E',
                                  #'/6A']
        self.expiry = 201909
        self.tda_ib_pair = {'/MES':'MES',
                            '/ES':'ES',
                            '/NQ':'NQ',
                            '/MNQ':'MNQ'}
        self.exchange_combination = {'NQ':'GLOBEX','ES':'GLOBEX','YM':'GLOBEX','RTY':'GLOBEX'}
