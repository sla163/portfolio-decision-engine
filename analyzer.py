# analyzer.py
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from config import GEMINI_API_KEY, SYSTEM_INSTRUCTION

def analyze_and_summarize(raw_news_text: str, portfoy_ozeti: str = None) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY ortam değişkeni tanımlı değil!")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Eğer portföy sapmaları geldiyse prompta ekliyoruz:
    portfoy_metni = ""
    if portfoy_ozeti:
        portfoy_metni = f"\n\n{portfoy_ozeti}\n"
    
    prompt = (
        f"{portfoy_metni}\n"
        "Aşağıdaki son 24 saate ait ham haber akışını incele. "
        "Kullanıcının güncel portföy sapmalarını da göz önünde bulundurarak "
        "belirtilen format kurallarına uygun günlük faizsiz portföy bültenini oluştur:\n\n"
        f"{raw_news_text}"
    )

    models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash"
        ]
    for model_name in models_to_try:
        for attempt in range(3):  # Her model için 3 kez dene
            try:
                print(f"[{model_name}] ile bülten üretiliyor (Deneme {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2
                    )
                )
                return response.text

            except ServerError as e:
                print(f"[UYARI] {model_name} sunucu yoğunluğu (503): {e}. Bekleniyor...")
                time.sleep(5 * (attempt + 1))  # 5sn, 10sn bekle ve tekrar dene
            except Exception as e:
                print(f"[HATA] Beklenmeyen istek hatası: {e}")
                break  # Diğer modele geç

    raise RuntimeError("Tüm Gemini modelleri yoğunluk nedeniyle yanıt veremedi. Lütfen biraz sonra tekrar deneyin.")