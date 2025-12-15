import requests
import config

def check_llm(url, headers, model_name):
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Chỉ trả lời: OK"}],
        "temperature": 0.0,
        "max_completion_tokens": 5
    }

    r = requests.post(url, headers=headers, json=payload, timeout=15)

    print("="*50)
    print(f"🔎 MODEL: {model_name}")
    print("HTTP:", r.status_code)

    try:
        print("RESPONSE:", r.json())
    except Exception:
        print("RAW:", r.text)


def check_embed():
    payload = {
        "model": "vnptai_hackathon_embedding",
        "input": "test embedding"
    }

    r = requests.post(
        config.URL_EMBEDDING,
        headers=config.HEADERS_EMBED,
        json=payload, 
        timeout=15
    )

    print("="*50)
    print("🔎 EMBEDDING")
    print("HTTP:", r.status_code)
    print("OK" if r.status_code == 200 else r.text)


if __name__ == "__main__":
    check_llm(
        config.URL_LLM_SMALL,
        config.HEADERS_SMALL,
        "vnptai_hackathon_small"
    )

    check_llm(
        config.URL_LLM_LARGE,
        config.HEADERS_LARGE,
        "vnptai_hackathon_large"
    )

    check_embed()
