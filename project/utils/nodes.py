import concurrent.futures,inspect, requests,config

class apiException(Exception):
    pass

def get_resp(url: str) -> requests.models.Response:
    
    resp = requests.get(url,timeout=5)
    resp.raise_for_status()
    if resp.json().get("error"):
        raise apiException(resp.json().get("error"))
    return resp

def build_query(args: dict) -> str:
        args.pop("endpoint")
        args.pop("url")
        args.pop("self")
        query = None
        for arg in args:
            #print(arg)
            if args.get(arg) is not None:
                if query is None:
                    query = f"{arg}={args.get(arg)}"
                else:
                    query += f"&{arg}={args.get(arg)}"
        return query

class History:
    def __init__(
        self,
        api_version="v1",
        server="https://wax.greymass.com",
    ):
        self.limit = 100
        self.api_version = api_version 
        self.server = server
        self.url_base = f"{self.server}/{self.api_version}/history"
        self.session = requests.Session()
    
    def get_actions(
        self,
        account_name: str = 'm.federation',
        pos: int = None,
        offset: int = 100,
        sort: str = "asc",
        start: str ="2020-12-17T15:30:51.346Z"
    ) -> requests.models.Response:
        endpoint = inspect.currentframe().f_code.co_name
        url = f"{self.url_base}/{endpoint}"
        data = {
            'account_name':account_name,
            'pos':pos,
            'offset':offset,
            "sort": sort,
            "after":start
        }
        # print(url)
        return self.session.post(f"{url}",json=data)

class Hyperion:
    def __init__(
        self,
        api_version="v2",
        server="api.waxsweden.org",
    ):
        self.limit = 100
        self.api_version = api_version 
        self.server = server
        self.url_base = f"https://{self.server}/{self.api_version}/history"

    def get_mines(
        self,
        skip: int = None,
        after: int = None,
        serv: str = 'https://api.waxsweden.org',
    ) -> requests.models.Response:
        url = f"{serv}/v2/history/"
        
        return get_resp(f'{url}get_actions?act.name=logmine&limit=100&sort=asc&after={after}&skip={skip}')
        

class WAXMonitor:
    def __init__(
        self,
        server="waxmonitor.cmstats.net",
    ):
        self.limit = 100
        self.server = server
        self.url_base = f"http://{self.server}/api"
        
        self.session = requests.Session()
    
    def endpoints(
        self,
        type: int = None,
    ) -> requests.models.Response:
        endpoint = "endpoints"
        url = f"{self.url_base}/{endpoint}"
        #args = locals()
        #print(f"{url
        args = locals()
        query = build_query(args)
        if query is None:
            raise Exception("Must provide at least one query parameter")
        return self.session.get(f"{url}?{query}")

class AH:
    def __init__(
        self,
        api_version="v1",
        server="https://aa-wax-public1.neftyblocks.com",
    ):
        self.limit = 100
        self.api_version = api_version  # use v2 apis unless explicitely overriden
        self.server = server
        self.url_base = f"{self.server}/atomicassets/{self.api_version}"
        self.session = requests.Session()
    
    def get_resp_ah(self,url: str) -> requests.models.Response:
    
        resp = self.session.get(url,timeout=15)
        resp.raise_for_status()
        return resp.json()

    
    
    def templates(
        self,
        collection_name: str = "centurytrain",
        schema_name: str = None,
        page: int = None,
        limit: int = 1000,
        after: int = None,
        sort: str = "created",
        order: str = "asc",
    ) -> requests.models.Response:
        endpoint = inspect.currentframe().f_code.co_name
        url = f"{self.url_base}/{endpoint}"
        args = locals()
        query = build_query(args)
        if query is None:
            raise Exception("Must provide at least one query parameter")
        #print(f"{url}?{query}")
        return self.get_resp_ah(f"{url}?{query}")

    def assets(
        self,
        collection_name: str = "centurytrain",
        schema_name: str = None,
        page: int = None,
        ids: str = None,
        limit: int = 1000,
        after: int = None,
        sort: str = "minted",
        order: str = "asc",
    ) -> requests.models.Response:
        endpoint = inspect.currentframe().f_code.co_name
        url = f"{self.url_base}/{endpoint}"
        args = locals()
        query = build_query(args)
        if query is None:
            raise Exception("Must provide at least one query parameter")
        # print(f"{url}?{query}")
        return self.get_resp_ah(f"{url}?{query}")


def pick_best_waxnode(type,cutoff:int=8):
    
    resp = WAXMonitor().endpoints(type=type).json()
    out=[]
    for node in resp:
        if node["weight"] > cutoff:
            out.append(node["node_url"])
    if len(out) == 0:
        return ["https://aa-wax-public1.neftyblocks.com"]
    return out



