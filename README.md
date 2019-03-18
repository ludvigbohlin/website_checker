# website_checker

python website_checker <URL_to_check>


## Input: 
(1) URL, e.g. https://www.shimmercat.com/

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
(11) Standard Deviation of TTFB<br />
(12) Number of detected unoptimized images (Image size >= 350KB)<br />

Creates three files: cdns.csv, css_js.csv, and images.csv with additional info

