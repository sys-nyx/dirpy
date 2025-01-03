import os
import time
import asyncio
import aiohttp
import argparse
import configparser
from bs4 import BeautifulSoup

class Target(object):
    def __init__(self, args):
        self.address = args.address
        self.last_request_timestamp = time.time()
        self.timeout = args.timeout
    def last_request_time(self):
        pass

    def ready(self, timeout: float, time_since_last_request: float) -> bool:
        return (time_since_last_request + timeout) >= time.time()

class Dirpy(object):
    def __init__(self, *args, **kwargs):
        self. args = arg
        self.sem = asyncio.Semaphore(args.workers)
        self.url_queue = asyncio.Queue()
        self.sessions = []

    def load_list(self, path:str) -> list[str]:
        if not os.path.exists(path):
            print("File path does not exist. Exiting...")
            exit()

        with open(path, 'r', encoding='utf-8') as f:
            
            
            return f.readlines().strip()


    async def main_loop(queue = asyncio.Queue()):
        [self.queue.put_nowait(line) for line in self.load_list(self.args.wordlist)]
            


        for i in range(self.args.sessions):
            session = aiohttp.ClientSession()
            
        with aiohttp.ClientSession() as session:
            while queue.qsize() > 0:
                url = await self.url_queue.get()
                response = await fetch(url)
                results = parse_response(response)
                f = process_results(results)



    def request_worker(self, session: object, target: object):
        async with session:
            while not target.ready():
                asyncio.sleep(target.timeout / self.args.workers)
            
            if target.ready():
                response = await session.get(target.address)


    async def run(self):


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_type", type=str, help='Type of scan to run.(fuzz, crawl, auth)')
    parser.add_argument("address", type=str, help='domain or ip address to scan, i.e. https://example.com')
    parser.add_argument("--persist", type=bool, help='Maintain progress on scan')
    parser.add_argument("-w", "--workers", type=int, help='Max number of simultaneous requests to make')
    parser.add_argument("-c", "--cookies", type=str, help='Cookies to inlcude with requests')
    parser.add_argument("-s", "--sessions", tpye=int, help="Number of concurrent sessions to use.")
    args = parser.parse_args()

    dirpy = Dirpy(args)

    await dirpy.run()

if __name__=="__main__":    
    asyncio.run(main())