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
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-68-2020-QH14-cu-tru-435315.aspx",
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-59-2014-QH13-cu-tru-217276.aspx",
    "https://thuvienphapluat.vn/van-ban/Bat-dong-san/Luat-Dat-dai-2024-31-2024-QH15-523642.aspx",
    "https://tapchitoaan.vn/giao-dich-dan-su-vo-hieu-theo-quy-dinh-cua-blds-2015",
    "https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/tu-van-phap-luat/46304/do-tuoi-chiu-trach-nhiem-hinh-su-theo-bo-luat-hinh-su",
    "https://thuvienphapluat.vn/van-ban/Tai-nguyen-Moi-truong/Luat-so-72-2020-QH14-Bao-ve-moi-truong-2020-431147.aspx",
    "https://sovhtt.hanoi.gov.vn/quan-ly/thu-tuc-to-chuc-cuoc-thi-nguoi-dep-nguoi-mau-2/",
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-Hon-nhan-va-gia-dinh-2014-219432.aspx",
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-Bao-hiem-xa-hoi-2014-217269.aspx",
    "https://vi.wikipedia.org/wiki/C%C3%B4ng_%C6%B0%E1%BB%9Bc_ch%C3%A2u_%C3%82u_v%E1%BB%81_Nh%C3%A2n_quy%E1%BB%81n",
    "https://vi.wikipedia.org/wiki/Quy%E1%BB%81n_LGBT_%E1%BB%9F_Honduras"
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
