import requests
import xml.etree.ElementTree as ET

def get_rcf_sitemap():
    url = "https://www.rcf.it/sitemap.xml"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            # It might be a sitemap index
            root = ET.fromstring(response.content)
            
            # Check if it's a sitemap index
            if 'sitemapindex' in root.tag:
                print("Found sitemap index")
                for sitemap in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
                    loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
                    print(f"Processing sub-sitemap: {loc}")
                    process_sitemap(loc)
            else:
                process_sitemap(url)
        else:
            print(f"Failed to fetch sitemap: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def process_sitemap(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            links = []
            for url_tag in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                loc = url_tag.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
                if '/product-detail/' in loc or '/products/detail/' in loc:
                    links.append(loc)
            
            print(f"Found {len(links)} product links in {url}")
            
            if links:
                with open("/workspaces/Support-Center-/backend/data/rcf_links.txt", "a") as f:
                    for link in links:
                        f.write(link + "\n")
    except Exception as e:
        print(f"Error processing sitemap {url}: {e}")

if __name__ == "__main__":
    # Clear file first
    with open("/workspaces/Support-Center-/backend/data/rcf_links.txt", "w") as f:
        pass
    get_rcf_sitemap()
