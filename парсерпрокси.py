import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import socks
import socket
from collections import defaultdict


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, "Proxy")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Mobile/15E148 Safari/604.1"
]

COUNTRY_CODES = {
    "US": "United States",
    "RU": "Russia",
    "CN": "China",
    "DE": "Germany",
    "FR": "France",
    "UK": "United Kingdom",
    "BR": "Brazil",
    "IN": "India",
    "Unknown": "Unknown"
}

PROXY_SOURCES = [
    {'url': 'https://www.sslproxies.org/', 'type': 'HTTPS', 'parse_method': 'table'},
    {'url': 'https://free-proxy-list.net/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'table'},
    {'url': 'https://www.us-proxy.org/', 'type': 'HTTP', 'parse_method': 'table'},
    {'url': 'https://www.socks-proxy.net/', 'type': ['SOCKS4', 'SOCKS5'], 'parse_method': 'table'},
    {'url': 'https://www.proxy-list.download/HTTP', 'type': 'HTTP', 'parse_method': 'text'},
    {'url': 'https://www.proxy-list.download/SOCKS4', 'type': 'SOCKS4', 'parse_method': 'text'},
    {'url': 'https://www.proxy-list.download/SOCKS5', 'type': 'SOCKS5', 'parse_method': 'text'},
    {'url': 'https://www.proxy-list.download/HTTPS', 'type': 'HTTPS', 'parse_method': 'text'},
    {'url': 'https://hidemy.name/en/proxy-list/', 'type': ['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'], 'parse_method': 'hidemyname'},
    {'url': 'https://www.proxyscan.io/', 'type': ['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'], 'parse_method': 'proxyscan'},
    {'url': 'https://openproxy.space/list/http', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'openproxy'},
    {'url': 'https://www.freeproxylists.net/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'table'},
    {'url': 'https://spys.one/en/free-proxy-list/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'spysone'},
    {'url': 'https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc', 
     'type': ['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'], 'parse_method': 'json'},
    {'url': 'https://proxy-daily.com/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'text'},
    {'url': 'https://www.my-proxy.com/free-proxy-list.html', 'type': 'HTTP', 'parse_method': 'myproxy'},
    {'url': 'https://proxyhttp.net/free-list/anonymous-server-hide-ip-address', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'table'},
    # Новые источники
    {'url': 'https://www.proxynova.com/proxy-server-list/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'proxynova'},
    {'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt', 'type': 'HTTP', 'parse_method': 'text'},
    {'url': 'https://www.proxyrack.com/free-proxy-list/', 'type': ['HTTP', 'HTTPS'], 'parse_method': 'proxyrack'},
    {'url': 'https://proxyscrape.com/free-proxy-list', 'type': ['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'], 'parse_method': 'proxyscrape'}
]


def get_random_user_agent():
    import random
    return random.choice(USER_AGENTS)

def fetch_proxies(source):
    url = source['url']
    proxy_types = source['type'] if isinstance(source['type'], list) else [source['type']]
    parse_method = source.get('parse_method', 'table')
    headers = {'User-Agent': get_random_user_agent()}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser') if parse_method != 'json' else None

        proxies = []
        if parse_method == 'table':
            proxies = parse_table(soup, url)
        elif parse_method == 'text':
            proxies = parse_text(response.text)
        elif parse_method == 'hidemyname':
            proxies = parse_hidemyname(soup)
        elif parse_method == 'proxyscan':
            proxies = parse_proxyscan(soup)
        elif parse_method == 'openproxy':
            proxies = parse_openproxy(soup)
        elif parse_method == 'spysone':
            proxies = parse_spysone(soup)
        elif parse_method == 'json':
            proxies = parse_json(response.json())
        elif parse_method == 'myproxy':
            proxies = parse_myproxy(soup)
        elif parse_method == 'proxynova':
            proxies = parse_proxynova(soup)
        elif parse_method == 'proxyrack':
            proxies = parse_proxyrack(soup)
        elif parse_method == 'proxyscrape':
            proxies = parse_proxyscrape(soup)

        return [proxy for proxy in proxies if proxy[2] in proxy_types]
    except Exception as e:
        print(f"❌ Ошибка при парсинге {url}: {str(e)}")
        return []

def parse_table(soup, url):
    proxies = []
    table = soup.find('table')
    if not table:
        print(f"⚠️ Таблица не найдена на {url}")
        return []
    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            country = COUNTRY_CODES.get(cols[2].text.strip(), "Unknown")
            proxy_type = "HTTP"
            if "sslproxies" in url:
                proxy_type = "HTTPS"
            elif "socks" in url.lower():
                proxy_type = "SOCKS5" if "socks5" in url.lower() else "SOCKS4"
            proxies.append((ip, port, proxy_type, country))
    return proxies

def parse_text(text):
    proxies = []
    for line in text.splitlines():
        line = line.strip()
        if ':' in line:
            ip, port = line.split(':', 1)
            proxies.append((ip.strip(), port.strip(), "HTTP", "Unknown"))
    return proxies

def parse_hidemyname(soup):
    proxies = []
    table = soup.find('table', class_='proxy__t')
    if not table:
        print("⚠️ Таблица не найдена на hidemy.name")
        return []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 5:
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            country = COUNTRY_CODES.get(cols[2].text.strip(), "Unknown")
            proxy_type = cols[4].text.strip().upper()
            proxies.append((ip, port, proxy_type, country))
    return proxies

def parse_proxyscan(soup):
    proxies = []
    table = soup.find('table')
    if not table:
        print("⚠️ Таблица не найдена на proxyscan.io")
        return []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 5:
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            country = COUNTRY_CODES.get(cols[2].text.strip(), "Unknown")
            proxy_type = cols[4].text.strip().upper()
            proxies.append((ip, port, proxy_type, country))
    return proxies

def parse_openproxy(soup):
    proxies = []
    proxy_list = soup.find('div', class_='proxy-list')
    if not proxy_list:
        print("⚠️ Список прокси не найден на openproxy.space")
        return []
    for item in proxy_list.find_all('div', class_='proxy-item'):
        text = item.text.strip()
        if ':' in text:
            ip, port = text.split(':', 1)
            proxies.append((ip.strip(), port.strip(), "HTTP", "Unknown"))
    return proxies

def parse_spysone(soup):
    proxies = []
    table = soup.find('table', width='100%')
    if not table:
        print("⚠️ Таблица не найдена на spys.one")
        return []
    for row in table.find_all('tr')[3:]:
        cols = row.find_all('td')
        if len(cols) >= 5:
            ip_port = cols[0].text.strip().split(':')
            if len(ip_port) == 2:
                ip, port = ip_port
                country = COUNTRY_CODES.get(cols[1].text.strip(), "Unknown")
                proxy_type = cols[2].text.strip().upper()
                proxies.append((ip, port, proxy_type, country))
    return proxies

def parse_json(data):
    proxies = []
    if 'data' in data:
        for proxy in data['data']:
            ip = proxy.get('ip')
            port = proxy.get('port')
            country = COUNTRY_CODES.get(proxy.get('country', 'Unknown'), "Unknown")
            proxy_type = proxy.get('protocols', ['HTTP'])[0].upper()
            proxies.append((ip, port, proxy_type, country))
    return proxies

def parse_myproxy(soup):
    proxies = []
    content = soup.find('div', class_='list')
    if not content:
        print("⚠️ Список прокси не найден на my-proxy.com")
        return []
    for line in content.text.splitlines():
        if ':' in line:
            ip, port = line.split(':', 1)
            proxies.append((ip.strip(), port.strip(), "HTTP", "Unknown"))
    return proxies

def parse_proxynova(soup):
    proxies = []
    table = soup.find('table', id='tbl_proxy_list')
    if not table:
        print("⚠️ Таблица не найдена на proxynova.com")
        return []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 3:
            ip_script = cols[0].find('script')
            ip = ip_script.text.split('"')[1] if ip_script else cols[0].text.strip()
            port = cols[1].text.strip()
            country = COUNTRY_CODES.get(cols[2].text.strip(), "Unknown")
            proxies.append((ip, port, "HTTP", country))
    return proxies

def parse_proxyrack(soup):
    proxies = []
    pre = soup.find('pre')
    if not pre:
        print("⚠️ Список прокси не найден на proxyrack.com")
        return []
    for line in pre.text.splitlines():
        if ':' in line:
            ip, port = line.split(':', 1)
            proxies.append((ip.strip(), port.strip(), "HTTP", "Unknown"))
    return proxies

def parse_proxyscrape(soup):
    proxies = []
    textarea = soup.find('textarea', class_='form-control')
    if not textarea:
        print("⚠️ Список прокси не найден на proxyscrape.com")
        return []
    for line in textarea.text.splitlines():
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 2:
                ip, port = parts[0], parts[1]
                proxy_type = parts[2].upper() if len(parts) > 2 else "HTTP"
                proxies.append((ip.strip(), port.strip(), proxy_type, "Unknown"))
    return proxies

def check_proxy(proxy, max_response_time):
    ip, port, proxy_type, country = proxy
    proxy_url = f"{proxy_type.lower()}://{ip}:{port}"
    try:
        test_url = "http://httpbin.org/ip"
        headers = {'User-Agent': get_random_user_agent()}
        if proxy_type.startswith("SOCKS"):
            proxy_type_num = socks.SOCKS4 if proxy_type == "SOCKS4" else socks.SOCKS5
            socks.set_default_proxy(proxy_type_num, ip, int(port))
            socket.socket = socks.socksocket
            start_time = time.time()
            response = requests.get(test_url, headers=headers, timeout=5)
        else:
            start_time = time.time()
            response = requests.get(test_url, headers=headers, proxies={"http": proxy_url, "https": proxy_url}, timeout=5)
        
        response_time = time.time() - start_time
        if response.status_code == 200 and response_time < max_response_time:
            print(f"✅ Рабочий прокси: {proxy_url} ({country}, время: {response_time:.2f} сек)")
            return (proxy_url, country)
        return None
    except Exception as e:
        print(f"❌ Не рабочий: {proxy_url} ({country}, {str(e)})")
        return None

def main():
    while True:
        try:
            max_response_time = float(input("Введите максимальное время ответа прокси в секундах (например, 5.0): "))
            if max_response_time > 0:
                break
            print("Пожалуйста, введите положительное число.")
        except ValueError:
            print("Пожалуйста, введите корректное число (например, 5.0).")

    os.makedirs(TARGET_DIR, exist_ok=True)
    print(f"🟢 Папка для сохранения: {TARGET_DIR}")
    print(f"⏱ Установлено максимальное время ответа: {max_response_time} сек")

    all_proxies = []
    for source in PROXY_SOURCES:
        print(f"🔎 Парсим прокси с {source['url']}...")
        proxies = fetch_proxies(source)
        all_proxies.extend(proxies)
    print(f"Всего найдено прокси: {len(all_proxies)}")

    valid_proxies_by_country = defaultdict(list)
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_proxy, proxy, max_response_time) for proxy in all_proxies]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                proxy_url, country = result
                valid_proxies_by_country[country].append(proxy_url)

    all_proxies_file = os.path.join(TARGET_DIR, "all_proxies.txt")
    with open(all_proxies_file, "w", encoding="utf-8") as f:
        all_valid_proxies = [proxy for proxies in valid_proxies_by_country.values() for proxy in proxies]
        f.write("\n".join(all_valid_proxies))
    print(f"Сохранено {len(all_valid_proxies)} прокси в файл: {all_proxies_file}")

    for country, proxies in valid_proxies_by_country.items():
        safe_country = country.replace(" ", "_").replace("/", "_")
        country_file = os.path.join(TARGET_DIR, f"{safe_country}.txt")
        with open(country_file, "w", encoding="utf-8") as f:
            f.write("\n".join(proxies))
        print(f"Сохранено {len(proxies)} прокси для {country} в файл: {country_file}")

    print("\n📊 Статистика рабочих прокси:")
    total_valid_proxies = sum(len(proxies) for proxies in valid_proxies_by_country.values())
    print(f"Всего рабочих прокси: {total_valid_proxies}")
    print("Распределение по странам:")
    for country, proxies in sorted(valid_proxies_by_country.items()):
        print(f"  {country}: {len(proxies)} прокси")

if __name__ == "__main__":
    main()