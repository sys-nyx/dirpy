import os
import sys
import time
import typing
import base64
import asyncio
import aiohttp
import argparse
import ipaddress
import configparser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote, unquote


def print_something(*args, **kwargs):
    print(*args)

async def do_something(*args):
    # print('sleeping')
    await asyncio.sleep(1)

class PayloadMutators:
    def mutator_map(self):
        return {
            'url': self.url_encode,
            'b64': self.b64_encode
        }

    def mutate_all(self, payload: str, mutators:list[str]):
        if mutators:
            mutators = mutators.split(',')
        
            for m in mutators:
                payload =  self.mutator_map()[m](payload)
        return payload

    def url_encode(self, payload: str) -> str:
        return quote(payload)

    def b64_encode(self, payload: str) -> str:

        return base64.b64encode(payload.encode('utf-8')).decode('utf-8')

class EventHandler(object):
    """
    Class for containing methods which can be used to trigger groups scripts.

    Attributes:
        events:         A Dictionary containing containing event names(keys) and functions
                        to call with each event (list), I.e.  {
                                                            'on_response': [
                                                                            do_something, 
                                                                            do_another_thing
                                                                            ]
                                                            }

    Sub-Classes:
        event:          Class which stores a reference to a function and provides a simple 
                        interface for calling it.

                        Attributes:
                            func: function:     Stores a reference to a function.
                            callable: bool:     Stores True if function is callable. Otherwise 
                                                it is False.

                            is_async: bool:     True if function needs to called as asyncio 
                                                task and awaited. Otherwise it is False.

    Methods:
        add:            Associate a function with a specific event name to be called when the 
                        event is triggered. 

        call_events:    Call all functions associated to the event specified in its arguments.

    """
    events = {
        'before_request': [],
        'mutate_paload': [],
        'on_response': [],
        'on_success': [],
        'on_failure': [],
        'on_timeout': [],
        'on_err': [],
    }

    class event:
        def __init__(self, func: object=None, is_async:bool=False):
            """
            This is a subclass of the event Handler. It is meant to hold a reference to a function
            and provide a simple interface for calling it, asyncronsously or not, from within the 
            call_events method. 
            
            Args:
                func:       A function.
                is_async:   Boolean specifying if function is asynchronous or not. If it is, it can 
                            be called and awaited as an asyncio task.
            Methods: 
                call:       Check if function is callable and asynchronous or not using it's is_async
                            attribute and then call using the appropriate methods.
            """
            if callable(func):
                self.func = func
                self.is_async = is_async
                self.callable = True
            else:
                self.callable = False

        async def call(self, *args, **kwargs):
            if self.callable:
                if self.is_async:
                    await asyncio.create_task(self.func(*args,**kwargs))
                else:
                    self.func(args, kwargs)

        def __repr__(self):
            return f"<Event: {self.func.__name__}>"

    def add(self, event_name:str, function, is_async:bool=False):
        self.events[event_name].append(self.event(function, is_async))
 
    async def call_events(self, event_name: str, *args):
        for e in self.events[event_name]:
            await e.call(args)

class Target:
    """
    Class for containing data and methods regarding the target that is accessible to worker processses.

    Args: 
        address: str -> Ip address or url for target.
        wait_time: float -> Amount of time to wait in between requests to target.

    Attributes:
        r_timestamp:    A unix timestamp of last request sent to target.
        lock:           Asyncio lock that should be aquired before modifying any attibutes 
                        from within a worker process.

    Methods:
        reset_timer:    Overwrite r_timestamp with a new timestamp. Should be called along 
                        with every new request made to the target to insure timeoouts work
                        properly.
    
        ready -> bool:  Determine if time since last request is greater than the value 
                        stored in wait_time attribute. Used to determine if target is on
                        timeout or not.
    
        is_valid_ip -> bool: Determine if ip address provided is a valid ipv4 or ipv6 address.
        is_valid_url -> bool: Determine if url provided is a valid.
    """
    def __init__(self, args):
        self.address = args.address
        self.r_timestamp = time.time()
        self.wait_time = args.wait
        self.lock = asyncio.Lock()
        
    def reset_timer(self):
        self.r_timestamp = time.time()

    def ready(self) -> bool:
        return (time.time() - self.r_timestamp) >= self.wait_time


    def is_valid_url(self, url: str) -> bool:
        try: 
            url_parser = urlparse.parser(url, strict_parsing=True)
        except ValueError:
            return False
        return True

    def is_valid_ip(self, ip: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return True

class Dirpy:
    def __init__(self,args):
        self. args = args
        self.sem = asyncio.Semaphore(args.workers)
        self.payload_queue = asyncio.Queue()
        self.sessions = []

    def load_list(self, path:str) -> list[str]:
        if not os.path.exists(path):
            print("File path does not exist. Exiting...")
            sys.exit()
        with open(path, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f.readlines() if not l.startswith('#')]

    async def run(self):
        loop = asyncio.get_event_loop()
        target = Target(self.args)

        any(map(self.payload_queue.put_nowait, self.load_list(self.args.wordlist)))
        
        tasks = []

        events = EventHandler()
        events.add('on_response', do_something, is_async=True)
        events.add('on_response', print_something)
        for w in range(self.args.workers):
            task = asyncio.create_task(self.session_handler(target, events))

            tasks.append(task)

        await asyncio.gather(*tasks)
        # for s in self.sessions:
        #     await s.close()

    async def session_handler(self, target: object, event_handler: object):
        async with aiohttp.ClientSession() as session:
            err = False
            while self.payload_queue.qsize() > 0:
                while not target.ready():
                    await asyncio.sleep(target.wait_time / self.args.workers)
                
                try:
                    if target.wait_time > 0:
                        async with target.lock:
                            target.reset_timer()

                    payload = await self.payload_queue.get()

                    payload = PayloadMutators().mutate_all(payload, self.args.mutate)
        
                    url = os.path.join(target.address, payload)
                    await event_handler.call_events('before_request', payload)
                    async with session.get(url) as response:
                        await event_handler.call_events('on_response', response)
                        if response.status == 200:
                            await event_handler.call_events('on_success', response)
                        else:
                            await event_handler.call_events('on_failure', response)
                except aiohttp.client_exceptions.ServerDisconnectedError as e:
                    print(e)
                    err = True
                except aiohttp.client_exceptions.ClientConnectorError as e:
                    print(e)
                    err = True
                except ValueError as e:
                    print(e)
                    err = True
                finally:
                    if err:
                        await event_handler.call_events('on_err', response)
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
    parser.add_argument("--mutate", type=str, default='', help="apply mutations to payload")
    args = parser.parse_args()

    dirpy = Dirpy(args)

    await dirpy.run()

if __name__=="__main__":    
    asyncio.run(main())
