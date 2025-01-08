import os
import sys
import math
import time
import shutil
import typing
import base64
import asyncio
import aiohttp
import argparse
import ipaddress
import configparser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote, unquote

def show_logo():
    logo=r"""
                                                .=-.-.               _ __                                                     
        =========================== _,..---._  /==/_ /.-.,.---.   .-`.' ,`.  ,--.-.  .-,--. =================================
       ========================== /==/,   -  \|==|, |/==/  `   \ /==/, -   \/==/- / /=/_ / =================================
      =========================== |==|   _   _\==|  |==|-, .=., |==| _ .=. |\==\, \/=/. / =================================
     ============================ |==|  .=.   |==|- |==|   '='  /==| , '=',| \==\  \/ -/ =================================
    ============================= |==|,|   | -|==| ,|==|- ,   .'|==|-  '..'   |==|  ,_/ =================================
   ============================== |==|  '='   /==|- |==|_  . ,'.|==|,  |      \==\-, / =================================
  =============================== |==|-,   _`//==/. /==/  /\ ,  )==/ - |      /==/._/ =================================
 ================================ `-.`.____.' `--`-``--`-`--`--'`--`---'      `--`-` =================================
 
"""
    i = 31
    for c in logo:
        
        print(f"{c}", end="\033[0m")
        i += 1
        if i > 36:
            i = 31

    print("--- https://github.com/sys-nyx/dirpy - License: GNU 3.0 - Have fun and please don't use for anyhthing illegal :P ---\n")

def print_results(response, dirpy):
    """
    Calculate width of terminal and then print a string containing the url and status of the 
    response passed into it.
    """
    columns, lines = shutil.get_terminal_size()
    r_str = str(response.url)
    r_str = r_str + ('.' * (columns - (len(str(response.url)) + len(str(response.status)))))
    r_str = r_str + str(response.status)
    print(r_str)

async def do_something(*args, **kwargs):
    # print('sleeping')
    await asyncio.sleep(1)

class PayloadMutators:
    """
    Class for providing simple methods for applying various forms of text encoding and transformations.

    Methods:
        mutator_map:    Return a dictionary containing function references(value) and their 
                        names(key).

        mutate_all:     Extract names from a comma seperated list and apply each associated 
                        function to a string

    """
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
        """
        Url encode a string and return it.
        """
        return quote(payload)

    def b64_encode(self, payload: str) -> str:
        """
        Base64 encode a string and return it.
        """
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
            """
            Call a function stored in the parent class. Function is asynchronous execute it as 
            asyncio task.
            """
            if self.callable:
                if self.is_async:
                    await asyncio.create_task(self.func(*args, **kwargs))
                else:
                    self.func(*args, **kwargs)

        def __repr__(self):
            return f"<Event: {self.func.__name__}>"

    def add(self, event_name:str, function, is_async:bool=False):
        """
        Takes a function and adds it to the event handler to be called when the specified event 
        is triggered.

        Args: 
            event_name:     Name of event to register function with.
            function:       A refernce to the function to be ran.
            is_async:       Boolean representing whether or not the function is asynchronous or 
                            not. Default is false.
        """
        self.events[event_name].append(self.event(function, is_async))
 
    async def call_events(self, event_name: str, *args, **kwargs):
        """
        Call all functions associated to a given event name within the self.events dictionary.

        Args:
            event_name:     String name of the event being triggered.
            args:           Packed positional arguments to be passed along to the functions being called.
            kwargs:         Packed keyword arguments to be passed along to the functions being called.
        """
        for e in self.events[event_name]:
            await e.call(*args, **kwargs)

class Target:
    """
    Class for containing data and methods regarding the target that is accessible to worker processses.

    Args: 

        address:        Ip address or url for target.

        wait_time:      Amount of time to wait in between requests to target.

    Attributes:

        r_timestamp:    A unix timestamp of the last request sent to target.

        lock:           Asyncio lock that should be aquired before modifying any attibutes 
                        from within a worker process.

    Methods:

        reset_timer:    Overwrite r_timestamp with a new timestamp. Should be called along 
                        with every new request made to the target to insure timeoouts work
                        properly.
    
        ready:          Determine if time since last request is greater than the value 
                        stored in wait_time attribute. Used to determine if target is on
                        timeout or not.
    
        is_valid_ip:    Determine if ip address provided is a valid ipv4 or ipv6 address.

        is_valid_url:   Determine if url provided is a valid.
    """

    def __init__(self, args):
        self.address = args.address
        self.r_timestamp = time.time()
        self.wait_time = args.wait
        self.lock = asyncio.Lock()
        self.req_count = 0

    def reset_timer(self):
        """
        Set self.r_timestamp to a current timestamp.
        """
        self.r_timestamp = time.time()

    def ready(self) -> bool:
        """
        Determine if time since last request is greater than the value stored in wait_time 
        attribute. Used to determine if target is on timeout or not.
        """
        return (time.time() - self.r_timestamp) >= self.wait_time

    def is_valid_url(self, url: str) -> bool:
        """
        Determine if a url is valid by trying to create a url object with the urlib library. If 
        it fails a value of False will be returned.
        """
        try: 
            url_parser = urlparse.parser(url, strict_parsing=True)
        except ValueError:
            return False
        return True

    def is_valid_ip(self, ip: str) -> bool:
        """
        Determine if an ip address is valid by attempting to create a ipaddress object with it. If
        it fails, a False value will be returned.
        """
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
        self.event_handler = EventHandler()
    def load_list(self, path:str) -> list[str]:
        if not os.path.exists(path):
            print("File path does not exist. Exiting...")
            sys.exit()
        with open(path, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f.readlines() if not l.startswith('#')]

    async def run(self):
        loop = asyncio.get_event_loop()
        target = Target(self.args)
        proxy = None
        proxies = None
        any(map(self.payload_queue.put_nowait, self.load_list(self.args.wordlist)))
        
        tasks = []

        self.event_handler.add('on_response', print_results)

        if self.args.session_proxies:
            proxies = load_list(self.args.session_proxies)


        for w in range(self.args.sessions):
            if proxies:
                proxy = proxies[w]
    
            task = asyncio.create_task(self.session_handler(target, proxy))

            tasks.append(task)

        await asyncio.gather(*tasks)

    async def request_worker(self, target, session):
        err = False
        while self.payload_queue.qsize() > 0:
            while not target.ready():
                await asyncio.sleep(target.wait_time / self.args.workers)
            
            try:
                if target.wait_time > 0 or target.wait_time == 0:
                    async with target.lock:
                        target.reset_timer()
                        target.req_count += 1
                        if target.req_count % 100 == 0:
                            print(target.req_count)
                payload = await self.payload_queue.get()
                payload = PayloadMutators().mutate_all(payload, self.args.mutate)
        
                url = os.path.join(target.address, payload)
                await self.event_handler.call_events('before_request', payload)
                async with session.request(self.args.method, url) as response:
                    await self.event_handler.call_events('on_response', response, self)
                    if response.status == 200:
                        await self.event_handler.call_events('on_success', response, self)
                    else:
                        await self.event_handler.call_events('on_failure', response, self)

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
                    await self.event_handler.call_events('on_err', response)
                self.payload_queue.task_done()


    async def session_handler(self, target: object, proxy: str):
        """
        Create a session, which iwll in turn spawn worker process. Each worker process utilizes 
        session attriubutes, such as user-agents, that are created within this function.

        Args:
            target:     Target object containing a valid url or ip address.

            proxy:      Set a proxy as the sessions default.
        """
        data = {}
        headers = {}
        if self.args.data:
            data = get_args_data(self.args.data)
        if self.args.headers:
            headers = get_args_headers(self.args.headers)
        if self.args.user_agent:
            if self.args.user_agent == "rand":
                headers['User-Agent'] = get_rand_ua()
            else: 
                headers['User-Agent'] = self.args.user_agent

        async with aiohttp.ClientSession(headers=headers, proxy=proxy) as session:
            tasks = []

            for w in range(math.floor(self.args.workers / self.args.sessions)):
                task = asyncio.create_task(self.request_worker(target, session))
                tasks.append(task)

            await asyncio.gather(*tasks)

def get_args_data(args_str: str) -> dict:
    return
def get_args_headers(args_str: str) -> dict:
    return

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_type", type=str, help='Type of scan to run {fuzz, crawl, auth, subdomain, vhost}')
    parser.add_argument("address", type=str, help='domain or ip address to scan, i.e. https://example.com')
    parser.add_argument("--persist", type=bool, help='Maintain progress on scan.')
    parser.add_argument("-t", "--workers", type=int, default=8, help='Max number of simultaneous request loops to run.')
    parser.add_argument("-c", "--cookies", type=str, help='Cookies to include with requests.')
    parser.add_argument("-s", "--sessions", type=int, default=1, help="Number of concurrent sessions to use.")
    parser.add_argument("-w", "--wordlist", type=str, help="Path to wordlist to use.")
    parser.add_argument("-pr", "--prefix", type=str, help="Append a string to the begginning of every payload.")
    parser.add_argument("-su", "--suffix", type=str, help="Append a string to the end of every payload. If an extension is also used, the extension is added last.")
    parser.add_argument("--wait", type=float, default=0, help="Number of concurrent sessions to use.")
    parser.add_argument("--mutate", type=str, default='', help="apply mutations to payload.")
    parser.add_argument("-H", "--headers", type=str, help="Add headers to each request to be made. Seperate each header to add with a comma. I.e. 'Host: example.com'")
    parser.add_argument("-D", "--data", type=str, help="Add custom data to each body.")
    parser.add_argument("-X", "--method", default="GET", type=str, help="Request method to use {GET, POST, HEAD, PUT, DELETE, OPTIONS}")
    parser.add_argument("-ua", "--user-agent", type=str, help="Specify a custom user agent to use.")
    parser.add_argument("-sp", "--session-proxies", type=str, help="Path a text file containing a list of proxies to use (One per generated session).")
    parser.add_argument("--quiet", help="Do not print messages to terminal.")
    parser.add_argument("--no-intro", default=False, action="store_true", help="Do not show the intro message at startup.")
    args = parser.parse_args()
    if not args.no_intro:
        show_logo()

    dirpy = Dirpy(args)

    await dirpy.run()

if __name__=="__main__":    
    asyncio.run(main())
