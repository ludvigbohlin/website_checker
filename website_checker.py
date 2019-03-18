"""
Website Checker - V.1.0.0

Usage:
    
    python website_checker.py https://wasi0013.com

Author: Wasi Mohammed Abdullah
Date: Feb 23, 2019
For help and support visit: https://wasi0013.com/contact

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

try:
    import pycurl
except ImportError:
    print("Couldn't Find Pycurl")



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
    print("LOOKING UP CDNS OF:", url, "PLEASE WAIT 60 SECS...")
    time.sleep(60)
    cdns = []
    # print(r.html.raw_html)
    for element in r.html.find('tbody>tr'):
        s = BeautifulSoup(element.raw_html, 'lxml')
        tds = {}
        try:
            tds['Count'], tds['Domain'], tds['Provider'] = [td.text for td in s.find_all('td')]
            print("Count:",  tds['Count'], "CDN:", tds['Domain'],"Provider:", tds['Provider'])    
        except Exception as e:
            print(e)
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
try:
    print("TTFB CHECK IN PROGRESS...")
    ttfb = []
    for i in range(1, 6):
        print("attempt {}: ".format(i), end="")
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
        print(js)
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
        print("Error fetching image size for:", image_url)

    if image_size is not None and image_size >=350:
        images.append({
               'url': image_url,
               'size(KB)': image_size,
        })
    image_count += 1


print("Using any cdn?", "Yes (stored the list in cdns.csv)" if cdns else "Nope" )
if html_length != html_length_with_js:
    print("Website uses JS to render: Yes")
else:
    print("Website uses JS to render: No")
if r.history:
    print("Redirected:", r.history[-1].is_redirect)
    print("Redirect status code:", r.history[-1].status_code)
    print("Redirected from:", r.history[-1].url)
    print("Redirected to:", r.url)
print("Checking website with Cache Disabled")
print("Detected Compression:", headers)
print("Supports HTTP 2.0 Version:", http_version(url))
print("Total JS Size: ", total/1000, "KB")
print("Total JS Compressed Size: ", total_compressed/1000, "KB")
print("Total CSS Size: ", total_css/1000, "KB")
print("Total CSS Compressed Size: ", total_css_compressed/1000, "KB")
print("website is using webcomponent: ", "yes ({})".format(len(web_components)) if web_components else "No")
print("TTFB Time: ", "%.2f MS"%ttfb_time)
print("Standard Deviation of TTFB: %.2f"%std_dev,"MS")
if images:
    print("Detected unoptimized images:",len(images),"of", image_count,"(Image size >= 350KB)")
    dx = pd.DataFrame(columns=['url', 'size(KB)'])
    dx = dx.append(images, ignore_index=False, sort=False)
    dx.to_csv("images.csv", index=False)
else:
    print("Unoptimized Images:","Not Found")
if data:
    df = pd.DataFrame(columns=['name', 'size', 'compressed'])
    df = df.append(data, ignore_index=False, sort=False)
    df.to_csv('css_js.csv', index=False)
if cdns:
    cdn_df = pd.DataFrame(columns=['Count', 'Domain', 'Provider'])
    cdn_df = cdn_df.append(cdns, ignore_index=True)
    cdn_df.to_csv("cdns.csv", index=False)
