# website_checker

  `python website_checker <URL_to_check>`

Download requirements.txt & website_checker.py script and store them in a folder. Run the following command from within that folder:

  `pip install -r requirements.txt`

If you get any error try running the below command:

  `python -m pip install -r requirements.txt`


## Input: 
(1) URL, e.g. https://www.shoutmeloud.com/

## Output:
(1) Time-to-first-byte, TTFB, in milliseconds. 5 attempts<br />
(2) Do the site use a CDN? (Yes/No), if possible return CDN name<br />
(3) Website uses JS to render? (Yes/No)<br />
(4) Detected compression format: gzip/brotli<br />
(5) Website supports HTTP 2.0: (True/False)<br />
(6) Total JS Size, in KB<br />
(7) Total JS Compressed Size, in KB<br />
(8) Total CSS Size, in KB<br />
(9) Total CSS Compressed Size, in KB<br />
(10) Website is using webcomponent (Yes/No)<br />
(11) Number of detected unoptimized images (Image size >= 350KB)<br />

Creates three files: cdns.csv, css_js.csv, and images.csv with additional info

## How is information extracted and why?

### (1) Time-to-first-byte
Function uses pycurl to find TTFB. If the website has a non trivial time-to-first-byte it means more time to push things and because we will reduce load with bot-blocking. If TTFB is more than half a second, then we are good. If it takes less than 0.1 seconds, then the website is probably using caching.

### (2) Do the site use a CDN?
Functions scrapes cdnplanet using https://www.cdnplanet.com/tools/cdnfinder/ to find CDNs of the given domain URL. It can be valuable to know if the website already use a CDN. A delay of 60 secs is used to include potential redirects. 

### (3) Website uses JS to render? (Yes/No)<br />
The website is first rendered with js **disabled**, stripping all the new lines & extra spaces. Then the website is rendered with js **enabled**, again stripping all the new lines & extra spaces. Then the two results are compared using the source code length to figure out if there were content blocked due to js rendering.

This can also be tested by loading the website with the cache enabled in Chrome devtools. If the time between TTFB and first site render with no or minimum network traffic is still very high, then the performance issues of the site have less to do with the network, and more to do with lots of CPU and Javascript bottleneck. In this case, there is very little we can do
(First site render is measuring for the first time the browser displays something other than a blank page) 

### (4) Detected compression format
Function uses library requests_html to find Content-Encoding in header. If website uses gzip it can be improved. 

### (5) Website supports HTTP 2.0:
Since Python stable libraries such as requests, requests_html etc. doesn't support HTTP/2 yet, it is challenging to extract this information about the website. For the HTTP/2 test we therefore use website: https://tools.keycdn.com/http2-test

### (6)-(9) File Sizes, in KB
Function uses library requests_html to find content size. Python libraries gzip and brotli are used to calculate comressed file size.

### (10) Website is using webcomponent
It is possible to a web component from a regular HTML element because it usually has a hypen (-) in the name. For example: <special-button></special-button>. If a site is using web components to render, but it is done sensibly, then no problem. But if a site uses web components a way that blocks the site render, then it is bad. That is what I would like to find out.

### (11) Website is using webcomponent
Say two images are bigger than 350 kb, then the website probably have a problem and need some image optimization service. The lighthouse report can also help here.
