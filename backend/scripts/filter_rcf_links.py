
input_file = "data/rcf_links.txt"
output_file = "data/rcf_links_en.txt"

with open(input_file, "r") as f:
    links = f.readlines()

en_links = [link.strip() for link in links if "/en/" in link]

print(f"Found {len(en_links)} English links out of {len(links)} total.")

with open(output_file, "w") as f:
    for link in en_links:
        f.write(link + "\n")
