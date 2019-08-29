#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# ezIBpy: a Pythonic Client for Interactive Brokers API
# https://github.com/ranaroussi/ezibpy
#
# Copyright 2015 Ran Aroussi
#
# Licensed under the GNU Lesser General Public License, v3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.gnu.org/licenses/lgpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ezibpy
import time
from qtpylib import futures

# initialize ezIBpy
ibConn = ezibpy.ezIBpy()
ibConn.connect(clientId=3016, host="localhost", port=7496, account='DU1314277')

# subscribe to account/position updates
ibConn.requestPositionUpdates(subscribe=True)
ibConn.requestAccountUpdates(subscribe=True)
active_month = futures.get_active_contract("MES")
print('Active month', active_month)
# available variables (auto-updating)
print("Account Information")
#print(ibConn.account)

print("Positions")
print(ibConn.positions)

# create a contract
contract = ibConn.createFuturesContract("MES", exchange="GLOBEX", expiry="201909")
print('Contract', contract.__dict__)
# create an order
#order = ibConn.createOrder(quantity=5) # use price=X for LMT orders
# submit an order (returns order id)
#orderId = ibConn.placeOrder(contract, order)

# let order fill
#time.sleep(3)

# subscribe to account/position updates
ibConn.requestPositionUpdates(subscribe=False)
ibConn.requestAccountUpdates(subscribe=False)

# see the positions
print("Positions")
print(ibConn.positions)

# disconnect
ibConn.disconnect()
