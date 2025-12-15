import requests
from bs4 import BeautifulSoup
import re
import os
import time

# =========================
# CONFIG
# =========================

FILE_PATH = "data/documents.txt"

URLS = [
    "https://www.studocu.vn/vn/document/truong-dai-hoc-cong-nghiep-ha-noi/kien-truc-may-tinh/4-phan-doan-va-phan-trang/80299122",
    "https://vietmachine.com.vn/phan-mem-in3d-cura3d.html",
    "https://viettelidc.com.vn/tin-tuc/sock-la-gi",
    "https://viettelidc.com.vn/tin-tuc/tim-hieu-chung-ve-cac-loai-raid-luu-tru",
    "https://vi.wikipedia.org/wiki/An_ninh_m%E1%BA%A1ng",
    "https://vi.wikipedia.org/wiki/%C4%90%E1%BB%99ng_c%C6%A1_%C4%91i%E1%BB%87n_kh%C3%B4ng_%C4%91%E1%BB%93ng_b%E1%BB%99",
    "https://vi.wikipedia.org/wiki/Bi%E1%BA%BFn_%C3%A1p",
    "https://codienvimax.vn/cach-tinh-cong-suat-3-pha/",
    






]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# UTILS
# =========================

def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[cần dẫn nguồn\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(soup, url):
    if "wikipedia.org" in url:
        h1 = soup.find("h1", id="firstHeading")
        if h1:
            return h1.get_text(strip=True)

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    title = soup.find("title")
    if title:
        return title.get_text(strip=True)

    return "KHÔNG XÁC ĐỊNH"


def extract_main_content(soup, url):
    if "wikipedia.org" in url:
        return soup.find("div", class_="mw-parser-output")

    if "thuvienphapluat.vn" in url:
        return soup.find("div", class_="content1")

    for cls in ["content", "main-content", "article-content", "entry-content"]:
        div = soup.find("div", class_=cls)
        if div:
            return div

    return None


def remove_junk(div):
    for tag in div.find_all(["table", "ul", "nav", "aside"]):
        tag.decompose()


# =========================
# MAIN CRAWLER
# =========================

def crawl():
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

    collected = ""

    for url in URLS:
        print(f"🔄 Crawling: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print("❌ HTTP error")
                continue

            soup = BeautifulSoup(r.content, "html.parser")

            title = extract_title(soup, url)
            content_div = extract_main_content(soup, url)

            if not content_div:
                print("⚠️ Không tìm thấy nội dung chính")
                continue

            remove_junk(content_div)

            raw_text = content_div.get_text(separator="\n\n")
            paragraphs = raw_text.split("\n\n")

            count = 0
            collected += f"\n\n=== {title} ===\n"
            collected += f"Source: {url}\n\n"

            for p in paragraphs:
                text = clean_text(p)

                if len(text) < 150:
                    continue

                collected += text + "\n\n"
                count += 1

                if count >= 15:
                    break

            print(f"✅ Added {count} paragraphs")

            time.sleep(1)

        except Exception as e:
            print(f"❌ Error: {e}")

    if collected:
        with open(FILE_PATH, "a", encoding="utf-8") as f:
            f.write(collected)

        print(f"\n🎉 DONE. Data saved to {FILE_PATH}")
    else:
        print("\n⚠️ No content collected")


if __name__ == "__main__":
    crawl()
