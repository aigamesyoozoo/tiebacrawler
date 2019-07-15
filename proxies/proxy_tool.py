from itertools import cycle
import asyncio
from proxybroker import Broker
import time

async def retrieve(proxies):
    while True:
        proxy = await proxies.get()
        if proxy is None: break
        # print(proxy)

proxies = asyncio.Queue()
broker = Broker(proxies)
tasks = asyncio.gather(
    broker.find(types=['HTTP', 'HTTPS'], limit=10),
    retrieve(proxies))

loop = asyncio.get_event_loop()
loop.run_until_complete(tasks)

proxies = list(map(lambda x: ':'.join(map(str, x)), list(broker.unique_proxies.keys())))
# construct proxy pool and rotate
# proxy_pool = cycle(list(broker.unique_proxies.keys()))

proxy_pool = cycle(proxies)
#with open('proxies.txt', 'w') as f:
#    for proxy in proxies:
#        f.write(proxy+'\n')
#time.sleep(5)

for i in range(300):
    print(next(proxy_pool))
