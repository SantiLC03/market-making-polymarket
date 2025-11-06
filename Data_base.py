

import requests
import pandas as pd

from py_clob_client.clob_types import TradeParams

from py_clob_client.clob_types import TradeParams

resp = client.get_trades(
    TradeParams(
        asset_id="66281600716773880802753015201294956591448454218578699327801428058257011939378"
    )
)
print(resp)



