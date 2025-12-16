import os
from pathlib import Path
from tqdm import tqdm
import re

# --- CONFIG ---
INPUT_FOLDER = "hisoty_raw_book"
OUTPUT_FILE = "data/big_dataset_history.txt"

SAFE_MIN_LENGTH = 5

def is_historical_content(line):
    """Detect lines that indicate historical content: years, centuries, dates, Roman numerals, common historical verbs/names.
    Keep these even when short.
    """
    # Years like 1800, 1945, 2020; ranges like 1914-1918
    if re.search(r"\b(1[5-9][0-9]{2}|20[0-9]{2}|(\d{3,4}[-–—]\d{2,4}))\b", line):
        return True

    # BC / AD and century mentions
    if re.search(r"\b(BC|B\.C\.|AD|A\.D\.|century|centuries|c\.|ca\.|circa)\b", line, re.I):
        return True

    # Date formats like 12/04/1870 or April 12, 1870
    if re.search(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b", line):
        return True
    if re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b", line, re.I):
        return True

    # Roman numerals often used in chapter/volume headings (I, II, III, IV)
    if re.match(r"^[IVXLCDM]+$", line.strip()):
        return True

    # Common history-related words/phrases
    if re.search(r"\b(reign|reigned|born|died|battle|treaty|signed|king|queen|emperor|dynasty|siege|colonial|independence)\b", line, re.I):
        return True

    # Names with titles: "King Henry", "President Lincoln"
    if re.search(r"\b(King|Queen|Emperor|President|Prime Minister|General|Duke|Archduke|Sir)\s+[A-Z][a-z]+", line):
        return True

    return False


def is_header_or_title(line):
    """Preserve obvious headers and short titles.
    Similar heuristics to the STEM script but tuned for history texts.
    """
    if not line:
        return False
    # All-caps headings (e.g., CHAPTER I, PREFACE)
    if line.isupper() and len(line) > 3:
        return True
    # Lines that end with a colon are likely section titles
    if line.endswith(':'):
        return True
    # Numbered headings like "1.2. The Causes"
    if re.match(r'^\d+(\.\d+)*', line):
        return True
    # Short Roman numeral + title (e.g., "I. Introduction")
    if re.match(r'^[IVXLCDM]+\.?\s', line):
        return True
    return False


def is_garbage(line):
    """Remove lines that are almost certainly page artifacts or separators."""
    if not line:
        return True
    # Page numbers
    if line.isdigit():
        return True
    # Lines of repeated dots/underscores/equals are separators
    if line.count('.') > 10 or line.count('_') > 10 or line.count('=') > 10:
        return True
    # Single-character lines that are not Roman numerals
    if len(line) <= 2 and not re.match(r'^[IVXLCDM]+$', line):
        return True
    return False


def ingest_many_books():
    print("Scanning input folder for history books...")
    input_path = Path(INPUT_FOLDER)
    all_files = list(input_path.rglob("*.txt"))

    if not all_files:
        print(f"No .txt files found in {INPUT_FOLDER}")
        return

    print(f"--> Found {len(all_files)} files.")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    total_lines = 0
    success_count = 0

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f_out:
        for file_path in tqdm(all_files, desc="Processing files"):
            try:
                with open(file_path, "r", encoding="utf-8", errors='replace') as f_in:
                    content = f_in.read()

                lines = content.split('\n')
                processed_content = []

                rel_path = file_path.relative_to(INPUT_FOLDER)
                processed_content.append(f"\n\n<DOCUMENT_START filename='{rel_path}'>\n")

                for line in lines:
                    line = line.strip()

                    if is_garbage(line):
                        continue

                    # Safe mode: keep longer lines
                    if len(line) > SAFE_MIN_LENGTH:
                        processed_content.append(line)
                    else:
                        # Keep short lines that are historical content or headers
                        if is_historical_content(line) or is_header_or_title(line):
                            processed_content.append(line)
                        else:
                            pass

                processed_content.append(f"\n<DOCUMENT_END filename='{rel_path}'>\n")

                f_out.write("\n".join(processed_content))

                total_lines += len(processed_content)
                success_count += 1

            except Exception as e:
                with open("error_log.txt", "a", encoding="utf-8") as f_err:
                    f_err.write(f"Error file {file_path}: {str(e)}\n")

    print("\n" + "="*40)
    print("DONE!")
    print(f"Processed: {success_count} files")
    print(f"Total lines: {total_lines}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
    else:
        ingest_many_books()
