"""
Website Checker - V.1.0.0
Usage:  
    python website_checker.py https://wasi0013.com
"""

import io
from math import sqrt
import time
import sys
import brotli
from bs4 import BeautifulSoup
import pandas as pd
import requests_html
import gzip
import scipy.stats


try:
    import pycurl
except ImportError:
    print("Couldn't find pycurl")
    exit()



if(len(sys.argv) != 2):
    print("\nError usage: python %s <URL_to_check>\n" % sys.argv[0])
    exit()

url = sys.argv[1]    
headers = {}

def standard_deviation(items):
    """returns the standard deviation of a list of numbers (items)"""
    average = sum(items)/len(items)
    variance = sum([(item - average)**2 for item in items]) / len(items)
    return sqrt(variance)


def mean_confidence_interval(mean, standard_deviation, number_of_attempts, confidence=0.95):
    m = mean
    se = standard_deviation
    n = number_of_attempts-1
    h = se * scipy.stats.t.ppf((1 + confidence) / 2., n-1)
    return m-h, m+h

def cdn_finder(url):
    """
    scrape cdnplanet to find cdns of the given domain url
    """
    s = requests_html.HTMLSession()
    try:
        r = s.get("https://www.cdnplanet.com/tools/cdnfinder/#site:"+url)
        # print(r.html.full_text)
        r.html.render()
    except Exception as e:
        print(e)
    wait_seconds = 60
    print("\nLooking up CDNs of:", url)
    print("  Pleaste wait", wait_seconds, "seconds...")
    time.sleep(wait_seconds)
    cdns = []
    # print(r.html.raw_html)
    for element in r.html.find('tbody>tr'):
        s = BeautifulSoup(element.raw_html, 'lxml')
        tds = {}
        try:
            tds['Count'], tds['Domain'], tds['Provider'] = [td.text for td in s.find_all('td')]
            print("   Count:",  tds['Count'], "CDN:", tds['Domain'],"Provider:", tds['Provider'])    
        except Exception as e:
            print("   ", e)
        if tds:
            cdns.append(tds)
    return cdns


def http_version(url):
    """
    scrape https://tools.keycdn.com/http2-test to find http 2/0 support of the given domain url
    """
    url = url.replace("https://", "").replace("http://", "")
    x = requests_html.HTMLSession()
    r = x.get("https://tools.keycdn.com/http2-test")
    script = """
        () => {
        var  value = ""
         if(jQuery.isReady) {
            $("#public").prop('checked', false);
            $("#url").val("%s")
            
            value = $.post( "http2-query.php", $('#http2Form').serialize()).done(function( data ) {value = data})
            }
    return value;
    }
    """%url
    result = r.html.render(script=script)
    # print(result)
    return True if "alert-success" in result else False



cdns = []
try:
    cdns = cdn_finder(url) 
except Exception as e:
    print("Error Occurred: Couldn't Fetch CDN", e)

data = []
session = requests_html.HTMLSession()
try:
    r = session.get(url)
except Exception as e:
    print("Error:", e)

html_length = len(r.html.full_text.strip())

try:
    r.html.render()
except Exception as e:
    print("Rendering Error:", e)

# print("rendering website please wait 30s...")
# time.sleep(30)

ttfb_time = None
std_dev = None
number_of_attempts = 6
try:
    print("\nTTFB checks in progress...")
    ttfb = []
    for i in range(1, number_of_attempts):
        print("   Attempt {}: ".format(i), end="")
        c = pycurl.Curl()
        c.setopt(pycurl.URL, r.url)  # set url
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.perform()  # execute
        ttfb_time = c.getinfo(pycurl.STARTTRANSFER_TIME)
        print(r.url, "%.2f"%(ttfb_time*1000),"MS")
        ttfb.append(ttfb_time*1000)#time-to-first-byte time    
        c.close()
    std_dev = standard_deviation(ttfb)
    ttfb_time = sum(ttfb)/len(ttfb)
except Exception as e:
    print("Error Occurred: Couldn't find TTFB", e)


soup = BeautifulSoup(r.html.raw_html, "lxml")
web_components = set(tag.name for tag in soup.find_all() if "-" in tag.name or 'template' in tag.name)

html_length_with_js = len(r.html.full_text.strip())
headers = r.headers.get("Content-Encoding")

# print(r.headers)


if "br" in headers.lower():
    is_brotli_enabled = True
else:
    is_brotli_enabled = False



### CHECK JS FILE SIZE ###

total = 0
total_compressed = 0


for element in r.html.find('script'):
    if element.attrs.get('src'):
        # print(element.attrs.get('src'))
        try:
            js = session.get(element.attrs['src'])

        except:
            js = session.get(element.base_url + element.attrs['src'])
        if js.status_code != 200:
            continue
        size = len(js._content)
        if is_brotli_enabled:

            if isinstance(js._content, bytes):
                compressed = len(brotli.compress(js._content))
            else:    
                compressed = len(brotli.compress(bytes(js._content, encoding='utf-8')))
        else:

            if isinstance(js._content, bytes):
                compressed = len(gzip.compress(js._content))
            else:    
                compressed = len(gzip.compress(bytes(js._content, encoding='utf-8')))
        data.append({
            'name':element.attrs['src'],
            'size': "%.2fKB"%(size/1000),
            'compressed':"%.2fKB"%(compressed/1000)
            })
        total += size
        total_compressed += compressed
    else:
        if is_brotli_enabled:
            compressed = len(brotli.compress(bytes(element.text, encoding='utf-8')))
        else:
            compressed = len(gzip.compress(bytes(element.text, encoding='utf-8')))
        data.append({
            'name':'inline script',
            'size': "%.2fKB"%(len(element.text)/1000),
            'compressed':"%.2fKB"%(compressed/1000)
            
            })
        total += len(element.text)
        total_compressed += compressed


### CHECK CSS FILE SIZE ###

total_css = 0
total_css_compressed = 0

for element in r.html.find('link'):
    if (element.attrs.get('type') and ("text/css" in element.attrs.get('type'))) or (element.attrs.get("rel") and ("stylesheet" in element.attrs.get("rel"))) or (element.attrs.get('href') and ("css" in element.attrs.get('href'))):
        try:
            x = session.get(element.attrs.get('href'))
        except:
            # print("except")
            x = session.get(element.base_url + element.attrs['href'])
        if x.status_code != 200:
            continue
        css_size = len(x._content)
        if is_brotli_enabled:
            if isinstance(x._content, bytes):
                css_compressed = len(brotli.compress(x._content))    
            else:
                css_compressed = len(brotli.compress(bytes(x._content, encoding='utf-8')))
        else:
            if isinstance(x._content, bytes):
                css_compressed = len(gzip.compress(x._content))    
            else:
                css_compressed = len(gzip.compress(bytes(x._content, encoding='utf-8')))
        
        data.append({
            'name':element.attrs['href'],
            'size': "%.2fKB"%(css_size/1000),
            'compressed':"%.2fKB"%(css_compressed/1000)
            })
        total_css += css_size
        total_css_compressed += css_compressed

for element in r.html.find("style"):
        if is_brotli_enabled:
            css_compressed = len(brotli.compress(bytes(element.text, encoding='utf-8')))
        else:
            css_compressed = len(gzip.compress(bytes(element.text, encoding='utf-8')))
        data.append({
            'name':'inline css',
            'size': "%.2fKB"%(len(element.text)/1000),
            'compressed':"%.2fKB"%(css_compressed/1000)
            
            })
        total_css += len(element.text)
        total_css_compressed += css_compressed


### Optimized Image Check ###
images = []
images_missing_info = 0
image_count = 0
for element in r.html.find("img"):
    image_url = element.attrs.get("src")
    try:
        if image_url:
            i = session.get(image_url)
        else:
            continue
    except:
        if image_url[0] == "/" and element.base_url[-1] == "/": image_url = image_url[1::]
        image_url = element.base_url + image_url
        i = session.get(image_url)
    if i.status_code != 200:
        continue
    image_size = None
    try:
        image_size = int(i.raw.info().get("Content-Length"))/1000
    except:
        images_missing_info = 1
        images.append({
               'url': image_url,
               'size(KB)': "Error fetching image size. No Content-Length in header."
               })

    if image_size is not None and image_size >=350:
        images.append({
               'url': image_url,
               'size(KB)': image_size,
        })
    image_count += 1


ttfb_interval_array = mean_confidence_interval(ttfb_time, std_dev, number_of_attempts)

print("1. TTFB, mean: %.2f ms, CI: [%.2fms, %.2fms]"%(ttfb_time,ttfb_interval_array[0],ttfb_interval_array[1]))
print("2. Do the site use a CDN?", "Yes (stored the list in cdns.csv)" if cdns else "No" )
if html_length != html_length_with_js:
    print("3. Website uses JS to render: Yes")
else:
    print("3. Website uses JS to render: No")
if r.history:
    print("   Redirected:", r.history[-1].is_redirect)
    print("   Redirect status code:", r.history[-1].status_code)
    print("   Redirected from:", r.history[-1].url)
    print("   Redirected to:", r.url)

print("4. Detected compression format:", headers)
print("5. Supports HTTP/2.0:", http_version(url))
print("6. Total JS size: ", total/1000, "KB")
print("7. Total JS compressed size: ", total_compressed/1000, "KB")
print("8. Total CSS size: ", total_css/1000, "KB")
print("9. Total CSS compressed size: ", total_css_compressed/1000, "KB")
print("10. Website is using webcomponent: ", "Yes ({})".format(len(web_components)) if web_components else "No")

css_file = "css_js.csv"
cdn_file = "cdns.csv"
image_file = "images.csv"


if images:
    print("11. Number of detected unoptimized images:",len(images),"of", image_count,"(Image size >= 350KB)")
    dx = pd.DataFrame(columns=['url', 'size(KB)'])
    dx = dx.append(images, ignore_index=False, sort=False)
    dx.to_csv(image_file, index=False)
    if images_missing_info == 1:
        print("  (Note that some images lack content-length info in header)")
else:
    print("11. Number of detected unoptimized images: Unoptimized images Not Found")
    if images_missing_info == 1:
        print("  (Note that some images lack content-length info in header")



#Write to file
print("\nWriting output data to files:")
if images:
    print("  ",image_file)
if data:
    print("  ",css_file)
if cdns:
    print("  ",cdn_file)

if data:
    df = pd.DataFrame(columns=['name', 'size', 'compressed'])
    df = df.append(data, ignore_index=False, sort=False)
    df.to_csv(css_file, index=False)
if cdns:
    cdn_df = pd.DataFrame(columns=['Count', 'Domain', 'Provider'])
    cdn_df = cdn_df.append(cdns, ignore_index=True)
    cdn_df.to_csv(cdn_file, index=False)

print("\nScript finished")

