/* ============================================================
 * 領富 AI - Core JS
 * ============================================================ */

/* LINE 官方帳號（單一來源，要改 ID 只改這裡） */
const LINE_ID  = "@041exgtv";
const LINE_URL = "https://line.me/R/ti/p/@041exgtv";

/* Google Analytics 4 Measurement ID */
const GA_MEASUREMENT_ID = "G-FM7DSZ7V2R";

/* 網站主網域（之後綁自有網域時改這裡） */
const SITE_ORIGIN = "https://leadfuai.com";

const STOCK_DATA = {
  updatedAt: "2026-05-12 09:30",
  stocks: [
    { code: "6488", name: "環球晶", price: 462.5, change: 8.5,  volume: 1245,  category: "半導體",       status: "興櫃" },
    { code: "3552", name: "同致",   price: 178.0, change: -2.0, volume: 320,   category: "電子零組件",   status: "未上市" },
    { code: "6515", name: "穎崴",   price: 1245,  change: 35.0, volume: 88,    category: "半導體",       status: "興櫃" },
    { code: "8038", name: "長園科", price: 92.3,  change: 1.2,  volume: 540,   category: "電池材料",     status: "未上市" },
    { code: "6531", name: "愛普",   price: 1820,  change: -45,  volume: 45,    category: "IC設計",       status: "興櫃" },
    { code: "6770", name: "力積電", price: 28.5,  change: 0.5,  volume: 2850,  category: "晶圓代工",     status: "未上市" },
    { code: "6841", name: "長聖",   price: 215,   change: 5,    volume: 180,   category: "生技醫療",     status: "興櫃" },
    { code: "4174", name: "浩鼎",   price: 320,   change: -8,   volume: 95,    category: "生技醫療",     status: "準上市" },
    { code: "6962", name: "拓凱",   price: 156,   change: 2.5,  volume: 420,   category: "運動器材",     status: "未上市" },
    { code: "8155", name: "博智",   price: 386,   change: 11,   volume: 230,   category: "PCB",          status: "興櫃" },
    { code: "5483", name: "中美晶", price: 132.5, change: -1.5, volume: 680,   category: "半導體",       status: "未上市" },
    { code: "2069", name: "運錩",   price: 56.4,  change: 0.8,  volume: 1100,  category: "鋼鐵",         status: "未上市" },
    { code: "6116", name: "彩晶",   price: 8.95,  change: -0.05,volume: 12500, category: "面板",         status: "準上市" },
    { code: "3265", name: "台星科", price: 88,    change: 1.5,  volume: 380,   category: "半導體封測",   status: "興櫃" },
    { code: "4438", name: "廣越",   price: 245,   change: 4.5,  volume: 145,   category: "紡織成衣",     status: "未上市" },
    { code: "3293", name: "鈊象",   price: 985,   change: 22,   volume: 320,   category: "遊戲軟體",     status: "未上市" },
    { code: "8261", name: "富鼎",   price: 215,   change: -3.5, volume: 280,   category: "電源管理IC",   status: "興櫃" },
    { code: "6679", name: "鈺太",   price: 458,   change: 12,   volume: 165,   category: "IC設計",       status: "未上市" },
    { code: "6196", name: "帆宣",   price: 178,   change: 4.5,  volume: 920,   category: "電子設備",     status: "未上市" },
    { code: "8482", name: "商億-KY",price: 132,   change: -2.5, volume: 220,   category: "家具",         status: "未上市" },
    { code: "6859", name: "頎邦",   price: 78.5,  change: 1.2,  volume: 1850,  category: "半導體封測",   status: "未上市" },
    { code: "3416", name: "融程電", price: 156,   change: 3.5,  volume: 380,   category: "工業電腦",     status: "興櫃" },
    { code: "1597", name: "直得",   price: 92.5,  change: -1.5, volume: 450,   category: "機械",         status: "未上市" },
    { code: "4763", name: "材料-KY",price: 285,   change: 8.5,  volume: 210,   category: "化學材料",     status: "未上市" },
    { code: "6890", name: "宏觀",   price: 165,   change: 2,    volume: 320,   category: "PCB",          status: "興櫃" },
    { code: "6664", name: "群翊",   price: 178,   change: 6,    volume: 280,   category: "電子設備",     status: "未上市" },
    { code: "8358", name: "金居",   price: 92,    change: -0.5, volume: 1450,  category: "PCB銅箔",      status: "未上市" },
    { code: "3373", name: "熱映",   price: 56,    change: 1.5,  volume: 680,   category: "光學元件",     status: "未上市" },
    { code: "3217", name: "優群",   price: 145,   change: 5.5,  volume: 380,   category: "連接器",       status: "興櫃" },
    { code: "6669", name: "緯穎",   price: 2850, change: 65,   volume: 28,    category: "伺服器",       status: "準上市" }
  ],
  news: [
    {
      id: 1, time: "09:25", date: "2026-05-12", tag: "熱門", related: ["6488","6515"],
      title: "外資加碼半導體未上市股，環球晶連三紅",
      author: "領富 AI編輯部 / 記者 王志明",
      body: [
        "【台北報導】未上市股票市場今日延續強勢表現，半導體類股成為焦點。其中環球晶 (6488) 開盤即跳空上漲，盤中最高一度觸及 470 元，最終收在 462.5 元，連續三個交易日收紅。",
        "根據領富 AI統計，外資法人近五個交易日累積買超環球晶超過 1,200 張，買超金額達 5.5 億元，顯示國際資金看好台灣半導體供應鏈的中長期發展。",
        "業內人士分析，環球晶受惠於 AI 伺服器與先進製程晶圓需求大幅成長，12 吋矽晶圓出貨量逐月攀升。法人預估，公司 2026 全年營收可望年增 25% 以上。",
        "另一檔半導體類股穎崴 (6515) 同步走揚，今日上漲 35 元至 1,245 元，創 4 個月新高。穎崴所生產的 Probe Card 為 IC 測試關鍵設備，受惠於 AI 晶片測試需求暴增。",
        "展望後市，分析師建議投資人留意半導體類股的回檔買點，但提醒未上市股票流動性較低，建議分批布局並控管部位。"
      ]
    },
    {
      id: 2, time: "09:10", date: "2026-05-12", tag: "焦點", related: ["6531","6488"],
      title: "AI 概念股延燒至興櫃市場，IC 設計股表現亮眼",
      author: "領富 AI編輯部 / 記者 林佳穎",
      body: [
        "【台北報導】AI 浪潮持續發酵，已從上市櫃市場延燒至興櫃與未上市股票。IC 設計類股今日普遍走高，其中愛普 (6531) 雖小幅回檔，但近一個月仍上漲超過 20%。",
        "業界觀察，AI 應用對高效能運算晶片需求殷切，相關 IC 設計公司訂單能見度延伸至 2027 年。法人指出，這波 AI 行情才剛開始發酵，建議留意尚未大漲的中小型 IC 設計股。",
        "除 IC 設計外，AI 伺服器供應鏈相關個股如博智 (8155)、緯穎 (6669) 等也受到關注。其中緯穎為國際雲端大廠主要供應商，受惠於資料中心擴建潮。"
      ]
    },
    {
      id: 3, time: "08:55", date: "2026-05-12", tag: "公告", related: [],
      title: "金管會公布最新興櫃股票交易規範，5/15 上路",
      author: "領富 AI編輯部",
      body: [
        "【台北報導】金融監督管理委員會今日公布最新興櫃股票交易規範，新制將於 5 月 15 日正式上路。主要變動包括：",
        "1. 興櫃股票漲跌幅由現行 ±5% 放寬至 ±10%",
        "2. 強化資訊揭露要求，興櫃公司須每月公告營收",
        "3. 新增「注意股」公布機制，異常交易將即時警示",
        "4. 簡化興櫃轉上市櫃流程，縮短審查時間",
        "金管會表示，新制有助於提升興櫃市場流動性與透明度，並協助新創企業更快取得資本市場資源。投資人應留意漲跌幅放寬後的波動風險。"
      ]
    },
    {
      id: 4, time: "08:30", date: "2026-05-12", tag: "個股", related: ["4174","6841"],
      title: "生技股財報季登場，浩鼎、長聖獲法人青睞",
      author: "領富 AI編輯部 / 記者 陳冠廷",
      body: [
        "【台北報導】生技類股第一季財報陸續公布，浩鼎 (4174) 與長聖 (6841) 表現超出市場預期，吸引法人買盤進駐。",
        "浩鼎 2026 年第一季營收年增 35%，主要來自於海外授權金挹注。執行長表示，多項臨床試驗進度順利，預計下半年將有重要里程碑。",
        "長聖在細胞治療領域持續突破，第一季已有 3 件 CDMO 訂單入帳。法人預估全年營收可望突破 8 億元。",
        "生技股近期成為市場焦點，建議投資人聚焦在有實際營收、本益比合理的個股。"
      ]
    },
    {
      id: 5, time: "昨日", date: "2026-05-11", tag: "週評", related: [],
      title: "未上市股市週評：成交量回升 15%，買盤轉趨積極",
      author: "領富 AI研究部",
      body: [
        "【週評】上週未上市股票市場成交量較前週回升 15%，買盤轉趨積極，顯示市場信心逐步恢復。",
        "類股表現方面，半導體類股漲幅居前，週漲幅達 5.2%；其次為生技醫療 (3.8%) 與電池材料 (3.1%)。下跌類股則以紡織成衣 (-1.2%) 為主。",
        "外資動向方面，本週前三大買超分別為環球晶、博智、長聖，賣超則集中於部分傳產類股。",
        "本週重點觀察：(1) 5/15 興櫃漲跌幅放寬政策上路影響、(2) 浩鼎、彩晶 IPO 抽籤、(3) 第一季財報全面公布。"
      ]
    },
    {
      id: 6, time: "昨日", date: "2026-05-11", tag: "抽籤", related: ["4174","6116"],
      title: "新股申購：兩檔興櫃股下週開放抽籤",
      author: "領富 AI編輯部",
      body: [
        "【台北報導】下週將有兩檔興櫃股票開放申購，分別為浩鼎 (4174) 與彩晶 (6116)。",
        "浩鼎承銷價訂為 305 元，5/18 起開放申購，5/20 截止，預計中籤率約 0.85%。彩晶承銷價 8.5 元，5/20 起申購，5/22 截止，中籤率約 1.2%。",
        "兩檔個股近期成交價均高於承銷價，預期中籤後可享有不錯的價差空間。投資人可至往來券商或銀行通路申購，手續費為 20 元/件。"
      ]
    },
    {
      id: 7, time: "07:50", date: "2026-05-12", tag: "個股", related: ["8038"],
      title: "電動車電池材料漲價，長園科盤前競價走高 5%",
      author: "領富 AI即時新聞",
      body: [
        "【即時】受國際鋰電池材料報價上漲影響，長園科 (8038) 今日盤前競價一度上漲 5%。",
        "公司主力產品磷酸鋰鐵 (LFP) 與三元正極材料近期受惠於電動車與儲能市場需求，產能利用率維持高檔。",
        "法人預估，第二季產品平均售價有望調漲 3-5%，將直接挹注獲利表現。"
      ]
    },
    {
      id: 8, time: "07:30", date: "2026-05-12", tag: "公告", related: [],
      title: "5/15 起興櫃股票漲跌幅放寬至 ±10%，影響評估",
      author: "領富 AI研究部",
      body: [
        "【深度分析】金管會宣布興櫃股票漲跌幅將於 5/15 由 ±5% 放寬至 ±10%，市場關注此舉對交易行為與股價波動的影響。",
        "短期影響：預期股價波動將加大，部分流動性較低的個股可能出現劇烈震盪。",
        "中長期影響：(1) 提升交易效率，價格發現機制更完善；(2) 吸引更多投資人參與；(3) 部分公司可能加速申請轉上市櫃。",
        "投資建議：(1) 降低融資槓桿；(2) 設定停損停利；(3) 留意爆量爆漲爆跌個股的風險。"
      ]
    },
    {
      id: 9, time: "5/11", date: "2026-05-11", tag: "週評", related: [],
      title: "週評：未上市加權指數收 312.5 點，週漲 1.8%",
      author: "領富 AI研究部",
      body: [
        "【週評】領富 AI自編未上市加權指數本週收在 312.5 點，週漲幅 1.8%。其中半導體類股貢獻最大，佔指數漲幅 60% 以上。",
        "技術面觀察，指數已連續 3 週收紅，月線、季線皆呈現上揚走勢，中長期多頭格局確立。",
        "投資人情緒指標方面，領富 AI討論區看多比例升至 62%，創 6 個月新高。"
      ]
    },
    {
      id: 10, time: "5/11", date: "2026-05-11", tag: "個股", related: ["6962"],
      title: "拓凱受惠國際品牌訂單回升，毛利率連兩季提升",
      author: "領富 AI編輯部",
      body: [
        "【台北報導】拓凱 (6962) 公布第一季財報，毛利率較去年同期提升 2.3 個百分點，主要受惠於國際運動品牌訂單回升。",
        "公司主力產品為高階自行車安全帽與球拍，主要客戶包括歐美知名品牌。第二季在手訂單能見度已達 80%。"
      ]
    }
  ],
  hotTopics: [
    "AI 伺服器供應鏈", "半導體先進製程", "電動車電池材料", "生技新藥",
    "低軌衛星", "重電族群", "PCB 載板", "面板雙虎"
  ],
  // 個股詳情資料：基本資料、財務、K 線、相關討論
  details: {
    "6488": {
      fullName: "環球晶圓股份有限公司",
      english: "GlobalWafers Co., Ltd.",
      industry: "半導體 - 矽晶圓",
      founded: "2011-10",
      capital: "43.6 億",
      chairman: "徐秀蘭",
      president: "徐秀蘭",
      address: "新竹科學園區創新一路 8 號",
      phone: "(03) 552-1888",
      website: "globalwafers.com",
      employees: 7800,
      mainProduct: "12 吋、8 吋、6 吋矽晶圓",
      financials: { revenue: 752.3, netProfit: 168.2, eps: 38.6, bps: 152.4, pe: 11.98, pb: 3.03, roe: 25.4 },
      kline: [430, 435, 442, 438, 445, 451, 448, 454, 461, 458, 463, 459, 465, 462, 470, 462.5],
      announcements: [
        { date: "2026-05-10", title: "公告本公司董事會決議分派 2025 年度現金股利每股 12 元" },
        { date: "2026-05-05", title: "公告本公司 2026 年第一季合併財務報告" },
        { date: "2026-04-28", title: "公告本公司股東常會召開日期" }
      ]
    },
    "6515": {
      fullName: "穎崴科技股份有限公司",
      english: "WinWay Technology Co., Ltd.",
      industry: "半導體 - 測試介面",
      founded: "2002-03",
      capital: "4.2 億",
      chairman: "王嘉煌",
      president: "王嘉煌",
      address: "新竹市科學園區力行二路 8 號",
      phone: "(03) 666-8868",
      website: "winwayglobal.com",
      employees: 580,
      mainProduct: "IC 測試介面、Probe Card",
      financials: { revenue: 32.5, netProfit: 8.6, eps: 20.5, bps: 125.6, pe: 60.7, pb: 9.91, roe: 16.3 },
      kline: [1180, 1195, 1210, 1205, 1220, 1235, 1228, 1240, 1255, 1248, 1232, 1245, 1260, 1250, 1238, 1245],
      announcements: [
        { date: "2026-05-08", title: "公告本公司 2026 年 4 月份合併營收" },
        { date: "2026-04-30", title: "公告本公司董事會通過第一季財報" }
      ]
    },
    "6770": {
      fullName: "力晶積成電子製造股份有限公司",
      english: "Powerchip Semiconductor Manufacturing Corporation",
      industry: "晶圓代工",
      founded: "2019-05",
      capital: "412 億",
      chairman: "黃崇仁",
      president: "黃崇仁",
      address: "新竹科學園區力行路 12 號",
      phone: "(03) 567-8898",
      website: "psmc.com",
      employees: 6500,
      mainProduct: "12 吋晶圓代工、DRAM、Logic IC",
      financials: { revenue: 485.6, netProfit: 25.3, eps: 0.62, bps: 28.5, pe: 45.97, pb: 1.0, roe: 2.18 },
      kline: [26.5, 27.0, 27.8, 28.2, 27.9, 28.5, 29.1, 28.6, 28.9, 28.3, 28.7, 29.2, 28.8, 28.4, 28.6, 28.5],
      announcements: [
        { date: "2026-05-09", title: "公告本公司 2026 年 4 月份合併營收" },
        { date: "2026-05-03", title: "公告本公司董事會通過資本支出案" }
      ]
    }
  },
  // IPO / 抽籤資料
  ipoCalendar: [
    { code: "4174", name: "浩鼎",   listPrice: 305, openDate: "2026-05-18", closeDate: "2026-05-20", market: "上市", odds: "0.85%" },
    { code: "6116", name: "彩晶",   listPrice: 8.5, openDate: "2026-05-20", closeDate: "2026-05-22", market: "上櫃", odds: "1.20%" },
    { code: "6770", name: "力積電", listPrice: 30,  openDate: "預計 6 月",  closeDate: "-",          market: "上市", odds: "-" },
    { code: "8155", name: "博智",   listPrice: 380, openDate: "預計 7 月",  closeDate: "-",          market: "上櫃", odds: "-" }
  ],
  // 全部公司公告
  announcements: [
    { date: "2026-05-10", code: "6488", name: "環球晶", title: "公告本公司董事會決議分派 2025 年度現金股利每股 12 元", type: "股利" },
    { date: "2026-05-09", code: "6770", name: "力積電", title: "公告本公司 2026 年 4 月份合併營收", type: "營收" },
    { date: "2026-05-08", code: "6515", name: "穎崴",   title: "公告本公司 2026 年 4 月份合併營收", type: "營收" },
    { date: "2026-05-08", code: "6841", name: "長聖",   title: "公告本公司董事會決議現金增資新股發行", type: "增資" },
    { date: "2026-05-07", code: "4174", name: "浩鼎",   title: "公告本公司召開法人說明會", type: "法說會" },
    { date: "2026-05-06", code: "8038", name: "長園科", title: "公告本公司簽訂重大合約", type: "合約" },
    { date: "2026-05-05", code: "6488", name: "環球晶", title: "公告本公司 2026 年第一季合併財務報告", type: "財報" },
    { date: "2026-05-05", code: "6531", name: "愛普",   title: "公告本公司更換會計師", type: "公司治理" },
    { date: "2026-05-04", code: "3265", name: "台星科", title: "公告本公司董事會通過買回庫藏股", type: "庫藏股" },
    { date: "2026-05-03", code: "6770", name: "力積電", title: "公告本公司董事會通過資本支出案", type: "重大訊息" },
    { date: "2026-05-02", code: "8155", name: "博智",   title: "公告本公司股東常會召開日期", type: "股東會" },
    { date: "2026-05-01", code: "6962", name: "拓凱",   title: "公告本公司 2026 年 4 月份合併營收", type: "營收" }
  ]
};

/* ============================================================
 * Utils
 * ============================================================ */
function pctChange(price, change) {
  const prev = price - change;
  if (prev <= 0) return 0;
  return (change / prev) * 100;
}
function fmtPrice(v) {
  return Number(v).toLocaleString("zh-TW", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtChange(v) {
  const s = v > 0 ? "+" : "";
  return s + Number(v).toLocaleString("zh-TW", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(v) {
  const s = v > 0 ? "+" : "";
  return s + v.toFixed(2) + "%";
}
function changeClass(c) {
  if (c > 0) return "up";
  if (c < 0) return "down";
  return "flat";
}
function arrow(c) {
  if (c > 0) return "▲";
  if (c < 0) return "▼";
  return "－";
}
function findStock(code) {
  return STOCK_DATA.stocks.find(s => s.code === code);
}
function relativePath(file) {
  // 根據目前頁面位置回傳正確相對路徑（首頁 vs pages/）
  const inPages = location.pathname.includes("/pages/");
  return inPages ? file : (file.startsWith("pages/") ? file : "pages/" + file);
}
function homeHref() {
  return location.pathname.includes("/pages/") ? "../index.html" : "index.html";
}
function pageHref(file) {
  return location.pathname.includes("/pages/") ? file : "pages/" + file;
}

/* ============================================================
 * 自選股（localStorage）
 * ============================================================ */
const WATCHLIST_KEY = "berich_watchlist";
function getWatchlist() {
  try { return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || "[]"); }
  catch { return []; }
}
function addToWatchlist(code) {
  const list = getWatchlist();
  if (!list.includes(code)) {
    list.push(code);
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
  }
}
function removeFromWatchlist(code) {
  const list = getWatchlist().filter(c => c !== code);
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
}
function isInWatchlist(code) {
  return getWatchlist().includes(code);
}

/* ============================================================
 * 今日日期 (top bar)
 * ============================================================ */
function renderDate() {
  const el = document.getElementById("todayDate");
  if (!el) return;
  const d = new Date();
  const w = ["日", "一", "二", "三", "四", "五", "六"];
  el.textContent = `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,"0")}/${d.getDate().toString().padStart(2,"0")} (週${w[d.getDay()]})`;
}

/* ============================================================
 * 跑馬燈
 * ============================================================ */
function renderTicker() {
  const track = document.getElementById("tickerTrack");
  if (!track) return;
  // 效能優化：原本渲染全部 887 檔 × 2 份 = 1774 個 DOM 節點，
  // 加上 JS RAF 每幀讀 scrollWidth (強制 reflow)，會把 CPU 拉到 100%。
  // 改為只顯示成交量前 30 名 + CSS animation（GPU 合成、不觸發 reflow）
  const topStocks = STOCK_DATA.stocks
    .filter(s => s.price > 0)
    .sort((a, b) => (b.volume || 0) - (a.volume || 0))
    .slice(0, 30);
  const items = topStocks.map(s => {
    const cls = changeClass(s.change);
    return `<span class="tk-item" data-code="${s.code}">
      <a href="${pageHref('stock-detail.html?code=' + s.code)}" style="color:inherit;text-decoration:none;">
        <span class="tk-code">${s.code} ${s.name}</span>
        <span class="tk-price">${fmtPrice(s.price)}</span>
        <span class="${cls}">${arrow(s.change)} ${fmtChange(s.change)}</span>
      </a>
    </span>`;
  }).join("");
  // 雙份內容塞進 .ticker-inner，由 CSS @keyframes ticker-scroll 做 translateX(-50%) 無縫循環
  track.innerHTML = `<div class="ticker-inner">${items}${items}</div>`;
}

/* ============================================================
 * 首頁股票表格
 * ============================================================ */
let currentFilter = "all";

function renderStockTable() {
  const tbody = document.getElementById("stockTbody");
  if (!tbody) return;
  const list = currentFilter === "all"
    ? STOCK_DATA.stocks
    : STOCK_DATA.stocks.filter(s => s.status === currentFilter);

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="loading">沒有符合條件的個股</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(s => {
    const pct = pctChange(s.price, s.change);
    const cls = changeClass(s.change);
    const inFav = isInWatchlist(s.code);
    return `<tr data-code="${s.code}">
      <td class="code"><a href="${pageHref('stock-detail.html?code=' + s.code)}">${s.code}</a></td>
      <td class="name"><a href="${pageHref('stock-detail.html?code=' + s.code)}" style="color:inherit;">${s.name}</a></td>
      <td class="num ${cls}">${fmtPrice(s.price)}</td>
      <td class="num ${cls}">${arrow(s.change)} ${fmtChange(s.change)}</td>
      <td class="num ${cls}">${fmtPct(pct)}</td>
      <td class="num">${s.volume.toLocaleString("zh-TW")}</td>
      <td>${s.category}</td>
      <td><span class="status-pill status-${s.status}">${s.status}</span></td>
      <td><button class="add-btn ${inFav ? 'in-fav' : ''}" data-code="${s.code}">${inFav ? '✓ 已加入' : '＋自選'}</button></td>
    </tr>`;
  }).join("");

  const ts = document.getElementById("updatedAt");
  if (ts) ts.textContent = STOCK_DATA.updatedAt;
}

function bindTabs() {
  document.querySelectorAll(".panel-tabs .tab").forEach(btn => {
    if (!btn.dataset.filter) return;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".panel-tabs .tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderStockTable();
    });
  });
}

function bindAddFavBtns() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".add-btn");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const code = btn.dataset.code;
    const s = findStock(code);
    const name = s ? s.name : code;
    if (isInWatchlist(code)) {
      removeFromWatchlist(code);
      btn.textContent = "＋自選";
      btn.classList.remove("in-fav");
      showToast(`已從自選移除 ${name}`, "info");
    } else {
      addToWatchlist(code);
      btn.textContent = "✓ 已加入";
      btn.classList.add("in-fav");
      showToast(`✓ 已加入自選：${name}`, "success");
    }
  });
}

/* 手機版：整列卡片可點擊跳轉個股 */
function bindMobileRowTap() {
  document.addEventListener("click", (e) => {
    if (window.innerWidth > 768) return;
    const tr = e.target.closest(".stock-table tr[data-code]");
    if (!tr) return;
    // 不要攔截真實連結與按鈕
    if (e.target.closest("a, button")) return;
    const code = tr.dataset.code;
    if (code) location.href = pageHref("stock-detail.html?code=" + code);
  });
}

/* ============================================================
 * 新聞 / 熱門題材
 * ============================================================ */
function renderNews() {
  const ul = document.getElementById("newsList");
  if (!ul) return;
  ul.innerHTML = STOCK_DATA.news.slice(0, 6).map(n => `
    <li>
      <span class="news-time">${n.time}</span>
      <span class="news-tag ${n.tag}">${n.tag}</span>
      <a class="news-title" href="${pageHref('news-detail.html?id=' + n.id)}">${n.title}</a>
    </li>
  `).join("");
}
function renderTopics() {
  const ul = document.getElementById("topicList");
  if (!ul) return;
  ul.innerHTML = STOCK_DATA.hotTopics.map(t => `<li># ${t}</li>`).join("");
}

/* ============================================================
 * 搜尋 → 跳轉個股詳情
 * ============================================================ */
// 中文數字 → 阿拉伯數字（給語音搜尋用：「六四八八」→ 6488）
const _CN_DIGIT_MAP = {
  "零":"0","〇":"0","○":"0","０":"0",
  "一":"1","壹":"1","ㄧ":"1",
  "二":"2","貳":"2","兩":"2",
  "三":"3","參":"3","叁":"3",
  "四":"4","肆":"4",
  "五":"5","伍":"5",
  "六":"6","陸":"6","陆":"6",
  "七":"7","柒":"7",
  "八":"8","捌":"8",
  "九":"9","玖":"9"
};

function normalizeSearchQuery(text) {
  if (!text) return "";
  // 1. 去全部空白
  text = text.replace(/\s+/g, "");
  // 2. 去句末標點（語音常會加 「。」「，」「？」）
  text = text.replace(/[。，、？！．.,?!]+$/g, "");
  // 3. 去常見語音尾巴（「環球晶股票」→ 環球晶）
  text = text.replace(/(的)?(股票|股價|股價多少|怎麼樣|股|公司|代號|代碼)$/g, "");
  // 4. 整串都是中文數字（3-5 字）→ 轉阿拉伯（給股票代號用）
  if (/^[零〇○０一壹ㄧ二貳兩三參叁四肆五伍六陸陆七柒八捌九玖]{3,5}$/.test(text)) {
    text = text.split("").map(c => _CN_DIGIT_MAP[c] || c).join("");
  }
  return text;
}

function bindSearch() {
  const input = document.getElementById("stockSearch");
  const btn = document.getElementById("searchBtn");
  if (!input || !btn) return;

  function doSearch() {
    let q = input.value.trim();
    if (!q) return;
    // 智慧正規化（手打也吃，例如打成「6488 」尾巴空白也清掉）
    const nq = normalizeSearchQuery(q);
    if (nq && nq !== q) input.value = nq, q = nq;

    // 1. 完全符合代號 → 跳個股
    const exact = STOCK_DATA.stocks.find(s => s.code === q);
    if (exact) { location.href = pageHref('stock-detail.html?code=' + exact.code); return; }

    // 2. 完全符合公司名稱 → 跳個股
    const exactName = STOCK_DATA.stocks.find(s => s.name === q);
    if (exactName) { location.href = pageHref('stock-detail.html?code=' + exactName.code); return; }

    // 3. 公司名稱開頭含查詢字串（例如「環球晶」→ 環球晶圓）→ 唯一結果直接跳
    const startsWith = STOCK_DATA.stocks.filter(s => s.name.startsWith(q));
    if (startsWith.length === 1) { location.href = pageHref('stock-detail.html?code=' + startsWith[0].code); return; }

    // 4. 部分包含（任何位置）→ 唯一結果直接跳
    const includes = STOCK_DATA.stocks.filter(s => s.name.includes(q) || s.code.includes(q));
    if (includes.length === 1) { location.href = pageHref('stock-detail.html?code=' + includes[0].code); return; }

    // 5. 多結果或全無 → 進搜尋頁
    location.href = pageHref('search.html?q=' + encodeURIComponent(q));
  }
  btn.addEventListener("click", doSearch);
  input.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
}

/* ============================================================
 * 🎤 語音搜尋（Web Speech API，免費、瀏覽器內建、繁中支援）
 * - 每個 .search-box 自動注入麥克風按鈕（不用改 HTML）
 * - 手機優先：按鈕加大、全螢幕聆聽視覺
 * - HTTPS only（leadfuai.com 已是 HTTPS，沒問題）
 * ============================================================ */
let _activeRecognition = null;

function setupVoiceSearch() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;   // 老瀏覽器不支援就靜默跳過，不影響其他功能

  document.querySelectorAll(".search-box").forEach(box => {
    if (box.querySelector(".voice-mic")) return;  // 已注入過跳過
    const input = box.querySelector("input");
    const submitBtn = box.querySelector("button");
    if (!input) return;

    const mic = document.createElement("button");
    mic.type = "button";
    mic.className = "voice-mic";
    mic.setAttribute("aria-label", "語音搜尋");
    mic.title = "語音搜尋（點麥克風開始）";
    mic.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5.91-3a.91.91 0 0 0-.91.91A4.99 4.99 0 0 1 12 17a4.99 4.99 0 0 1-5-5.09.91.91 0 1 0-1.82 0A6.81 6.81 0 0 0 11 18.91V21a1 1 0 1 0 2 0v-2.09a6.81 6.81 0 0 0 5.82-6.91.91.91 0 0 0-.91-.91z"/></svg>`;

    // 放在「查詢」按鈕之前，視覺順序：[ 輸入框 ][🎤][ 查詢 ]
    if (submitBtn) box.insertBefore(mic, submitBtn);
    else box.appendChild(mic);

    mic.addEventListener("click", () => startVoiceRecognition(input, submitBtn));
  });

  // 第一次來的使用者：發提示動畫一次（5 秒），告訴他「這裡新功能」
  if (!localStorage.getItem("leadfu_voice_hint_seen")) {
    setTimeout(() => {
      const firstMic = document.querySelector(".voice-mic");
      if (firstMic) {
        firstMic.classList.add("voice-mic-pulse-hint");
        setTimeout(() => firstMic.classList.remove("voice-mic-pulse-hint"), 5000);
        localStorage.setItem("leadfu_voice_hint_seen", "1");
      }
    }, 2500);
  }
}

function startVoiceRecognition(input, submitBtn) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;

  // 已經在聽就中止（再點一次=取消）
  if (_activeRecognition) {
    try { _activeRecognition.abort(); } catch (e) {}
    _activeRecognition = null;
    return;
  }

  const recog = new SR();
  recog.lang = "zh-TW";
  recog.continuous = false;
  recog.interimResults = true;
  recog.maxAlternatives = 1;
  _activeRecognition = recog;

  const overlay = _createVoiceOverlay(() => {
    if (_activeRecognition) {
      try { _activeRecognition.abort(); } catch (e) {}
      _activeRecognition = null;
    }
  });

  let finalText = "";

  recog.onresult = (e) => {
    let text = "";
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
    // 智慧正規化：去空白/標點、移除常見尾巴（「股票」「股價」）、中文數字轉阿拉伯
    // 例：聽到「六四八八」→ 6488，聽到「環球晶股票」→ 環球晶
    text = normalizeSearchQuery(text);
    overlay.setHeard(text);
    if (e.results[e.results.length - 1].isFinal) finalText = text;
  };

  recog.onerror = (e) => {
    const msg = e.error === "no-speech" ? "沒有聽到聲音，請再試一次"
              : e.error === "not-allowed" ? "請允許麥克風權限後重試"
              : e.error === "audio-capture" ? "找不到麥克風"
              : "語音辨識失敗，請改用打字";
    overlay.setError(msg);
    setTimeout(() => overlay.close(), 2000);
    _activeRecognition = null;
  };

  recog.onend = () => {
    _activeRecognition = null;
    if (finalText) {
      input.value = finalText;
      overlay.setSuccess(finalText);
      setTimeout(() => {
        overlay.close();
        if (submitBtn) submitBtn.click();
      }, 900);
    } else {
      // onend 沒拿到 final（可能用戶取消）
      overlay.close();
    }
  };

  try {
    recog.start();
  } catch (err) {
    overlay.setError("啟動失敗，請改用打字");
    setTimeout(() => overlay.close(), 1500);
    _activeRecognition = null;
  }
}

function _createVoiceOverlay(onCancel) {
  const el = document.createElement("div");
  el.className = "voice-overlay";
  el.innerHTML = `
    <div class="voice-overlay-box">
      <div class="voice-pulse"><div class="voice-pulse-dot">🎤</div></div>
      <div class="voice-overlay-status">正在聆聽...</div>
      <div class="voice-overlay-text">請說股票代號或公司名稱</div>
      <button class="voice-overlay-cancel" type="button">取消</button>
    </div>
  `;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));

  const statusEl = el.querySelector(".voice-overlay-status");
  const textEl = el.querySelector(".voice-overlay-text");

  el.querySelector(".voice-overlay-cancel").addEventListener("click", () => {
    onCancel && onCancel();
    closeOverlay();
  });

  function closeOverlay() {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 220);
  }

  return {
    setHeard: (t) => {
      if (t) {
        statusEl.textContent = "聽到了：";
        textEl.textContent = `「${t}」`;
        textEl.classList.add("voice-overlay-text--heard");
      }
    },
    setSuccess: (t) => {
      statusEl.textContent = "✅ 已搜尋：";
      textEl.textContent = `「${t}」`;
      textEl.classList.add("voice-overlay-text--heard");
    },
    setError: (msg) => {
      statusEl.textContent = "⚠ " + msg;
      textEl.textContent = "";
      el.querySelector(".voice-pulse").style.display = "none";
    },
    close: closeOverlay
  };
}

/* ============================================================
 * AI 佔位區塊（之後接 Claude API）
 * ============================================================ */
function bindAiPlaceholders() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".ai-trigger");
    if (!btn) return;
    const target = document.querySelector(btn.dataset.target);
    if (!target) return;
    const action = btn.dataset.action || "analyze";
    target.innerHTML = `<div class="ai-loading"><span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span> AI 分析中...</div>`;
    setTimeout(() => {
      target.innerHTML = window.LeadFu.mockAiResponse(action, btn.dataset.code);
    }, 1200);
  });
}

function mockAiResponse(action, code) {
  // ⚠ 佔位 mock。重要：AI 內容一律「中性整理公開資料」，不得出現買進/賣出/評等等推介字眼
  //    （台灣《證券投資信託及顧問法》：未取得投顧執照不得做個股推介建議）
  //    之後串 Claude API 時，prompt 也須遵守此原則
  const s = code ? findStock(code) : null;
  if (action === "stockAnalyze" && s) {
    const pct = pctChange(s.price, s.change);
    const dir = s.change > 0 ? "上漲" : (s.change < 0 ? "下跌" : "持平");
    return `
      <div class="ai-result">
        <div class="ai-result-head">📋 AI 個股資料摘要（範例）</div>
        <p><strong>${s.code} ${s.name}</strong>（${s.category}・${s.status}）目前報價 ${fmtPrice(s.price)}，今日${dir} ${fmtPct(pct)}。</p>
        <p><strong>成交概況：</strong>今日成交量 ${s.volume.toLocaleString()} 張，於興櫃個股中屬${s.volume > 500 ? "成交較活躍" : "成交一般"}。</p>
        <p><strong>產業別：</strong>歸類於 ${s.category}。本摘要僅彙整公開數據，未對個股做任何評價或判斷。</p>
        <p><strong>風險提醒：</strong>${s.status === "未上市" ? "未上市股票無集中市場、流動性低、價格不透明" : "興櫃股票漲跌幅較大"}，買賣應透過合法券商辦理。</p>
        <p class="ai-disclaimer">※ 本內容為 AI 整理之公開資料摘要，不構成投資建議或推介，亦非證券投資顧問服務。投資決策與風險請自行評估。</p>
      </div>`;
  }
  if (action === "newsSummary") {
    return `
      <div class="ai-result">
        <div class="ai-result-head">📋 AI 新聞摘要（範例）</div>
        <p>今日財經新聞主題包含半導體供應鏈、生技股財報季，以及金管會興櫃交易新規等。</p>
        <p>本摘要僅彙整公開新聞之標題與重點，完整內容請點各則新聞連結至原始來源閱讀。</p>
        <p class="ai-disclaimer">※ 由 AI 自動彙整公開新聞重點，不代表本站立場，亦不構成投資建議。</p>
      </div>`;
  }
  if (action === "threadSummary") {
    return `
      <div class="ai-result">
        <div class="ai-result-head">📋 AI 討論區重點（範例）</div>
        <p>今日討論區較多人討論的主題包含個股觀察、新股申購、以及興櫃交易制度變動等。</p>
        <p>以下為使用者公開發言之整理，內容為網友個人意見，不代表本站立場。</p>
        <p class="ai-disclaimer">※ 由 AI 彙整討論區公開發言，僅供參考，不構成投資建議。</p>
      </div>`;
  }
  return `<div class="ai-result"><p>AI 服務尚未開啟（佔位）。</p></div>`;
}

/* ============================================================
 * 底部 Tab Bar（手機版）
 * ============================================================ */
function setupBottomTabBar() {
  if (document.querySelector(".bottom-tab-bar")) return;

  const inPages = location.pathname.includes("/pages/");
  const prefix = inPages ? "" : "pages/";
  const home   = inPages ? "../index.html" : "index.html";

  const tabs = [
    { label: "首頁",   icon: "🏠", href: home,                       match: /index\.html$|\/$/ },
    { label: "行情",   icon: "📊", href: prefix + "stocks.html",     match: /stocks\.html|stock-detail\.html|industries\.html/ },
    { label: "選股",   icon: "🔍", href: prefix + "screener.html",   match: /screener\.html|search\.html/ },
    { label: "自選",   icon: "⭐", href: prefix + "watchlist.html",  match: /watchlist\.html/ },
    { label: "我的",   icon: "👤", href: prefix + "member.html",     match: /member\.html|login\.html|register\.html|vip\.html/ }
  ];

  const bar = document.createElement("nav");
  bar.className = "bottom-tab-bar";
  bar.setAttribute("aria-label", "底部導航");
  bar.innerHTML = tabs.map(t => {
    const active = t.match.test(location.pathname) ? "active" : "";
    return `<a href="${t.href}" class="${active}">
      <span class="tab-icon">${t.icon}</span>
      <span class="tab-label">${t.label}</span>
    </a>`;
  }).join("");
  document.body.appendChild(bar);
}

/* ============================================================
 * SEO：動態 canonical + Open Graph + JSON-LD
 * 每個頁面自動寫入正確的 canonical URL 與 og 標籤
 * ============================================================ */
function setupSEO() {
  const url = SITE_ORIGIN + location.pathname + location.search;
  const head = document.head;

  function ensureMeta(selector, create) {
    let el = head.querySelector(selector);
    if (!el) {
      el = create();
      head.appendChild(el);
    }
    return el;
  }

  // canonical
  ensureMeta('link[rel="canonical"]', () => {
    const l = document.createElement("link");
    l.rel = "canonical";
    return l;
  }).href = url;

  // og:url
  ensureMeta('meta[property="og:url"]', () => {
    const m = document.createElement("meta");
    m.setAttribute("property", "og:url");
    return m;
  }).setAttribute("content", url);

  // og:title (用 document.title，每頁不同)
  ensureMeta('meta[property="og:title"]', () => {
    const m = document.createElement("meta");
    m.setAttribute("property", "og:title");
    return m;
  }).setAttribute("content", document.title);

  // og:site_name
  ensureMeta('meta[property="og:site_name"]', () => {
    const m = document.createElement("meta");
    m.setAttribute("property", "og:site_name");
    return m;
  }).setAttribute("content", "領富 AI");

  // og:image fallback
  if (!head.querySelector('meta[property="og:image"]')) {
    const m = document.createElement("meta");
    m.setAttribute("property", "og:image");
    m.setAttribute("content", SITE_ORIGIN + "/icons/icon-512.png");
    head.appendChild(m);
  }

  // og:type
  ensureMeta('meta[property="og:type"]', () => {
    const m = document.createElement("meta");
    m.setAttribute("property", "og:type");
    return m;
  }).setAttribute("content", "website");
}

/* ============================================================
 * Google Analytics 4
 * 拿到 Measurement ID 後在 GA_MEASUREMENT_ID 替換即生效
 * ============================================================ */
function loadGA() {
  if (!GA_MEASUREMENT_ID || GA_MEASUREMENT_ID === "G-XXXXXXXXXX") return;

  // 載入 gtag.js
  const s = document.createElement("script");
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  window.gtag("js", new Date());
  window.gtag("config", GA_MEASUREMENT_ID, {
    page_path: location.pathname + location.search
  });

  console.log("[領富 AI] ✅ GA4 已載入");
}

/* ============================================================
 * 全站切割聲明（合規）— 注入到 footer 上方，每頁都有
 * 明示「純資訊平台、不介入交易」，符合未上市股票資訊網的法律定位
 * ============================================================ */
function setupDisclaimer() {
  if (document.querySelector(".site-disclaimer")) return;
  const footer = document.querySelector(".site-footer");
  if (!footer) return;

  const fraudHref = pageHref("fraud-alert.html");
  const bar = document.createElement("div");
  bar.className = "site-disclaimer";
  bar.innerHTML = `
    <div class="container">
      <span class="disc-icon">⚠</span>
      <span>
        <strong>領富 AI 為未上市／興櫃股票公開資訊整理平台。</strong>
        本站<strong>不介入任何股票買賣、不撮合交易、不代為下單或過戶、不收受投資款項</strong>，
        亦非證券投資顧問事業。所有內容（含 AI 功能）僅為公開資料之整理與摘要，不構成投資建議。
        未上市股票買賣應透過合法券商辦理，謹防詐騙 — 請參閱
        <a href="${fraudHref}">投資人防詐須知</a>。
      </span>
    </div>`;
  footer.parentNode.insertBefore(bar, footer);
}

/* ============================================================
 * PWA 註冊 + 安裝提示橫幅
 * ============================================================ */
function setupPWA() {
  // 註冊 Service Worker（離線快取 + 加到主畫面前置）
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" })
      .then(() => console.log("[領富 AI] ✅ Service Worker 已註冊"))
      .catch(e => console.log("[領富 AI] SW 註冊失敗:", e.message));
  }

  // 安裝提示流程
  let deferredPrompt = null;
  const DISMISS_KEY = "leadfu_pwa_dismissed_until";

  // 已在 PWA standalone 模式 → 已安裝，不顯示
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  if (isStandalone) return;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // 7 天內關過就不再煩
    const dismissedUntil = parseInt(localStorage.getItem(DISMISS_KEY) || "0", 10);
    if (Date.now() < dismissedUntil) return;

    // 延 4 秒再跳，讓使用者先看到內容
    setTimeout(showInstallBanner, 4000);
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    hideInstallBanner();
    showToast("✓ 已加到主畫面，下次直接從手機桌面開", "success");
  });

  function showInstallBanner() {
    if (document.getElementById("pwaInstallBanner")) return;
    const banner = document.createElement("div");
    banner.id = "pwaInstallBanner";
    banner.className = "pwa-install-banner";
    banner.innerHTML = `
      <div class="pwa-icon">📱</div>
      <div class="pwa-text">
        <strong>加到主畫面</strong>
        <small>當 app 用，下次一鍵打開</small>
      </div>
      <button id="pwaInstallBtn">安裝</button>
      <button class="pwa-dismiss" id="pwaDismissBtn" aria-label="關閉">✕</button>
    `;
    document.body.appendChild(banner);
    requestAnimationFrame(() => banner.classList.add("show"));

    banner.querySelector("#pwaInstallBtn").addEventListener("click", async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      const result = await deferredPrompt.userChoice;
      deferredPrompt = null;
      hideInstallBanner();
      if (result.outcome === "dismissed") {
        // 用戶在系統 prompt 取消 → 暫停 3 天
        localStorage.setItem(DISMISS_KEY, (Date.now() + 3 * 86400000).toString());
      }
    });
    banner.querySelector("#pwaDismissBtn").addEventListener("click", () => {
      // 主動關 → 暫停 7 天
      localStorage.setItem(DISMISS_KEY, (Date.now() + 7 * 86400000).toString());
      hideInstallBanner();
    });
  }

  function hideInstallBanner() {
    const el = document.getElementById("pwaInstallBanner");
    if (!el) return;
    el.classList.remove("show");
    setTimeout(() => el.remove(), 400);
  }
}

/* ============================================================
 * 滾動時隱藏 Header + 回到頂部按鈕
 * ============================================================ */
function setupHideableHeader() {
  let lastY = window.scrollY;
  let ticking = false;

  // 注入回到頂部按鈕
  if (!document.querySelector(".back-to-top")) {
    const btn = document.createElement("button");
    btn.className = "back-to-top";
    btn.innerHTML = "↑";
    btn.setAttribute("aria-label", "回到頂部");
    btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    document.body.appendChild(btn);
  }

  function onScroll() {
    const y = window.scrollY;
    const isMobile = window.innerWidth <= 768;

    // 回到頂部按鈕：捲超過 400px 才顯示
    const backBtn = document.querySelector(".back-to-top");
    if (backBtn) backBtn.classList.toggle("visible", y > 400 && isMobile);

    if (!isMobile) {
      document.body.classList.remove("header-hidden");
      ticking = false;
      return;
    }

    // 往下捲超過 80px 才收合
    if (y > lastY + 5 && y > 80) {
      document.body.classList.add("header-hidden");
    } else if (y < lastY - 5) {
      document.body.classList.remove("header-hidden");
    }
    if (y < 30) document.body.classList.remove("header-hidden");

    lastY = y;
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(onScroll);
      ticking = true;
    }
  }, { passive: true });
}

/* ============================================================
 * Toast 通知
 * ============================================================ */
function showToast(msg, type = "info") {
  let host = document.getElementById("berich-toast-host");
  if (!host) {
    host = document.createElement("div");
    host.id = "berich-toast-host";
    host.style.cssText = "position:fixed;top:80px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;gap:6px;pointer-events:none;";
    document.body.appendChild(host);
  }
  const t = document.createElement("div");
  const bg = type === "success" ? "#1a8e3e" : (type === "error" ? "#1B4332" : "#163A2E");
  t.style.cssText = `background:${bg};color:#fff;padding:10px 18px;border-radius:24px;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,0.15);opacity:0;transform:translateY(-10px);transition:all 0.25s;pointer-events:auto;`;
  t.textContent = msg;
  host.appendChild(t);
  requestAnimationFrame(() => { t.style.opacity = "1"; t.style.transform = "translateY(0)"; });
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transform = "translateY(-10px)";
    setTimeout(() => t.remove(), 250);
  }, 1800);
}

/* ============================================================
 * 行動裝置：漢堡選單注入
 * ============================================================ */
function setupMobileNav() {
  const nav = document.querySelector(".main-nav");
  if (!nav) return;
  const container = nav.querySelector(".container");
  if (!container) return;

  // 插入漢堡 toolbar
  const bar = document.createElement("div");
  bar.className = "main-nav-bar";
  bar.innerHTML = `
    <span class="nav-label">≡ 功能選單</span>
    <button class="menu-toggle" aria-label="切換選單">☰</button>
  `;
  container.insertBefore(bar, container.firstChild);

  bar.querySelector(".menu-toggle").addEventListener("click", () => {
    nav.classList.toggle("open");
  });
  bar.querySelector(".nav-label").addEventListener("click", () => {
    nav.classList.toggle("open");
  });

  // 點任一連結後自動收合
  nav.querySelectorAll("li a").forEach(a => {
    a.addEventListener("click", () => nav.classList.remove("open"));
  });
}

/* ============================================================
 * AI 今日盤勢警報（進站彈窗）
 * 進站 1.5 秒後跳出，當日已關閉就不再跳，localStorage 按日記憶
 * ============================================================ */
function setupAiAlert() {
  const overlay = document.getElementById("aiAlertOverlay");
  if (!overlay) return;

  const today = new Date().toISOString().slice(0, 10);
  const dismissKey = "leadfu_ai_alert_" + today;
  if (localStorage.getItem(dismissKey)) return;

  // 更新日期文字
  const d = new Date();
  const w = ["日","一","二","三","四","五","六"];
  const dateEl = overlay.querySelector("#aiAlertDate");
  if (dateEl) {
    dateEl.textContent = `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2,"0")}-${d.getDate().toString().padStart(2,"0")} (週${w[d.getDay()]}) ・ AI 盤前更新`;
  }

  // 動態填入 3 個亮點：今日漲幅前 2 + 1 則最新政策/公告
  const itemsHost = overlay.querySelector("#aiAlertItems");
  if (itemsHost) {
    const ranked = STOCK_DATA.stocks
      .filter(s => s.price > 0 && s.change !== 0)
      .map(s => ({ ...s, pct: pctChange(s.price, s.change) }))
      .sort((a, b) => b.pct - a.pct);
    const topGainers = ranked.slice(0, 2);

    const items = topGainers.map((s, i) => {
      const tagClass = i === 0 ? "tag-strong" : "tag-tech";
      // 中性標籤：只描述「今日漲幅排名」這個客觀事實，不做推介
      const tagText = `今日漲幅第 ${i + 1} 名`;
      const reason = `今日${s.change > 0 ? "上漲" : "下跌"} ${fmtPct(s.pct)}，成交量 ${s.volume.toLocaleString()} 張，屬 ${s.category} 類股。以上為公開數據整理，非投資建議。`;
      return `<a class="ai-alert-item" href="${pageHref('stock-detail.html?code=' + s.code)}">
        <div class="ai-alert-rank">0${i+1}</div>
        <div class="ai-alert-content">
          <div class="ai-alert-row">
            <strong>${s.code} ${s.name}</strong>
            <span class="ai-alert-tag ${tagClass}">${tagText}</span>
          </div>
          <p>${reason}</p>
        </div>
      </a>`;
    }).join("");

    // 第 3 項：最新「公告」或「政策」類新聞，沒有就放預設政策警示
    let policyItem = "";
    const policyNews = (STOCK_DATA.news || []).find(n => n.tag === "公告" || n.tag === "焦點");
    if (policyNews) {
      const newsHref = pageHref("news-detail.html?id=" + (policyNews.id || ""));
      policyItem = `<a class="ai-alert-item" href="${newsHref}">
        <div class="ai-alert-rank">03</div>
        <div class="ai-alert-content">
          <div class="ai-alert-row">
            <strong>${policyNews.tag === "公告" ? "政策警示" : "市場焦點"}</strong>
            <span class="ai-alert-tag tag-policy">影響全市場</span>
          </div>
          <p>${policyNews.title}</p>
        </div>
      </a>`;
    } else {
      policyItem = `<a class="ai-alert-item" href="${pageHref('news.html')}">
        <div class="ai-alert-rank">03</div>
        <div class="ai-alert-content">
          <div class="ai-alert-row">
            <strong>每日市場觀察</strong>
            <span class="ai-alert-tag tag-policy">AI 摘要</span>
          </div>
          <p>共 ${STOCK_DATA.stocks.length} 檔興櫃個股追蹤中，AI 持續監控成交異常與動能變化</p>
        </div>
      </a>`;
    }

    itemsHost.innerHTML = items + policyItem;
  }

  function show() {
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add("visible"));
    document.body.style.overflow = "hidden";
  }
  function dismiss() {
    overlay.classList.remove("visible");
    document.body.style.overflow = "";
    setTimeout(() => {
      overlay.hidden = true;
      localStorage.setItem(dismissKey, "1");
    }, 300);
  }

  overlay.querySelector("#aiAlertClose").addEventListener("click", dismiss);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) dismiss(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("visible")) dismiss();
  });
  // LINE 按鈕由全域代理（line-cta / data-action=line）處理跳轉
  // 這裡只負責點完關閉警報
  const lineBtn = overlay.querySelector("[data-action='line']");
  if (lineBtn) {
    lineBtn.addEventListener("click", () => setTimeout(dismiss, 300));
  }

  setTimeout(show, 1500);
}

/* ============================================================
 * 即時股價模擬（隨機漂移，讓網站看起來活的）
 * ============================================================ */
function startLivePriceSimulation(intervalMs = 3000) {
  setInterval(() => {
    // 每次隨機挑 3-5 檔個股調整
    const picks = [];
    const n = 3 + Math.floor(Math.random() * 3);
    while (picks.length < n) {
      const i = Math.floor(Math.random() * STOCK_DATA.stocks.length);
      if (!picks.includes(i)) picks.push(i);
    }

    picks.forEach(i => {
      const s = STOCK_DATA.stocks[i];
      const delta = (Math.random() - 0.5) * s.price * 0.005; // ±0.25% 微幅變動
      const newPrice = Math.max(0.1, +(s.price + delta).toFixed(2));
      const prevClose = s.price - s.change;
      s.price = newPrice;
      s.change = +(newPrice - prevClose).toFixed(2);
      s.volume += Math.floor(Math.random() * 10);

      // 同步更新 DOM 中該股的所有出現位置
      document.querySelectorAll(`tr[data-code="${s.code}"]`).forEach(tr => {
        const tds = tr.querySelectorAll("td");
        if (tds.length < 6) return;
        const cls = changeClass(s.change);
        const pct = pctChange(s.price, s.change);
        tds[2].textContent = fmtPrice(s.price);
        tds[2].className = "num " + cls;
        tds[3].innerHTML = `${arrow(s.change)} ${fmtChange(s.change)}`;
        tds[3].className = "num " + cls;
        tds[4].textContent = fmtPct(pct);
        tds[4].className = "num " + cls;
        tds[5].textContent = s.volume.toLocaleString("zh-TW");
        // 閃一下高亮
        tr.style.transition = "background 0.6s";
        tr.style.background = s.change >= 0 ? "#ffe7ec" : "#e7f5ec";
        setTimeout(() => { tr.style.background = ""; }, 600);
      });

      // 效能優化：用 data-code 屬性直接定位（不再掃描全部 tk-item）
      // 跑馬燈節點是雙份（前 30 名 × 2），用 querySelectorAll 一次取到
      document.querySelectorAll(`#tickerTrack .tk-item[data-code="${s.code}"]`).forEach(item => {
        const priceEl = item.querySelector(".tk-price");
        if (priceEl) priceEl.textContent = fmtPrice(s.price);
        const chgSpan = item.querySelectorAll("a > span")[2];
        if (chgSpan) {
          chgSpan.textContent = `${arrow(s.change)} ${fmtChange(s.change)}`;
          chgSpan.className = changeClass(s.change);
        }
      });
    });

    // 更新時間
    const now = new Date();
    const ts = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
    document.querySelectorAll("#updatedAt").forEach(el => {
      el.innerHTML = `${STOCK_DATA.updatedAt.slice(0,10)} <span style="color:#1B4332;">${ts}</span> <span style="background:#06c755;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;margin-left:4px;">LIVE</span>`;
    });
  }, intervalMs);
}

/* ============================================================
 * 全域暴露
 * ============================================================ */
// 讓 inline script 等到 loadLiveData() 跑完才 render，避免 race
let _resolveReady;
const _readyPromise = new Promise(r => { _resolveReady = r; });

window.LeadFu = {
  data: STOCK_DATA,
  fmtPrice, fmtChange, fmtPct, pctChange, changeClass, arrow,
  findStock, pageHref, homeHref,
  getWatchlist, addToWatchlist, removeFromWatchlist, isInWatchlist,
  mockAiResponse, startLivePriceSimulation, showToast,
  lineUrl: LINE_URL, lineId: LINE_ID,
  ready: _readyPromise
};

/* 全站「加 LINE」按鈕點擊代理：
   只要元素有 .line-cta / .btn-line class，或 data-action="line"，都會跳到 LINE 加好友頁 */
document.addEventListener("click", (e) => {
  const t = e.target.closest(".line-cta, .btn-line, [data-action='line']");
  if (!t) return;
  e.preventDefault();
  e.stopPropagation();
  showToast("正在開啟 LINE 加好友頁...", "success");
  setTimeout(() => window.open(LINE_URL, "_blank", "noopener"), 200);
});

/* ============================================================
 * Init
 * ============================================================ */
/* ============================================================
 * 讀取所有即時資料（fetch，失敗就用內嵌備份）
 * 由 scripts/run_all.py 每日產生 4 個 JSON：
 *   stocks_live.json / news_live.json / announcements_live.json / klines.json
 * ============================================================ */
function dataUrl(file) {
  const inPages = location.pathname.includes("/pages/");
  return (inPages ? "../" : "") + "data/" + file;
}

async function fetchJson(file) {
  const resp = await fetch(dataUrl(file), { cache: "no-cache" });
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return resp.json();
}

async function loadLiveData() {
  // 1. 興櫃個股報價
  try {
    const live = await fetchJson("stocks_live.json");
    if (live.stocks && live.stocks.length) {
      STOCK_DATA.stocks = live.stocks;
      STOCK_DATA.updatedAt = (live.updatedAt || "") + " · " + (live.source || "TPEx");
      STOCK_DATA.source = live.source;
      console.log(`[領富 AI] ✅ ${live.stocks.length} 檔 TPEx 即時報價 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 個股報價用備份 (${e.message})`);
  }

  // 2. 財經新聞（Google News RSS）
  try {
    const live = await fetchJson("news_live.json");
    if (live.news && live.news.length) {
      STOCK_DATA.news = live.news;
      console.log(`[領富 AI] ✅ ${live.news.length} 則即時新聞`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 新聞用備份 (${e.message})`);
  }

  // 3. 公告（TPEx 重大訊息）
  try {
    const live = await fetchJson("announcements_live.json");
    if (live.announcements && live.announcements.length) {
      STOCK_DATA.announcements = live.announcements;
      console.log(`[領富 AI] ✅ ${live.announcements.length} 筆即時公告`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 公告用備份 (${e.message})`);
  }

  // 4. K 線歷史（不存進 STOCK_DATA，個股詳情頁另外讀）
  try {
    const live = await fetchJson("klines.json");
    if (live.klines) {
      STOCK_DATA.klines = live.klines;
      const days = Object.values(live.klines)[0]?.length || 0;
      console.log(`[領富 AI] ✅ ${live.stockCount || 0} 檔 K 線（累積 ${days} 天）`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ K 線用 mock (${e.message})`);
  }

  // 5. 公司基本資料（887 筆，董事長/地址/網站/成立日/實收資本...）
  try {
    const live = await fetchJson("companies_live.json");
    if (live.companies) {
      STOCK_DATA.companies = live.companies;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆公司基本資料`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 公司基本資料未載入 (${e.message})`);
  }

  // 6. 月營收（含月增/年增/累計）
  try {
    const live = await fetchJson("revenue_live.json");
    if (live.revenue) {
      STOCK_DATA.revenue = live.revenue;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆月營收`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 月營收未載入 (${e.message})`);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  setupSEO();
  loadGA();
  setupMobileNav();
  setupBottomTabBar();
  setupHideableHeader();
  setupDisclaimer();
  setupPWA();
  renderDate();

  // 先抓即時資料再渲染表格
  await loadLiveData();
  _resolveReady();   // 通知所有 inline script 資料就緒，可以開始 render

  renderTicker();
  renderStockTable();
  renderNews();
  renderTopics();
  bindTabs();
  bindAddFavBtns();
  bindMobileRowTap();
  bindSearch();
  setupVoiceSearch();   // 🎤 語音搜尋（每頁 search-box 自動注入麥克風按鈕）
  bindAiPlaceholders();
  setupAiAlert();
  // 開啟即時股價模擬（每 6 秒微幅跳動，避免長時間高 CPU 佔用）
  startLivePriceSimulation(6000);
});
