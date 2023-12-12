import re
import sys
import logging as lg

from threading import Thread
from pathlib import Path

import requests

SEGMENT_SIZE = 10
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Cookie": "_ga=GA1.1.817644579.1702294121; cf_clearance=wj8RP08EF_PelxOQn6074ysrrk35s.yqTZopq5udSRo-1702294121-0-1-87fe4013.9f377095.be00799f-0.2.1702294121; __cf_bm=OZ2vopqbejAHyajAgGcK0sGGqk1_7DtOJHmP7FKk6I8-1702299562-1-ARm8Jt0BAo7I+U2V3wQhy2jgJUaD98TZ9jO8Yb2cFviNwj34D+IXMnlzagAK0Ov3AVmbTS3/DeYncBn5sgUY0uE=; __gads=ID=8d6926ef1f06fed9:T=1702294121:RT=1702299563:S=ALNI_Ma8vFw-LVwRVnqoh9yPA9KUfPZu5w; __gpi=UID=00000ca983cd3fde:T=1702294121:RT=1702299563:S=ALNI_Mb0_QlRUiUhe4tYYKIKW_ZLOq5Z-A; MVN_SESSION=eyJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7InVpZCI6IjZmMWM1OTcxLTk4MTgtMTFlZS1iYmFlLTQ1N2Y4YzJlNGM3YiJ9LCJleHAiOjE3MzM4MzU1NjYsIm5iZiI6MTcwMjI5OTU2NiwiaWF0IjoxNzAyMjk5NTY2fQ.a-gZkOiDph5ZbwuxJEbxmhdI7mX9aGYxIBZlKBrM_tM; _ga_3WZHLSR928=GS1.1.1702299562.2.1.1702299567.0.0.0",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "Windows",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
}


def display_help():
    print(
        """
        Usage:
            python3 mvn_resolve.py <artifact:package> <path_to_pom.xml>
            
        Example : 
            python3 mvn_resolve.py org.yaml:snakeyaml ./pom.xml
        """
    )
    sys.exit()


# Check for parameter validity
if len(sys.argv) < 3:
    display_help()

try:
    gid, pkg = sys.argv[1].split(":")
    path = Path(sys.argv[2]).resolve()
    if not path.exists():
        print(f"\n'{path}' does not exist!")
        raise FileNotFoundError
except (ValueError, FileNotFoundError):
    display_help()
except Exception:
    print("An unhandled error occured!")

# Configure python logger
lg.basicConfig(filename="mvn_resolve.log", level=lg.INFO)
lg.info(f"Reading pom.xml from '{path.parent}'")

base_url = f"https://mvnrepository.com/artifact/{gid}/{pkg}/usages?p="

# Define upper and lower limit for segments
start, end = 1, SEGMENT_SIZE + 1

# Variable to keep tract of access denied event
ad_count = 0

groupids = set()
threads = list()

# Compile regex for scraping response and pom.xml
re_text = re.compile(
    r'.*?<p class="im-subtitle"><a.*?>(.*?)</a>.*?<a.*?>(.*?)</a>.*?</p>',
    re.DOTALL,
)
re_pom = re.compile(
    r".*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>",
    re.DOTALL,
)


# Subclass of Thread to handle requests
class RequestThread(Thread):
    def __init__(self, start, end):
        self.s, self.e = start, end
        super().__init__(target=self.request_handler)

    def request_handler(self):
        while self.s < self.e:
            self.sc, self.rt = self.send_req()
            if self.sc == 403:
                lg.warning(f"Access denied on page {self.s}, retrying")
                continue
            elif self.sc == 404:
                lg.error(f"Page {self.s} not found, exiting")
                break
            elif self.sc == 200:
                lg.info(f"Recieved response from page {self.s}")
                self.s += 1
            else:
                lg.error(4, f"Unhandled status {
                         self.sc} on page {self.s}, retrying")
                continue
            self.find_and_save()

    def send_req(self):
        full_url = f"{base_url}{self.s}"
        resp = requests.get(full_url, headers=HEADERS, verify="cacert.pem")
        return resp.status_code, resp.text

    def find_and_save(self):
        text = self.rt
        m = re_text.findall(text)
        for i in m:
            groupids.add(f"{i[0]} {i[1]}")


def parse_pom():
    groups = set()  # holds all group and artifact id in pom.xml
    pom = open(path, "r")  # Skipping error checking as already checked path
    text = pom.read()
    for i in re_pom.findall(text):
        groups.add(f"{i[0]} {i[1]}")
    pom.close()
    return groups


while True:
    th = RequestThread(start, end)
    sc, rt = th.send_req()
    if sc == 404:
        for i in threads:
            i.join()
        lg.info("All threads exited...")
        break
    elif sc == 403:
        if ad_count > 5:
            print("Connection refused, try again later...")
            break
        ad_count += 1
        continue
    else:
        start = end
        end += SEGMENT_SIZE
    th.daemon = True
    th.start()
    threads.append(th)

for i in groupids.intersection(parse_pom()):
    p, g = i.split()
    print(f"\n{p} >> {g}")
    print("  |\n  +--", end="")
    print(f"https://mvnrepository.com/artifact/{p}/{g}")
