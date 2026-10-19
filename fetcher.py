import feedparser
from config import RSS_FEEDS

def fetch_all_news(limit_per_feed: int = 5) -> str:
    """Belirtilen RSS kaynaklarından son haberleri çeker ve metin olarak birleştirir."""
    aggregated_news = []
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                # HTML etiketlerini basitçe temizle veya kısalt
                clean_summary = summary.replace("<b>", "").replace("</b>", "")[:250]
                
                aggregated_news.append(
                    f"Kaynak: {source_name}\n"
                    f"Başlık: {title}\n"
                    f"Özet: {clean_summary}\n"
                    f"---"
                )
        except Exception as e:
            print(f"[UYARI] {source_name} çekilirken hata oluştu: {e}")
            
    return "\n".join(aggregated_news)