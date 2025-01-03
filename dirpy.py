import os
import time
import typing
import asyncio
import aiohttp
import argparse
import configparser
from bs4 import BeautifulSoup

# class PayloadModifiers(object):

class EventHandler(object):
    events = {
        'before_request': [],
        'mutate_paload': [],
        'on_response': [],
        'on_success': [],
        'on_failure': [],
        'on_err': [],
    }

    class event(object):
        def __init__(self, func: object=None, is_async:bool=False):
            if callable(func):
                self.func = func
                self.is_async = is_async
                self.callable = True
            else:
                self.callable = False

        async def call(self):
            if self.is_async:
                await asyncio.create_task(self.func())
            else:
                self.func()

        def __repr__(self):
            return f"<Event: {self.func.__name__}>"

    def add(self, event_name:str, function, is_async:bool=False):
        self.events[event_name].append(event(function, is_async))
 
    def call_events(self, event_name: str):
        [e.call() for e in self.events[event_name]]

class Target(object):
    def __init__(self, args):
        self.address = args.address
        self.r_timestamp = time.time()
        self.wait_time = args.wait
        self.lock = asyncio.Lock()
    def reset_timer(self):
        self.r_timestamp = time.time()

    def ready(self) -> bool:
        return (time.time() - self.r_timestamp) >= self.wait_time

class Dirpy(object):
    def __init__(self,args):
        self. args = args
        self.sem = asyncio.Semaphore(args.workers)
        self.payload_queue = asyncio.Queue()
        self.sessions = []

    def load_list(self, path:str) -> list[str]:
        if not os.path.exists(path):
            print("File path does not exist. Exiting...")
            exit()
        with open(path, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f.readlines() if not l.startswith('#')]

    async def run(self, queue = asyncio.Queue()):
        loop = asyncio.get_event_loop()
        target = Target(self.args)

        any(map(self.payload_queue.put_nowait, self.load_list(self.args.wordlist)))
        
        tasks = []

        for w in range(self.args.workers):
            task = asyncio.create_task(self.request_worker(target))

            tasks.append(task)

        await asyncio.gather(*tasks)
        # for s in self.sessions:
        #     await s.close()

    async def request_worker(self, target: object):
        async with aiohttp.ClientSession() as session:
            while self.payload_queue.qsize() > 0:
                while not target.ready():
                    await asyncio.sleep(target.wait_time / self.args.workers)
                
                try:
                    async with target.lock:
                        target.reset_timer()

                    payload = await self.payload_queue.get()
                    url = os.path.join(target.address, payload)
                    print(url)
                    async with session.get(url) as response:
                        if response.status == 200:
                            print(response)

                except aiohttp.client_exceptions.ServerDisconnectedError:
                    
                    pass
                except ValueError as e:
                    print(e)

                finally:
                    self.payload_queue.task_done()
    
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_type", type=str, help='Type of scan to run {fuzz, crawl, auth, subdomain, vhost}')
    parser.add_argument("address", type=str, help='domain or ip address to scan, i.e. https://example.com')
    parser.add_argument("--persist", type=bool, help='Maintain progress on scan')
    parser.add_argument("-t", "--workers", type=int, default=8, help='Max number of simultaneous requests to make')
    parser.add_argument("-c", "--cookies", type=str, help='Cookies to inlcude with requests')
    parser.add_argument("-s", "--sessions", type=int, default=1, help="Number of concurrent sessions to use.")
    parser.add_argument("-w", "--wordlist", type=str, help="Path to wordlist to use")
    parser.add_argument("-pr", "--prefix", type=str )
    parser.add_argument("--wait", type=float, default=0, help="Number of concurrent sessions to use.")
    args = parser.parse_args()

    dirpy = Dirpy(args)

    await dirpy.run()

if __name__=="__main__":    
    asyncio.run(main())