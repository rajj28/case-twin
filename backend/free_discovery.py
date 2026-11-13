"""Source-backed facility search without paid search APIs or generated locations."""
import functools
import ipaddress
import json
import math
import re
import socket
import threading
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "CaseTwin-Research-Demo/1.0 (https://github.com/rajj28/case-twin)"}
_geocode_lock = threading.Lock()
_last_geocode = 0.0

@functools.lru_cache(maxsize=128)
def locate(location):
    global _last_geocode
    parts = (location or "").split(",")
    if len(parts) == 2:
        try:
            lat, lng = map(float, parts)
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng
        except ValueError:
            pass
    if not location:
        raise ValueError("Enter a city or latitude,longitude to search hospitals.")
    with _geocode_lock:
        time.sleep(max(0, 1.05 - (time.monotonic() - _last_geocode)))
        response = requests.get("https://nominatim.openstreetmap.org/search", params={"q": location, "format": "json", "limit": 1}, headers=HEADERS, timeout=15)
        _last_geocode = time.monotonic()
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError("Location was not found. Try a city name or latitude,longitude.")
    return float(results[0]["lat"]), float(results[0]["lon"])

def distance_km(a, b, c, d):
    lat1, lat2 = math.radians(a), math.radians(c)
    value = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(d-b)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(value)))

@functools.lru_cache(maxsize=64)
def _nearby(lat, lng, radius, cache_period):
    global _last_geocode
    delta_lat = radius / 111320
    delta_lng = delta_lat / max(.15, math.cos(math.radians(lat)))
    viewbox = f"{max(-180,lng-delta_lng)},{min(89.9,lat+delta_lat)},{min(180,lng+delta_lng)},{max(-89.9,lat-delta_lat)}"
    with _geocode_lock:
        time.sleep(max(0, 1.05 - (time.monotonic() - _last_geocode)))
        response = requests.get("https://nominatim.openstreetmap.org/search", params={"q":"hospital","viewbox":viewbox,"bounded":1,"format":"jsonv2","limit":15,"extratags":1}, headers=HEADERS, timeout=20)
        _last_geocode = time.monotonic()
    response.raise_for_status()
    # A directory of best matches, not an exhaustive inventory of the area.
    return [{"type":row["osm_type"],"id":row["osm_id"],"lat":float(row["lat"]),"lon":float(row["lon"]),"tags":{"name":row.get("name") or row.get("display_name","").split(",")[0],**(row.get("extratags") or {})}} for row in response.json() if row.get("type")=="hospital"]

def find_hospitals(diagnosis, location, equipment=None, max_travel=None, max_distance=None):
    lat, lng = locate(location)
    miles = float(max_distance or 50)
    radius = max(1000, min(100000, round(miles * 1609.344)))
    elements = _nearby(round(lat, 5), round(lng, 5), radius, int(time.time() // 3600))
    ranked = []
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if not name:
            continue
        center = element.get("center", element)
        x, y = center.get("lat"), center.get("lon")
        if x is None or y is None:
            continue
        distance = distance_km(lat, lng, x, y)
        if distance > miles * 1.609344:
            continue
        source = f'https://www.openstreetmap.org/{element["type"]}/{element["id"]}'
        specialty = tags.get("healthcare:speciality", "").replace(";", ", ")
        reason = f"Hospital listed in OpenStreetMap, {distance:.1f} km straight-line distance from the search location."
        if specialty:
            reason += " Listed specialties: " + specialty + "."
        if equipment:
            reason += " Requested equipment/capabilities require confirmation with the facility."
        url = tags.get("website") or tags.get("contact:website") or source
        ranked.append((distance, {"name": name, "url": url, "capability": "Unverified", "travel": "Not available", "reason": reason, "lat": x, "lng": y, "source_url": source, "phone": tags.get("phone", tags.get("contact:phone", "")), "verified_capabilities": [], "distance_km": round(distance, 2)}))
    ranked.sort(key=lambda item: item[0])
    centers = []
    seen = set()
    for _, center in ranked:
        if center["name"].casefold() in seen:
            continue
        seen.add(center["name"].casefold())
        try:
            response = requests.get(f'https://router.project-osrm.org/route/v1/driving/{lng},{lat};{center["lng"]},{center["lat"]}', params={"overview": "false"}, headers=HEADERS, timeout=8)
            data = response.json() if response.ok else {}
            if data.get("routes"):
                seconds = float(data["routes"][0]["duration"])
                if max_travel and seconds > float(max_travel) * 3600:
                    continue
                minutes = max(1, round(seconds / 60))
                center["travel"] = f"{minutes//60}h {minutes%60}m" if minutes >= 60 else f"{minutes}m"
        except (requests.RequestException, ValueError, KeyError):
            pass
        centers.append(center)
        if len(centers) == 6:
            break
    return {"centers": centers, "user_location": {"lat": lat, "lng": lng}, "source": "OpenStreetMap contributors (ODbL)", "capability_verification": "Required capabilities are not verified by this directory search."}

def _public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Provide a public hospital website URL.")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or not all(ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
        raise ValueError("Only public hospital websites can be inspected.")
    return url

def _schema_physicians(url, diagnosis, hospital_name, location=""):
    current = _public_url(url)
    for _ in range(4):
        response = requests.get(current, headers=HEADERS, timeout=15, stream=True, allow_redirects=False)
        if response.is_redirect:
            current = _public_url(urljoin(current, response.headers.get("Location", "")))
            response.close()
            continue
        response.raise_for_status()
        if "text/html" not in response.headers.get("Content-Type", ""):
            response.close()
            return {"specialists": [], "source_url": current, "message": "The hospital URL did not return an HTML directory."}
        chunks=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size > 2_000_000:break
            chunks.append(chunk)
        response.close()
        soup=BeautifulSoup(b"".join(chunks),"html.parser")
        people=[]
        def visit(value):
            if isinstance(value,list):
                for item in value:visit(item)
            elif isinstance(value,dict):
                kinds=value.get("@type",[])
                kinds=[kinds] if isinstance(kinds,str) else kinds
                if any(k in ("Physician","Person") for k in kinds) and value.get("name"):
                    if "Physician" in kinds or value.get("medicalSpecialty") or re.match(r"Dr\.?\s",value["name"]):
                        specialty=value.get("medicalSpecialty") or "Not documented"
                        if not isinstance(specialty,str):specialty="Not documented"
                        people.append({"name":value["name"],"specialty":specialty,"credentials":value.get("honorificSuffix", "Not documented"),"context":f"Listed in structured data on {hospital_name or 'the hospital website'}. Confirm specialty and availability directly.","url":urljoin(current,value.get("url") or current),"phone":value.get("telephone","")})
                for key,item in value.items():
                    if isinstance(item,(list,dict)):visit(item)
        for script in soup.find_all("script",type="application/ld+json"):
            try:visit(json.loads(script.string or script.get_text()))
            except (json.JSONDecodeError,TypeError):continue
        unique={person["name"]:person for person in people}
        return {"specialists":list(unique.values())[:5],"source_url":current,"message":"Only named clinicians found in the website's structured data are included." if unique else "No named clinicians were found in this page's structured data. Open the hospital's physician directory directly."}
    raise ValueError("Hospital website redirected too many times.")


def _same_system(candidate, origin):
    host=(urlparse(candidate).hostname or "").lower()
    base=(urlparse(origin).hostname or "").lower().removeprefix("www.")
    return bool(base) and (host==base or host.endswith("."+base))

@functools.lru_cache(maxsize=64)
def _reader_physicians(url, hospital_name, cache_period):
    """Read at most two public pages and retain only explicit named profile links."""
    queue=[url];visited=set();people=[]
    for _ in range(2):
        if not queue:break
        target=_public_url(queue.pop(0))
        if target in visited:continue
        visited.add(target)
        response=requests.get("https://r.jina.ai/"+target,headers={**HEADERS,"X-Timeout":"12","X-Robots-Txt":"*"},timeout=18)
        response.raise_for_status()
        text=response.text[:180000]
        links=re.findall(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)",text)
        for title,link in links:
            if not _same_system(link,url):continue
            parsed=urlparse(link);path=parsed.path.lower().rstrip("/")
            is_directory=any(part in link.lower() for part in ("find-a-doctor","find-a-provider","/doctors","/physicians")) or (parsed.hostname or "").startswith("doctors.")
            if not is_directory:continue
            if re.search(r"\b(find|search|directory)\b",title,re.I):
                if link not in visited and link not in queue:queue.append(link)
                continue
            if path in ("","/doctors","/physicians","/find-a-doctor","/find-a-provider"):continue
            cleaned=re.sub(r"[*_]+","",title).strip()
            if not 5<=len(cleaned)<=100 or not 2<=len(cleaned.split())<=9:continue
            if re.search(r"\b(find|search|more|view|meet|services|hospital|health|directory|image|physicians|doctors|profile)\b",cleaned,re.I):continue
            if not re.fullmatch(r"[A-Za-zÀ-ž'’.,()\-\s]+",cleaned):continue
            credential=re.search(r"\b(MD|M\.D\.|DO|D\.O\.|MBBS|PhD)\b",cleaned)
            people.append({"name":cleaned,"specialty":"Not documented on the directory listing","credentials":credential.group(0) if credential else "Not documented","context":f"Profile link published in this health system's directory. Affiliation with {hospital_name or 'the selected hospital'} and current availability are unverified.","url":link,"phone":""})
        if people:break
    unique={p["url"]:p for p in people}
    return list(unique.values())[:5]

def find_physicians(url, diagnosis, hospital_name, location=""):
    _public_url(url)
    try:
        result=_schema_physicians(url,diagnosis,hospital_name,location)
        if result.get("specialists"):return result
    except (requests.RequestException,ValueError,KeyError,TypeError):
        pass
    try:
        people=_reader_physicians(url,hospital_name,int(time.time()//3600))
    except (requests.RequestException,ValueError,KeyError,TypeError):
        people=[]
    return {"specialists":people,"source_url":url,"message":"Profile links are source-backed; individual hospital affiliation and availability are unverified." if people else "This website did not expose named physician profiles. Open the official physician directory or contact the hospital directly.","directory_available":bool(people)}
