export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. GET İsteği: Python bülteni veriyi buradan okur
    if (request.method === "GET") {
      const authHeader = request.headers.get("Authorization");
      if (!env.PORTFOLIO_API_TOKEN || authHeader !== `Bearer ${env.PORTFOLIO_API_TOKEN}`) {
        return new Response("Unauthorized", { status: 401 });
      }
      if (!env.PORTFOLIO_STORE) {
        return new Response("PORTFOLIO_STORE KV bağlantısı bulunamadı.", { status: 503 });
      }
      const raw = await env.PORTFOLIO_STORE.get("holdings");
      return new Response(raw || "[]", {
        headers: { "Content-Type": "application/json; charset=utf-8" }
      });
    }

    // 2. Python'dan gelen hazır analizi KV'ye önbellekleme endpointi
    if (request.method === "POST" && url.pathname === "/cache_analysis") {
      const authHeader = request.headers.get("Authorization");
      if (!env.PORTFOLIO_API_TOKEN || authHeader !== `Bearer ${env.PORTFOLIO_API_TOKEN}`) {
        return new Response("Unauthorized", { status: 401 });
      }
      if (!env.PORTFOLIO_STORE) {
        return new Response("PORTFOLIO_STORE KV bağlantısı bulunamadı.", { status: 503 });
      }
      let data;
      try {
        data = await request.json();
      } catch {
        return new Response("Geçersiz JSON.", { status: 400 });
      }
      if (typeof data.report !== "string" || !data.report.trim()) {
        return new Response("report alanı boş olmayan bir metin olmalıdır.", { status: 400 });
      }
      await env.PORTFOLIO_STORE.put("cached_analysis", data.report);
      return new Response("OK", { status: 200 });
    }

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    if (
      !env.TELEGRAM_WEBHOOK_SECRET ||
      request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.TELEGRAM_WEBHOOK_SECRET
    ) {
      return new Response("Unauthorized", { status: 401 });
    }

    let chatId = "";
    try {
      const payload = await request.json();
      const message = payload.message || {};
      chatId = String(message.chat?.id || "");
      const text = typeof message.text === "string" ? message.text.trim() : "";

      // Güvenlik: Sadece sizin Telegram ID'niz
      const allowedId = String(env.TELEGRAM_CHAT_ID || "").trim();
      if (!allowedId || chatId !== allowedId) {
        return new Response("Unauthorized", { status: 200 });
      }

      if (!env.PORTFOLIO_STORE) {
        await sendMsg(env, chatId, "❌ Hata: PORTFOLIO_STORE KV bağlantısı bulunamadı.");
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /portfoy veya /liste
      // ==========================================
      if (text === "/portfoy" || text === "/liste") {
        const holdings = await getHoldingsData(env);
        if (holdings.length === 0) {
          await sendMsg(env, chatId, "Portföyde kayıtlı varlık bulunamadı.");
          return new Response("OK", { status: 200 });
        }

        let table = "📊 <b>GÜNCEL PORTFÖY TABLOSU</b>\n\n<pre>";
        table += "SEMBOL     ADET     MALİYET    PARA  SINIF\n";
        table += "------------------------------------------\n";

        for (let item of holdings) {
          const sembol = (item.sembol || "").padEnd(10, " ");
          const adet = String(item.adet || 0).padEnd(8, " ");
          const maliyet = String(item.maliyet || 0).padEnd(10, " ");
          const para = (item.para || "TRY").padEnd(5, " ");
          const sinif = item.sinif || "";
          table += `${sembol} ${adet} ${maliyet} ${para} ${sinif}\n`;
        }
        table += "</pre>";

        await sendMsg(env, chatId, table, "HTML");
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /kar veya /rapor
      // ==========================================
      if (text === "/kar" || text === "/rapor") {
        const cached = await env.PORTFOLIO_STORE.get("cached_analysis");
        if (!cached) {
          await sendMsg(env, chatId, "⚠️ Henüz önbelleğe alınmış güncel bir analiz raporu yok. Lütfen scripti çalıştırın.");
        } else {
          await sendMsg(env, chatId, cached, "Markdown");
        }
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /gecmis [ADET] (İşlem Geçmişi)
      // ==========================================
      if (text.startsWith("/gecmis") || text.startsWith("/log")) {
        const parts = text.split(/\s+/);
        const limit = parts[1] ? parseInt(parts[1], 10) : 7;
        const history = await getHistoryData(env);

        if (history.length === 0) {
          await sendMsg(env, chatId, "İşlem geçmişinde kayıt bulunamadı.");
          return new Response("OK", { status: 200 });
        }

        const sonIslemler = history.slice(-limit).reverse();
        let msg = `📜 <b>SON İŞLEM GEÇMİŞİ (Son ${sonIslemler.length} İşlem)</b>\n\n`;

        for (let islem of sonIslemler) {
          msg += `🕒 <code>${islem.tarih}</code> | <b>${islem.tip}</b>\n`;
          msg += `└ ${islem.detay}\n\n`;
        }

        await sendMsg(env, chatId, msg, "HTML");
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /yatir TUTAR [PARA] (Taze Para Girişi)
      // ==========================================
      if (text.startsWith("/yatir") || text.startsWith("/ekle_nakit")) {
        const parts = text.split(/\s+/);
        if (parts.length >= 2) {
          const tutar = parseFloat(parts[1]);
          const para = parts[2] ? parts[2].toUpperCase() : "TRY";

          if (isNaN(tutar) || tutar <= 0) {
            await sendMsg(env, chatId, "⚠️ Yatırılan tutar geçerli pozitif bir sayı olmalıdır.");
            return new Response("OK", { status: 200 });
          }

          let holdings = await getHoldingsData(env);
          const nakitSembol = `NAKIT_${para}`;
          let nakitItem = holdings.find(i => (i.sembol || "").toUpperCase() === nakitSembol);

          if (nakitItem) {
            nakitItem.adet = Number((parseFloat(nakitItem.adet || 0) + tutar).toFixed(2));
          } else {
            holdings.push({
              sembol: nakitSembol,
              sinif: "nakit_para",
              adet: Number(tutar.toFixed(2)),
              maliyet: 1.0,
              para: para
            });
          }

          await saveHoldingsData(env, holdings);
          await logAction(env, "NAKİT GİRİŞİ", `+${tutar.toFixed(2)} ${para} hesaba eklendi`);

          const guncelNakit = holdings.find(i => (i.sembol || "").toUpperCase() === nakitSembol)?.adet;

          let msg = `📥 <b>Nakit Girişi Kaydedildi</b>\n\n` +
                    `Eklenen Tutar: <code>${tutar.toFixed(2)} ${para}</code>\n` +
                    `💵 <b>Toplam ${nakitSembol}:</b> <code>${guncelNakit} ${para}</code>`;
          await sendMsg(env, chatId, msg, "HTML");
        } else {
          await sendMsg(env, chatId, "⚠️ <b>Kullanım:</b>\n<code>/yatir TUTAR [PARA]</code>\nÖrn: <code>/yatir 10000 TRY</code>", "HTML");
        }
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /al SEMBOL ADET MALİYET [PARA] [SINIF]
      // ==========================================
      if (text.startsWith("/al")) {
        const parts = text.split(/\s+/);
        if (parts.length >= 4) {
          const sembol = parts[1].toUpperCase();
          const adet = parseFloat(parts[2]);
          const maliyet = parseFloat(parts[3]);
          const para = parts[4] ? parts[4].toUpperCase() : "TRY";
          const sinif = parts[5] ? parts[5].toLowerCase() : "bist_katilim";

          if (isNaN(adet) || isNaN(maliyet)) {
            await sendMsg(env, chatId, "⚠️ Adet ve maliyet geçerli bir sayı olmalıdır.");
            return new Response("OK", { status: 200 });
          }

          let holdings = await getHoldingsData(env);
          let updateMsg = "";
          let found = false;

          for (let item of holdings) {
            const itemSembol = (item.sembol || item.kod || "").toUpperCase();
            if (itemSembol === sembol) {
              const eskiAdet = parseFloat(item.adet || 0);
              const eskiMaliyet = parseFloat(item.maliyet || 0);
              const yeniAdet = eskiAdet + adet;
              const yeniMaliyet = yeniAdet > 0 ? ((eskiAdet * eskiMaliyet) + (adet * maliyet)) / yeniAdet : 0;

              item.adet = Number(yeniAdet.toFixed(4));
              item.maliyet = Number(yeniMaliyet.toFixed(4));
              found = true;
              updateMsg = `Mevcut varlık güncellendi: <b>${sembol}</b>\nYeni Adet: <code>${item.adet}</code> | Ort. Maliyet: <code>${item.maliyet} ${para}</code>`;
              break;
            }
          }

          if (!found) {
            holdings.push({
              sembol,
              adet: Number(adet.toFixed(4)),
              maliyet: Number(maliyet.toFixed(4)),
              para: para,
              sinif: sinif
            });
            updateMsg = `Yeni varlık eklendi: <b>${sembol}</b>\n<code>${adet}</code> adet @ <code>${maliyet} ${para}</code> (${sinif})`;
          }

          await saveHoldingsData(env, holdings);
          await logAction(env, "ALIM", `${sembol} +${adet} adet @ ${maliyet} ${para}`);

          await sendMsg(env, chatId, `✅ <b>Alım İşlendi</b>\n\n${updateMsg}`, "HTML");
        } else {
          await sendMsg(env, chatId, "⚠️ <b>Kullanım:</b>\n<code>/al SEMBOL ADET MALİYET [PARA] [SINIF]</code>\nÖrn: <code>/al BIMAS 5 450 TRY bist_katilim</code>", "HTML");
        }
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /sat SEMBOL ADET TOPLAM_TUTAR [PARA]
      // ==========================================
      if (text.startsWith("/sat")) {
        const parts = text.split(/\s+/);
        if (parts.length >= 4) {
          const sembol = parts[1].toUpperCase();
          const satilanAdet = parseFloat(parts[2]);
          const toplamTutar = parseFloat(parts[3]);
          const para = parts[4] ? parts[4].toUpperCase() : "TRY";

          if (isNaN(satilanAdet) || isNaN(toplamTutar) || satilanAdet <= 0 || toplamTutar < 0) {
            await sendMsg(env, chatId, "⚠️ Satılan adet ve toplam tutar geçerli pozitif sayılar olmalıdır.");
            return new Response("OK", { status: 200 });
          }

          let holdings = await getHoldingsData(env);
          let itemIndex = holdings.findIndex(i => (i.sembol || i.kod || "").toUpperCase() === sembol);

          if (itemIndex === -1) {
            await sendMsg(env, chatId, `⚠️ Portföyde <b>${sembol}</b> bulunamadı.`, "HTML");
            return new Response("OK", { status: 200 });
          }

          let targetItem = holdings[itemIndex];
          let mevcutAdet = parseFloat(targetItem.adet || 0);

          if (satilanAdet > mevcutAdet) {
            await sendMsg(env, chatId, `⚠️ Yetersiz adet! Portföyde sadece <code>${mevcutAdet}</code> adet <b>${sembol}</b> var.`, "HTML");
            return new Response("OK", { status: 200 });
          }

          let kalanAdet = Number((mevcutAdet - satilanAdet).toFixed(4));
          let varlikDurumu = "";

          if (kalanAdet <= 0) {
            holdings.splice(itemIndex, 1);
            varlikDurumu = `<b>${sembol}</b> tümüyle satıldı ve listeden çıkarıldı.`;
          } else {
            targetItem.adet = kalanAdet;
            varlikDurumu = `<b>${sembol}</b> kalan adet: <code>${kalanAdet}</code> (Ort. Maliyet: <code>${targetItem.maliyet} ${targetItem.para || 'TRY'}</code>)`;
          }

          const nakitSembol = `NAKIT_${para}`;
          let nakitItem = holdings.find(i => (i.sembol || "").toUpperCase() === nakitSembol);

          if (nakitItem) {
            nakitItem.adet = Number((parseFloat(nakitItem.adet || 0) + toplamTutar).toFixed(2));
          } else {
            holdings.push({
              sembol: nakitSembol,
              sinif: "nakit_para",
              adet: Number(toplamTutar.toFixed(2)),
              maliyet: 1.0,
              para: para
            });
          }

          const guncelNakit = holdings.find(i => (i.sembol || "").toUpperCase() === nakitSembol)?.adet;

          await saveHoldingsData(env, holdings);
          await logAction(env, "SATIŞ", `${sembol} -${satilanAdet} adet -> +${toplamTutar.toFixed(2)} ${para}`);

          let sonucMsg = `💰 <b>Satış İşlendi</b>\n\n` +
                         `Satılan: <code>${satilanAdet}</code> adet <b>${sembol}</b>\n` +
                         `Elde Edilen Tutar: <code>${toplamTutar.toFixed(2)} ${para}</code>\n` +
                         `${varlikDurumu}\n\n` +
                         `💵 <b>${nakitSembol} Bakiyesi:</b> <code>${guncelNakit} ${para}</code>`;

          await sendMsg(env, chatId, sonucMsg, "HTML");
        } else {
          await sendMsg(env, chatId, "⚠️ <b>Kullanım:</b>\n<code>/sat SEMBOL ADET TOPLAM_TUTAR [PARA]</code>\nÖrn: <code>/sat BIMAS 5 2250 TRY</code>", "HTML");
        }
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /cek veya /harca (NAKİT ÇIKIŞI)
      // ==========================================
      if (text.startsWith("/cek") || text.startsWith("/cekme") || text.startsWith("/harca")) {
        const parts = text.split(/\s+/);
        if (parts.length >= 2) {
          const cekilenTutar = parseFloat(parts[1]);
          const para = parts[2] ? parts[2].toUpperCase() : "TRY";

          if (isNaN(cekilenTutar) || cekilenTutar <= 0) {
            await sendMsg(env, chatId, "⚠️ Çekilen tutar geçerli pozitif bir sayı olmalıdır.");
            return new Response("OK", { status: 200 });
          }

          let holdings = await getHoldingsData(env);
          const nakitSembol = `NAKIT_${para}`;
          let nakitIndex = holdings.findIndex(i => (i.sembol || "").toUpperCase() === nakitSembol);

          if (nakitIndex === -1 || parseFloat(holdings[nakitIndex].adet || 0) < balanceCheck(holdings, nakitSembol, cekilenTutar)) {
            const mevcut = nakitIndex !== -1 ? holdings[nakitIndex].adet : 0;
            await sendMsg(env, chatId, `⚠️ Yetersiz bakiye! Mevcut ${nakitSembol}: <code>${mevcut} ${para}</code>`, "HTML");
            return new Response("OK", { status: 200 });
          }

          let kalanNakit = Number((parseFloat(holdings[nakitIndex].adet) - cekilenTutar).toFixed(2));
          if (kalanNakit <= 0) {
            holdings.splice(nakitIndex, 1);
          } else {
            holdings[nakitIndex].adet = kalanNakit;
          }

          await saveHoldingsData(env, holdings);
          await logAction(env, "NAKİT ÇIKIŞI", `-${cekilenTutar.toFixed(2)} ${para} hesaptan çekildi`);

          let sonucMsg = `📤 <b>Nakit Çıkışı Gerçekleşti</b>\n\n` +
                         `Çekilen Tutar: <code>${cekilenTutar.toFixed(2)} ${para}</code>\n` +
                         `Kalan ${nakitSembol}: <code>${kalanNakit} ${para}</code>`;

          await sendMsg(env, chatId, sonucMsg, "HTML");
        } else {
          await sendMsg(env, chatId, "⚠️ <b>Kullanım:</b>\n<code>/cek TUTAR [PARA]</code>\nÖrn: <code>/cek 4500 TRY</code>", "HTML");
        }
        return new Response("OK", { status: 200 });
      }

      // ==========================================
      // KOMUT: /yedek (JSON DÖKÜMÜ)
      // ==========================================
      if (text === "/yedek") {
        const raw = await env.PORTFOLIO_STORE.get("holdings");
        await sendMsg(env, chatId, `📦 <b>Portföy KV Yedeği:</b>\n\n<pre>${raw || "[]"}</pre>`, "HTML");
        return new Response("OK", { status: 200 });
      }

      return new Response("OK", { status: 200 });
    } catch (err) {
      if (chatId) {
        await sendMsg(env, chatId, `❌ İşlem Hatası:\n${err.message}`);
      }
      return new Response("Error", { status: 200 });
    }
  }
};

// ==========================================
// YARDIMCI VE LOG FONKSİYONLARI
// ==========================================
function balanceCheck(holdings, nakitSembol, tutar) {
  const item = holdings.find(i => (i.sembol || "").toUpperCase() === nakitSembol);
  return item && parseFloat(item.adet || 0) >= tutar ? 0 : Infinity;
}

async function getHoldingsData(env) {
  const existing = await env.PORTFOLIO_STORE.get("holdings");
  if (existing) {
    const holdings = JSON.parse(existing);
    if (!Array.isArray(holdings)) {
      throw new Error("KV portföy verisi bir liste değil.");
    }
    return holdings;
  }
  return [];
}

async function saveHoldingsData(env, data) {
  await env.PORTFOLIO_STORE.put("holdings", JSON.stringify(data, null, 2));
}

async function getHistoryData(env) {
  const existing = await env.PORTFOLIO_STORE.get("history");
  if (existing) {
    const history = JSON.parse(existing);
    if (!Array.isArray(history)) {
      throw new Error("KV işlem geçmişi bir liste değil.");
    }
    return history;
  }
  return [];
}

async function logAction(env, tip, detay) {
  try {
    let history = await getHistoryData(env);
    const now = new Date();
    // TSİ (UTC+3) saat formatı
    const tarih = new Intl.DateTimeFormat("tr-TR", {
      timeZone: "Europe/Istanbul",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }).format(now);

    history.push({ tarih, tip, detay });
    // Son 100 işlemi sakla (KV'nin gereksiz şişmesini önlemek için)
    if (history.length > 100) {
      history = history.slice(-100);
    }
    await env.PORTFOLIO_STORE.put("history", JSON.stringify(history, null, 2));
  } catch (e) {
    console.error("Log kaydı hatası:", e);
  }
}

async function sendMsg(env, chatId, text, parseMode = null) {
  const token = env.TELEGRAM_BOT_TOKEN;
  if (!token) throw new Error("TELEGRAM_BOT_TOKEN tanımlı değil.");
  const body = { chat_id: chatId, text: text };
  if (parseMode) body.parse_mode = parseMode;
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Telegram API hatası: HTTP ${response.status}.`);
  }
}
