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
    { code: "3552", name: "同致",   price: 178.0, change: -2.0, volume: 320,   category: "電子零組件",   status: "興櫃" },
    { code: "6515", name: "穎崴",   price: 1245,  change: 35.0, volume: 88,    category: "半導體",       status: "興櫃" },
    { code: "8038", name: "長園科", price: 92.3,  change: 1.2,  volume: 540,   category: "電池材料",     status: "興櫃" },
    { code: "6531", name: "愛普",   price: 1820,  change: -45,  volume: 45,    category: "IC設計",       status: "興櫃" },
    { code: "6770", name: "力積電", price: 28.5,  change: 0.5,  volume: 2850,  category: "晶圓代工",     status: "興櫃" },
    { code: "6841", name: "長聖",   price: 215,   change: 5,    volume: 180,   category: "生技醫療",     status: "興櫃" },
    { code: "4174", name: "浩鼎",   price: 320,   change: -8,   volume: 95,    category: "生技醫療",     status: "興櫃" },
    { code: "6962", name: "拓凱",   price: 156,   change: 2.5,  volume: 420,   category: "運動器材",     status: "興櫃" },
    { code: "8155", name: "博智",   price: 386,   change: 11,   volume: 230,   category: "PCB",          status: "興櫃" },
    { code: "5483", name: "中美晶", price: 132.5, change: -1.5, volume: 680,   category: "半導體",       status: "興櫃" },
    { code: "2069", name: "運錩",   price: 56.4,  change: 0.8,  volume: 1100,  category: "鋼鐵",         status: "興櫃" },
    { code: "6116", name: "彩晶",   price: 8.95,  change: -0.05,volume: 12500, category: "面板",         status: "興櫃" },
    { code: "3265", name: "台星科", price: 88,    change: 1.5,  volume: 380,   category: "半導體封測",   status: "興櫃" },
    { code: "4438", name: "廣越",   price: 245,   change: 4.5,  volume: 145,   category: "紡織成衣",     status: "興櫃" },
    { code: "3293", name: "鈊象",   price: 985,   change: 22,   volume: 320,   category: "遊戲軟體",     status: "興櫃" },
    { code: "8261", name: "富鼎",   price: 215,   change: -3.5, volume: 280,   category: "電源管理IC",   status: "興櫃" },
    { code: "6679", name: "鈺太",   price: 458,   change: 12,   volume: 165,   category: "IC設計",       status: "興櫃" },
    { code: "6196", name: "帆宣",   price: 178,   change: 4.5,  volume: 920,   category: "電子設備",     status: "興櫃" },
    { code: "8482", name: "商億-KY",price: 132,   change: -2.5, volume: 220,   category: "家具",         status: "興櫃" },
    { code: "6859", name: "頎邦",   price: 78.5,  change: 1.2,  volume: 1850,  category: "半導體封測",   status: "興櫃" },
    { code: "3416", name: "融程電", price: 156,   change: 3.5,  volume: 380,   category: "工業電腦",     status: "興櫃" },
    { code: "1597", name: "直得",   price: 92.5,  change: -1.5, volume: 450,   category: "機械",         status: "興櫃" },
    { code: "4763", name: "材料-KY",price: 285,   change: 8.5,  volume: 210,   category: "化學材料",     status: "興櫃" },
    { code: "6890", name: "宏觀",   price: 165,   change: 2,    volume: 320,   category: "PCB",          status: "興櫃" },
    { code: "6664", name: "群翊",   price: 178,   change: 6,    volume: 280,   category: "電子設備",     status: "興櫃" },
    { code: "8358", name: "金居",   price: 92,    change: -0.5, volume: 1450,  category: "PCB銅箔",      status: "興櫃" },
    { code: "3373", name: "熱映",   price: 56,    change: 1.5,  volume: 680,   category: "光學元件",     status: "興櫃" },
    { code: "3217", name: "優群",   price: 145,   change: 5.5,  volume: 380,   category: "連接器",       status: "興櫃" },
    { code: "6669", name: "緯穎",   price: 2850, change: 65,   volume: 28,    category: "伺服器",       status: "興櫃" }
  ],
  news: [
    {
      id: 1, time: "09:25", date: "2026-05-12", tag: "熱門", related: ["6488","6515"],
      title: "外資加碼半導體興櫃股，環球晶連三紅",
      author: "領富 AI編輯部 / 記者 王志明",
      body: [
        "【台北報導】興櫃股票市場今日延續強勢表現，半導體類股成為焦點。其中環球晶 (6488) 開盤即跳空上漲，盤中最高一度觸及 470 元，最終收在 462.5 元，連續三個交易日收紅。",
        "根據領富 AI統計，外資法人近五個交易日累積買超環球晶超過 1,200 張，買超金額達 5.5 億元，顯示國際資金看好台灣半導體供應鏈的中長期發展。",
        "業內人士分析，環球晶受惠於 AI 伺服器與先進製程晶圓需求大幅成長，12 吋矽晶圓出貨量逐月攀升。法人預估，公司 2026 全年營收可望年增 25% 以上。",
        "另一檔半導體類股穎崴 (6515) 同步走揚，今日上漲 35 元至 1,245 元，創 4 個月新高。穎崴所生產的 Probe Card 為 IC 測試關鍵設備，受惠於 AI 晶片測試需求暴增。",
        "展望後市，分析師建議投資人留意半導體類股的回檔買點，但提醒興櫃股票流動性較低，建議分批布局並控管部位。"
      ]
    },
    {
      id: 2, time: "09:10", date: "2026-05-12", tag: "焦點", related: ["6531","6488"],
      title: "AI 概念股延燒至興櫃市場，IC 設計股表現亮眼",
      author: "領富 AI編輯部 / 記者 林佳穎",
      body: [
        "【台北報導】AI 浪潮持續發酵，已從上市櫃市場延燒至興櫃與興櫃股票。IC 設計類股今日普遍走高，其中愛普 (6531) 雖小幅回檔，但近一個月仍上漲超過 20%。",
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
      title: "興櫃股市週評：成交量回升 15%，買盤轉趨積極",
      author: "領富 AI研究部",
      body: [
        "【週評】上週興櫃股票市場成交量較前週回升 15%，買盤轉趨積極，顯示市場信心逐步恢復。",
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
      title: "週評：興櫃加權指數收 312.5 點，週漲 1.8%",
      author: "領富 AI研究部",
      body: [
        "【週評】領富 AI自編興櫃加權指數本週收在 312.5 點，週漲幅 1.8%。其中半導體類股貢獻最大，佔指數漲幅 60% 以上。",
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
const HOME_TABLE_TOP_N = 30;   // 首頁熱門股表格：每分類顯示前 N 名（按成交量）

function renderStockTable() {
  const tbody = document.getElementById("stockTbody");
  if (!tbody) return;
  let pool = currentFilter === "all"
    ? STOCK_DATA.stocks
    : STOCK_DATA.stocks.filter(s => s.status === currentFilter);
  // 按成交量取前 N 名（避免 dump 2300 筆）
  const list = pool.filter(s => s.price > 0)
                   .slice()
                   .sort((a, b) => (b.volume || 0) - (a.volume || 0))
                   .slice(0, HOME_TABLE_TOP_N);

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
  // 整個 .stock-table 的 tr[data-code] 都可點，桌機/手機都通
  document.addEventListener("click", (e) => {
    const tr = e.target.closest(".stock-table tr[data-code]");
    if (!tr) return;
    // 不要攔截真實連結與按鈕（避免「+自選」按鈕被誤觸發跳轉）
    if (e.target.closest("a, button")) return;
    const code = tr.dataset.code;
    if (code) location.href = pageHref("stock-detail.html?code=" + code);
  });
  // 滑鼠 hover 顯示手型 cursor（視覺提示「這列可點」）
  if (!document.getElementById("_rowTapStyle")) {
    const s = document.createElement("style");
    s.id = "_rowTapStyle";
    s.textContent = `.stock-table tr[data-code]{cursor:pointer;}.stock-table tr[data-code]:hover{background:#fafbfc;}`;
    document.head.appendChild(s);
  }
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
 * 首頁 Hero 三張卡片（動態載入熱門股，不再硬編碼）
 * ============================================================ */
function renderHeroCards() {
  const host = document.getElementById("heroCards");
  if (!host) return;
  // 取上市熱門股 top 3（成交量），缺資料時自動退而求其次
  const all = STOCK_DATA.stocks || [];
  const listed = all.filter(s => s.market === "listed" && s.price > 0)
                    .sort((a, b) => (b.volume || 0) - (a.volume || 0));
  const pool = listed.length >= 3 ? listed : all.filter(s => s.price > 0)
                                                .sort((a, b) => (b.volume || 0) - (a.volume || 0));
  const top3 = pool.slice(0, 3);
  if (top3.length === 0) return;

  const cards = top3.map(s => {
    const pct = pctChange(s.price, s.change);
    const cls = changeClass(s.change);
    const marketLabel = s.status || (s.market === "listed" ? "上市"
                                   : s.market === "otc"    ? "上櫃"
                                   : s.market === "emerging" ? "興櫃" : "");
    return `<a class="hero-card" href="${pageHref('stock-detail.html?code=' + s.code)}" style="text-decoration:none;color:inherit;">
      <div class="hc-row"><span class="hc-name">${s.code} ${s.name}</span><span class="hc-price">${fmtPrice(s.price)}</span></div>
      <div class="hc-row"><span class="hc-pct ${cls}">${arrow(s.change)} ${fmtPct(pct)}</span><span style="font-size:11px;opacity:0.7;">${marketLabel}</span></div>
      <div class="hc-ai">AI 摘要：成交量 ${s.volume.toLocaleString()} 張・${s.category}</div>
    </a>`;
  }).join("");
  host.innerHTML = cards;
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

/* ============================================================
 * 自然語言意圖解析（第 1 層 AI 問答：無 LLM、純規則匹配）
 * 之後第 2 層接 Claude API 可在這函式 fallback 時呼叫
 * 回傳：{ kind, ...payload }  kind ∈ nav|stock|list|search|null
 * ============================================================ */
function parseAiQuery(text) {
  if (!text) return null;
  const q = String(text).trim();
  if (!q) return null;

  // ---- 1. 導覽意圖（跳頁）----
  if (/詐|騙|被坑|被害|警示/.test(q))
    return { kind: "nav", url: pageHref("fraud-alert.html"), label: "投資人防詐須知" };
  if (/註冊|加入會員|新會員/.test(q))
    return { kind: "nav", url: pageHref("register.html"), label: "會員註冊" };
  if (/登入|login/i.test(q))
    return { kind: "nav", url: pageHref("login.html"), label: "會員登入" };
  if (/(自選|追蹤|關注).*(股|清單)|我的(自選|追蹤|關注)/.test(q))
    return { kind: "nav", url: pageHref("watchlist.html"), label: "我的自選股" };
  if (/稅|報稅|證所稅/.test(q))
    return { kind: "nav", url: pageHref("tax.html"), label: "稅務說明" };
  if (/教學|怎麼下單|怎麼買|新手|入門|看不懂|教我/.test(q))
    return { kind: "nav", url: pageHref("tutorial.html"), label: "新手教學" };
  if (/IPO|新股|抽籤/i.test(q))
    return { kind: "nav", url: pageHref("ipo.html"), label: "新股抽籤" };
  if (/公告|重大訊息/.test(q))
    return { kind: "nav", url: pageHref("announcements.html"), label: "公告中心" };
  if (/新聞|快訊/.test(q) && !/公司新聞/.test(q))
    return { kind: "nav", url: pageHref("news.html"), label: "財經新聞" };

  // ---- 2. 個股直接命中（4 碼代號 或 完整公司名包含）----
  const codeMatch = q.match(/\b\d{4}\b/);
  if (codeMatch) {
    const code = codeMatch[0];
    const stock = (STOCK_DATA.stocks || []).find(s => s.code === code);
    if (stock) return { kind: "stock", code: stock.code, name: stock.name };
  }
  // 公司名子串匹配（從長到短，避免短名先match）
  const allStocks = (STOCK_DATA.stocks || []).filter(s => s.name && s.name.length >= 2);
  const sortedByLen = [...allStocks].sort((a, b) => b.name.length - a.name.length);
  const nameHit = sortedByLen.find(s => q.includes(s.name));
  if (nameHit) return { kind: "stock", code: nameHit.code, name: nameHit.name };

  // ---- 3. 列表查詢（市場 / 產業 / 排序 三維度組合）----
  // 解析市場
  let market = null;
  if (/上市/.test(q))      market = "listed";
  else if (/上櫃/.test(q)) market = "otc";
  else if (/興櫃/.test(q)) market = "emerging";

  // 解析產業（取最先出現的關鍵字）
  const industries = ["半導體","電子零組件","電腦周邊","通訊網路","電子通路","資訊服務",
                      "電子","生技","金融","金融控股","證券","保險","電機機械","鋼鐵",
                      "光電","航運","食品","紡織","塑膠","化學","橡膠","建材營造","建材",
                      "汽車","觀光","百貨","水泥","造紙","玻璃","電器電纜","PCB","醫療",
                      "AI"];
  const matchedIndustry = industries.find(i => q.includes(i));

  // 解析排序
  let sortBy = null;
  if (/漲(最多|幅|前|榜)|漲幅|多頭|表現好/.test(q))           sortBy = "gainers";
  else if (/跌(最多|幅|前|榜)|跌幅|空頭|表現差/.test(q))      sortBy = "losers";
  else if (/成交(量|活躍|熱門)|熱門|熱股|量(最多|大)|爆量/.test(q)) sortBy = "volume";
  else if (/股價(最高|前)|最貴|高價股/.test(q))               sortBy = "price_desc";
  else if (/(便宜|低價|銅板)股/.test(q))                       sortBy = "price_asc";

  if (sortBy || matchedIndustry || market) {
    return {
      kind: "list",
      market,
      industry: matchedIndustry || null,
      sortBy: sortBy || "volume",
      limit: 15
    };
  }

  // ---- 4. fallback：一般 fuzzy 搜尋 ----
  return { kind: "search", q };
}

/* 把意圖物件變成可分享的 URL（給 ai.html 結果頁用） */
function aiQueryUrl(query) {
  return pageHref("ai.html?q=" + encodeURIComponent(query));
}

/* 判斷查詢「看起來」是不是自然語言（vs 純股票代號 / 公司名）*/
function isNaturalLanguageQuery(text) {
  if (!text) return false;
  const q = String(text).trim();
  // 純 4 碼數字 = 代號，不是 NL
  if (/^\d{4}$/.test(q)) return false;
  // 太短 = 不像 NL
  if (q.length < 3) return false;
  // 包含問句字眼 / 動作字眼 / 多市場詞彙
  return /找|哪|怎麼|誰|多少|幾|前 |最多|最少|最大|最小|漲|跌|熱門|活躍|教|新手|詐|騙|我的|上市|上櫃|興櫃|類股|股票/.test(q);
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

    // ★ 自然語言查詢 → 走 AI 問答頁
    if (isNaturalLanguageQuery(q)) {
      location.href = aiQueryUrl(q);
      return;
    }

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

    // 依市場給對應的「同市場分布」描述與風險提醒（不再寫死「興櫃」）
    const marketLabel = s.market === "listed"   ? "上市"
                      : s.market === "otc"      ? "上櫃"
                      : s.market === "emerging" ? "興櫃"
                      : (s.status || "");
    const peerLabel = marketLabel ? `${marketLabel}個股` : "同類個股";
    // 各市場成交量量級不同：上市基準較高，上櫃次之，興櫃最低
    const volThreshold = s.market === "listed" ? 5000
                       : s.market === "otc"    ? 1000
                       : 500;
    const volBucket = s.volume > volThreshold ? "成交較活躍" : "成交一般";

    const riskByMarket = {
      "listed":   "上市股票於集中市場交易，每日漲跌幅限制 ±10%。短線波動可能較大",
      "otc":      "上櫃股票於櫃買中心交易，每日漲跌幅限制 ±10%。部分中小型股流動性較低",
      "emerging": "興櫃股票每日漲跌幅 ±10%，流動性與資訊揭露弱於上市櫃，買賣價差較大",
      "":         "興櫃股票無集中市場、流動性低、價格不透明、買賣風險高"
    };
    const riskText = (s.market === "興櫃" || s.status === "興櫃")
      ? riskByMarket[""]
      : (riskByMarket[s.market] || riskByMarket["emerging"]);

    return `
      <div class="ai-result">
        <div class="ai-result-head">📋 AI 個股資料摘要（範例）</div>
        <p><strong>${s.code} ${s.name}</strong>（${s.category}・${marketLabel || s.status}）目前報價 ${fmtPrice(s.price)}，今日${dir} ${fmtPct(pct)}。</p>
        <p><strong>成交概況：</strong>今日成交量 ${s.volume.toLocaleString()} 張，於${peerLabel}中屬${volBucket}。</p>
        <p><strong>產業別：</strong>歸類於 ${s.category}。本摘要僅彙整公開數據，未對個股做任何評價或判斷。</p>
        <p><strong>風險提醒：</strong>${riskText}，買賣應透過合法券商辦理。</p>
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
 * 🎨 主題切換（墨綠老錢 ↔ 喜氣紅金）
 * 台股族群迷信紅色 = 漲、賺錢，給他們選擇權
 * ============================================================ */
function setupThemeToggle() {
  const STORAGE_KEY = "leadfu_theme";
  // 先套用儲存的主題（避免閃爍）
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "red") document.body.classList.add("theme-red");

  // 在每個 .top-right 注入切換按鈕
  document.querySelectorAll(".top-right").forEach(host => {
    if (host.querySelector(".theme-toggle-btn")) return;
    const btn = document.createElement("button");
    btn.className = "theme-toggle-btn";
    btn.type = "button";
    btn.title = "切換主題顏色（墨綠 ↔ 喜氣紅）";
    btn.innerHTML = getThemeBtnLabel();
    btn.addEventListener("click", toggleTheme);
    // 放在最前面（會員登入按鈕左邊）
    host.insertBefore(btn, host.firstChild);
  });

  function getThemeBtnLabel() {
    return document.body.classList.contains("theme-red")
      ? `<span class="theme-dot theme-dot-green"></span>切換墨綠`
      : `<span class="theme-dot theme-dot-red"></span>切換喜氣紅`;
  }

  function toggleTheme() {
    document.body.classList.toggle("theme-red");
    const isRed = document.body.classList.contains("theme-red");
    localStorage.setItem(STORAGE_KEY, isRed ? "red" : "green");
    document.querySelectorAll(".theme-toggle-btn").forEach(b => b.innerHTML = getThemeBtnLabel());
    if (window.showToast) {
      window.showToast(isRed ? "🔴 已切換到喜氣紅金主題" : "💚 已切回墨綠老錢主題", "success");
    }
  }
}

/* ============================================================
 * 🔊 TTS 文字朗讀（Web Speech API，免費、繁中支援）
 * 給 45-75 老花眼用戶：點 AI 訊息上的 🔊 就能聽
 * ============================================================ */
const LeadFuTTS = {
  _voices: [],
  _currentBtn: null,    // 目前播放中的按鈕（用於 UI 狀態）

  init() {
    if (!window.speechSynthesis) return;
    const load = () => { this._voices = window.speechSynthesis.getVoices(); };
    load();
    // Chrome 上 voices 是非同步載入
    window.speechSynthesis.onvoiceschanged = load;
  },

  isSupported() { return !!window.speechSynthesis; },

  /** 清理文字：去掉 markdown 標記與免責句，讓朗讀順 */
  _cleanText(text) {
    if (!text) return "";
    return String(text)
      .replace(/\*\*([^*]+)\*\*/g, "$1")    // **bold**
      .replace(/\*([^*]+)\*/g, "$1")         // *italic*
      .replace(/`([^`]+)`/g, "$1")           // `code`
      .replace(/^[#\->\s]+/gm, "")           // 開頭 # > -
      .replace(/^[①②③④⑤⑥⑦⑧⑨⑩]\s*/gm, "")
      .replace(/[─━]+/g, "")                 // 分隔線
      .replace(/^\s*[\*\-\+]\s+/gm, "")      // 條列 bullet
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  },

  /** 選最佳繁中語音 */
  _pickVoice() {
    const v = this._voices;
    return v.find(x => x.lang === "zh-TW")
        || v.find(x => x.lang === "zh-Hant" || x.lang === "zh-Hant-TW")
        || v.find(x => x.lang === "zh-HK")
        || v.find(x => x.lang === "zh-CN")
        || v.find(x => x.lang && x.lang.startsWith("zh"))
        || null;
  },

  /** 朗讀，回傳 utterance；若已在朗讀則先停止 */
  speak(text, opts) {
    if (!this.isSupported()) return null;
    const clean = this._cleanText(text);
    if (!clean) return null;
    this.cancel();   // 停止之前的

    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "zh-TW";
    u.rate = (opts && opts.rate) || 1.0;
    u.pitch = 1.0;
    u.volume = 1.0;
    const voice = this._pickVoice();
    if (voice) u.voice = voice;

    if (opts && opts.onStart) u.onstart = opts.onStart;
    if (opts && opts.onEnd) {
      const end = opts.onEnd;
      u.onend = end;
      u.onerror = end;
    }
    window.speechSynthesis.speak(u);
    return u;
  },

  cancel() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  },

  /** Toggle 朗讀按鈕（點一次播、再點停）*/
  toggleButton(btn, text) {
    if (!this.isSupported()) return;
    const playing = btn.classList.contains("playing");

    // 先把所有播放中的按鈕還原
    document.querySelectorAll(".chat-tts-btn.playing").forEach(b => {
      b.classList.remove("playing");
      b.textContent = "🔊";
    });
    this.cancel();

    if (playing) return;  // 點同一個 → 停止

    btn.classList.add("playing");
    btn.textContent = "⏸";
    this.speak(text, {
      onEnd: () => {
        btn.classList.remove("playing");
        btn.textContent = "🔊";
      }
    });
  }
};
LeadFuTTS.init();
window.LeadFuTTS = LeadFuTTS;

/* 頁面離開時自動停止朗讀 */
window.addEventListener("beforeunload", () => LeadFuTTS.cancel());
window.addEventListener("pagehide", () => LeadFuTTS.cancel());

/* ============================================================
 * 💬 會員回饋小工具（漂浮按鈕 + Modal）
 * 任何頁面都能 1 秒丟意見，存進 Supabase feedback 表
 * ============================================================ */
function setupFeedbackWidget() {
  // 漂浮按鈕（右下角，手機在 bottom-tab-bar 上方）
  const btn = document.createElement("button");
  btn.className = "feedback-fab";
  btn.type = "button";
  btn.setAttribute("aria-label", "意見回饋");
  btn.title = "意見回饋";
  btn.innerHTML = `<span class="feedback-fab-emoji" aria-hidden="true">💬</span><span class="feedback-fab-label">回饋</span>`;
  document.body.appendChild(btn);
  btn.addEventListener("click", showFeedbackModal);
}

/* ============================================================
 * 📢 防詐騙官方資訊 banner（首頁頂端，可關閉 7 天）
 * ============================================================ */
function setupAntiFraudBanner() {
  const banner = document.getElementById("antiFraudBanner");
  if (!banner) return;

  // 7 天內關過 → 直接隱藏
  const KEY = "leadfu_afb_closed_at";
  const closedAt = parseInt(localStorage.getItem(KEY) || "0", 10);
  const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;
  if (closedAt && Date.now() - closedAt < SEVEN_DAYS) {
    banner.style.display = "none";
    return;
  }

  banner.addEventListener("click", (e) => {
    if (e.target.closest('[data-action="close"]')) {
      localStorage.setItem(KEY, String(Date.now()));
      banner.style.display = "none";
    }
  });
}

/* ============================================================
 * 全站 footer 防詐 reminder（自動注入到每個 site-footer 下方）
 * 給搜尋引擎 / AI 爬蟲穩定錨點：本站絕不...
 * ============================================================ */
function injectFooterFraudReminder() {
  const footer = document.querySelector(".site-footer");
  if (!footer) return;
  if (footer.querySelector(".footer-fraud-reminder")) return;
  const reminder = document.createElement("div");
  reminder.className = "footer-fraud-reminder";
  reminder.innerHTML = `
    <div class="container">
      <strong>📢 領富 AI 官方聲明：</strong>本站<strong>不提供個股推薦</strong>、<strong>不收任何投資款項</strong>、<strong>不主動加 LINE 群組</strong>、<strong>未發行 APP</strong>。
      唯一官方網址 <code style="background:rgba(197,165,114,0.15);padding:1px 5px;border-radius:3px;color:#C5A572;">leadfuai.com</code>
      ／唯一客服 LINE <a href="https://line.me/R/ti/p/@041exgtv" target="_blank" rel="noopener">@041exgtv</a>。
      看到任何冒用本品牌之投資邀約，請撥 <a href="https://165.npa.gov.tw/" target="_blank" rel="noopener">165</a> 反詐騙專線。
      <a href="${pageHref('fraud-alert.html')}">了解更多防詐須知 →</a>
    </div>
  `;
  footer.appendChild(reminder);
}

/* ============================================================
 * 👋 首次訪客 onboarding 浮層
 * 只有「首頁」且「localStorage 沒看過旗標」才會跳
 * 3 個步驟介紹核心差異化價值
 * ============================================================ */
function setupOnboarding() {
  // 只在首頁跳
  const isHome = location.pathname === "/" || location.pathname.endsWith("/index.html");
  if (!isHome) return;

  // 看過就不再跳
  const STORAGE_KEY = "leadfu_onboarded_v1";
  if (localStorage.getItem(STORAGE_KEY)) return;

  // 延遲 1.2 秒讓首頁先渲染（避免一進來就被擋）
  setTimeout(() => showOnboarding(), 1200);
}

function showOnboarding() {
  if (document.querySelector(".onboard-overlay")) return;

  const STORAGE_KEY = "leadfu_onboarded_v1";
  const steps = [
    {
      eyebrow: "歡迎來到",
      icon: "👋",
      title: "領富 AI · 您的 AI 投資助理",
      desc: "跨上市、上櫃、興櫃 2,310 檔台股，AI 幫您整理公開資料 — 看清楚再決定。",
      features: [
        "全市場資料：三大法人、籌碼、月營收、技術指標",
        "AI 自然語言對話、每日盤後摘要、產業週報",
        "免費註冊，不綁信用卡"
      ],
      next: "下一步 →"
    },
    {
      eyebrow: "不報明牌，先看清楚",
      icon: "⚠",
      title: "防錯雷達 + AI 對話",
      desc: "資料整理在前、決策權在您手上。我們不發強烈推薦，只把公開資訊整理到您看得懂。",
      features: [
        "⚠ 防錯雷達：注意股、處置股、月營收暴跌自動掃描",
        "🤖 AI 對話：「台積電現在貴嗎？」自然語言問答",
        "📋 持股健診：AI 生成風險組合分析報告"
      ],
      next: "下一步 →"
    },
    {
      eyebrow: "每週一早上 8 點",
      icon: "📰",
      title: "AI 產業週報",
      desc: "AI 自動整理上週台股 10 大產業重點，含朗讀功能、字級調整 — 邊喝咖啡邊聽完。",
      features: [
        "10 大產業逐一觀察、外資動向、重點個股",
        "整篇朗讀（約 7 分鐘）或單段播放",
        "字級三段切換（標準／大／特大）"
      ],
      next: "開始使用 →"
    }
  ];

  let idx = 0;
  const overlay = document.createElement("div");
  overlay.className = "onboard-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");

  function render() {
    const s = steps[idx];
    overlay.innerHTML = `
      <div class="onboard-modal">
        <div class="onboard-head">
          <button type="button" class="onboard-skip" data-action="skip">略過 ✕</button>
          <div class="onboard-eyebrow">${s.eyebrow}</div>
          <div class="onboard-icon">${s.icon}</div>
          <h2 class="onboard-title">${s.title}</h2>
          <p class="onboard-desc">${s.desc}</p>
        </div>
        <div class="onboard-body">
          <ul class="onboard-features">
            ${s.features.map(f => `<li><span class="ob-check">✓</span><span>${f}</span></li>`).join("")}
          </ul>
        </div>
        <div class="onboard-foot">
          <div class="onboard-dots">
            ${steps.map((_, i) => `<span class="${i === idx ? 'active' : ''}"></span>`).join("")}
          </div>
          <div style="display:flex;gap:8px;">
            ${idx > 0 ? `<button type="button" class="onboard-btn onboard-btn-back" data-action="back">← 上一步</button>` : ""}
            <button type="button" class="onboard-btn" data-action="${idx === steps.length - 1 ? 'done' : 'next'}">${s.next}</button>
          </div>
        </div>
      </div>
    `;
  }

  function close() {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    overlay.style.animation = "ob-fade-in 0.2s reverse";
    setTimeout(() => overlay.remove(), 180);
  }

  overlay.addEventListener("click", (e) => {
    // 點背景關閉
    if (e.target === overlay) { close(); return; }
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const act = btn.dataset.action;
    if (act === "skip" || act === "done") { close(); return; }
    if (act === "next" && idx < steps.length - 1) { idx++; render(); }
    if (act === "back" && idx > 0) { idx--; render(); }
  });

  // ESC 關閉
  const escHandler = (e) => {
    if (e.key === "Escape") {
      close();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);

  render();
  document.body.appendChild(overlay);
}

let _feedbackSubmitting = false;

async function showFeedbackModal() {
  if (document.getElementById("feedback-modal-overlay")) return;

  // 取目前登入使用者（若已登入帶入 email）
  let userEmail = "", userId = null;
  if (window.LeadFuAuth && window.LeadFuAuth.getUser) {
    try {
      const u = await window.LeadFuAuth.getUser();
      if (u) { userEmail = u.email || ""; userId = u.id; }
    } catch {}
  }

  const overlay = document.createElement("div");
  overlay.id = "feedback-modal-overlay";
  overlay.className = "feedback-modal-overlay";
  overlay.innerHTML = `
    <div class="feedback-modal" role="dialog" aria-modal="true" aria-labelledby="fbTitle">
      <div class="feedback-modal-head">
        <h2 id="fbTitle">💬 您的意見回饋</h2>
        <button type="button" class="feedback-modal-close" aria-label="關閉">✕</button>
      </div>
      <form id="feedbackForm" class="feedback-modal-body">
        <div class="feedback-row">
          <label>我想反映：</label>
          <div class="feedback-cat-grid">
            <label class="feedback-cat"><input type="radio" name="cat" value="建議" checked> 💡 建議</label>
            <label class="feedback-cat"><input type="radio" name="cat" value="問題回報"> 🐛 問題回報</label>
            <label class="feedback-cat"><input type="radio" name="cat" value="讚美"> 🎉 讚美</label>
            <label class="feedback-cat"><input type="radio" name="cat" value="其他"> 💭 其他</label>
          </div>
        </div>

        <div class="feedback-row">
          <label>整體評分（選填）：</label>
          <div class="feedback-stars" id="fbStars">
            <span data-r="1">☆</span><span data-r="2">☆</span><span data-r="3">☆</span><span data-r="4">☆</span><span data-r="5">☆</span>
          </div>
        </div>

        <div class="feedback-row">
          <label for="fbMessage">您的意見 *</label>
          <textarea id="fbMessage" name="message" rows="4" maxlength="500" required
            placeholder="告訴我們您的想法、遇到的問題、或希望我們改進的地方..."></textarea>
          <div class="feedback-counter"><span id="fbCount">0</span> / 500</div>
        </div>

        ${userEmail ? "" : `
        <div class="feedback-row">
          <label for="fbEmail">Email（選填，方便我們回覆）</label>
          <input type="email" id="fbEmail" name="email" placeholder="your@email.com" maxlength="120">
        </div>`}

        <div class="feedback-actions">
          <button type="button" class="feedback-cancel">取消</button>
          <button type="submit" class="feedback-submit">送出</button>
        </div>
        <p class="feedback-disclaimer">您的回饋會直接傳送給領富 AI 團隊，我們會儘快處理 🙏</p>
      </form>

      <div class="feedback-success" id="fbSuccess" hidden>
        <div class="feedback-success-icon">✅</div>
        <h3>謝謝您的回饋！</h3>
        <p>我們已經收到您的意見，會儘快參考改進。</p>
        <button type="button" class="feedback-submit feedback-close-after">完成</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  requestAnimationFrame(() => overlay.classList.add("show"));

  // 關閉
  const closeModal = () => {
    overlay.classList.remove("show");
    setTimeout(() => overlay.remove(), 200);
  };
  overlay.querySelector(".feedback-modal-close").addEventListener("click", closeModal);
  overlay.querySelector(".feedback-cancel").addEventListener("click", closeModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });

  // 字數計數
  const msgEl = overlay.querySelector("#fbMessage");
  const countEl = overlay.querySelector("#fbCount");
  msgEl.addEventListener("input", () => { countEl.textContent = msgEl.value.length; });

  // 星等評分
  let rating = 0;
  overlay.querySelectorAll("#fbStars span").forEach(star => {
    star.addEventListener("mouseenter", () => {
      const r = parseInt(star.dataset.r);
      overlay.querySelectorAll("#fbStars span").forEach(s => {
        s.textContent = parseInt(s.dataset.r) <= r ? "★" : "☆";
        s.classList.toggle("hover", parseInt(s.dataset.r) <= r);
      });
    });
    star.addEventListener("click", () => {
      rating = parseInt(star.dataset.r);
      overlay.querySelectorAll("#fbStars span").forEach(s => {
        s.textContent = parseInt(s.dataset.r) <= rating ? "★" : "☆";
        s.classList.toggle("selected", parseInt(s.dataset.r) <= rating);
      });
    });
  });
  overlay.querySelector("#fbStars").addEventListener("mouseleave", () => {
    overlay.querySelectorAll("#fbStars span").forEach(s => {
      s.classList.remove("hover");
      s.textContent = parseInt(s.dataset.r) <= rating ? "★" : "☆";
    });
  });

  // 送出
  overlay.querySelector("#feedbackForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (_feedbackSubmitting) return;
    _feedbackSubmitting = true;
    const submitBtn = overlay.querySelector(".feedback-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "送出中...";

    const formData = new FormData(e.target);
    const payload = {
      category: formData.get("cat") || "其他",
      rating: rating || null,
      message: (formData.get("message") || "").toString().trim().slice(0, 500),
      email: userEmail || (formData.get("email") || "").toString().trim().slice(0, 120) || null,
      user_id: userId,
      page_url: location.href,
      user_agent: navigator.userAgent.slice(0, 240)
    };

    let success = false, errMsg = "";
    try {
      // 兩種送法：優先用 Supabase JS（如果頁面有載），否則直接打 REST API
      if (window.LeadFuAuth && window.LeadFuAuth.client) {
        const { error } = await window.LeadFuAuth.client.from("feedback").insert(payload);
        if (error) throw error;
      } else {
        // 直接 REST API（不依賴 supabase-js，所有頁面都能用）
        const resp = await fetch("https://lhwxpnyzplylajxunlua.supabase.co/rest/v1/feedback", {
          method: "POST",
          headers: {
            "apikey": "sb_publishable_hBrtHt8ham91nuXSU_tdmA__BqcfIX1",
            "Authorization": "Bearer sb_publishable_hBrtHt8ham91nuXSU_tdmA__BqcfIX1",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
          },
          body: JSON.stringify(payload)
        });
        if (!resp.ok) {
          const t = await resp.text().catch(() => "");
          throw new Error(`HTTP ${resp.status} ${t.slice(0, 120)}`);
        }
      }
      success = true;
    } catch (err) {
      errMsg = (err && err.message) || String(err);
      console.warn("[領富 AI] feedback insert failed:", errMsg);
    }

    _feedbackSubmitting = false;
    if (success) {
      overlay.querySelector("#feedbackForm").hidden = true;
      overlay.querySelector("#fbSuccess").hidden = false;
      overlay.querySelector(".feedback-close-after").addEventListener("click", closeModal);
      // 5 秒後自動關
      setTimeout(closeModal, 5000);
    } else {
      submitBtn.disabled = false;
      submitBtn.textContent = "送出";
      // fallback：開 LINE 客服讓使用者直接傳訊
      if (confirm("送出失敗（" + errMsg + "）\n要直接從 LINE 客服反映嗎？")) {
        window.open(LINE_URL, "_blank", "noopener");
        closeModal();
      }
    }
  });
}

/* ============================================================
 * 偵測「內建瀏覽器」(LINE / FB / IG / WeChat 等 WebView)
 * 這些環境用 Google OAuth 會被擋 (disallowed_useragent 403)
 * 偵測到就跳警告 + 教學切外部瀏覽器
 * ============================================================ */
function detectInAppBrowser() {
  const ua = navigator.userAgent || "";
  if (/Line\//i.test(ua))             return { name: "LINE",      tip: "點右上角『⋯』→『在預設瀏覽器開啟』" };
  if (/FBAN|FBAV|FB_IAB/i.test(ua))   return { name: "Facebook",  tip: "點右下角『⋯』→『在外部瀏覽器中開啟』" };
  if (/Instagram/i.test(ua))          return { name: "Instagram", tip: "點右上角『⋯』→『在外部瀏覽器中開啟』" };
  if (/MicroMessenger/i.test(ua))     return { name: "微信 WeChat", tip: "點右上角『⋯』→『在瀏覽器開啟』" };
  if (/BytedanceWebview/i.test(ua))   return { name: "TikTok 抖音", tip: "點右上角『⋯』→『在瀏覽器開啟』" };
  if (/Twitter/i.test(ua))            return { name: "Twitter/X", tip: "點右上角分享圖示 → 在瀏覽器開啟" };
  if (/(KAKAOTALK|NAVER)/i.test(ua))  return { name: "Kakao/Naver", tip: "點選單在外部瀏覽器開啟" };
  // Generic WebView 偵測（iOS Safari WebView 與 Android WebView 沒有完整瀏覽器 UI）
  // 注意：純 Safari/Chrome 也可能匹配，避免誤判，只在「明確 WebView」時才警告
  return null;
}

function setupInAppBrowserWarning() {
  const inApp = detectInAppBrowser();
  if (!inApp) return;
  // 只在會員相關頁面顯示（OAuth 才會用到）
  if (!/login\.html|register\.html|member\.html/.test(location.pathname)) return;

  // 注入頂部警告 banner
  const banner = document.createElement("div");
  banner.className = "inapp-warning-banner";
  banner.innerHTML = `
    <div class="inapp-warning-inner">
      <span class="inapp-warning-icon">⚠</span>
      <div class="inapp-warning-text">
        <strong>您正在 ${inApp.name} 內建瀏覽器中</strong>
        <span>Google／Facebook 登入會被擋。請${inApp.tip}，再回來這頁。</span>
      </div>
      <button class="inapp-warning-copy" type="button">複製網址</button>
    </div>`;
  document.body.insertBefore(banner, document.body.firstChild);

  // 複製網址鈕
  banner.querySelector(".inapp-warning-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      banner.querySelector(".inapp-warning-copy").textContent = "✓ 已複製";
    } catch {
      // 退而求其次：顯示完整網址讓使用者長按複製
      banner.querySelector(".inapp-warning-text span").innerHTML +=
        `<br><span style="user-select:all;font-size:11px;color:#1B4332;background:#fff;padding:2px 6px;border-radius:3px;display:inline-block;margin-top:4px;">${location.href}</span>`;
      banner.querySelector(".inapp-warning-copy").textContent = "↑ 長按選取";
    }
  });

  // 攔截 Google / Facebook OAuth 按鈕 click → 改跳警告 modal（不要直接送出去被擋）
  const oauthBtns = document.querySelectorAll(
    "#googleLoginBtn, #googleRegBtn, #facebookLoginBtn, #facebookRegBtn"
  );
  oauthBtns.forEach(btn => {
    // 用 capture 階段先攔截，stopImmediatePropagation 擋掉原本的 click
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      _showInAppModal(inApp);
    }, true);
  });
}

function _showInAppModal(inApp) {
  const el = document.createElement("div");
  el.className = "inapp-modal-overlay";
  el.innerHTML = `
    <div class="inapp-modal-box">
      <div class="inapp-modal-icon">🚫</div>
      <h2>${inApp.name} 內無法使用<br>Google／Facebook 一鍵登入</h2>
      <p>這是 Google 的安全規定，不是網站問題。請依下方步驟改用外部瀏覽器，即可順利登入。</p>
      <div class="inapp-modal-steps">
        <div class="inapp-modal-step">
          <span class="inapp-modal-num">1</span>
          <span>${inApp.tip}</span>
        </div>
        <div class="inapp-modal-step">
          <span class="inapp-modal-num">2</span>
          <span>在開啟的 Chrome / Safari 中，再次點 Google 登入即可</span>
        </div>
      </div>
      <p style="font-size:13px;color:#666;margin-top:12px;">或者，您也可以在這個畫面直接用 <strong>Email 帳號密碼</strong> 註冊／登入。</p>
      <button class="inapp-modal-copy" type="button">📋 複製網址到剪貼簿</button>
      <button class="inapp-modal-close" type="button">我知道了</button>
    </div>`;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));

  el.querySelector(".inapp-modal-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      el.querySelector(".inapp-modal-copy").textContent = "✓ 已複製，請貼到 Chrome / Safari";
    } catch {
      el.querySelector(".inapp-modal-copy").innerHTML =
        `請長按選取下方網址：<br><span style="user-select:all;font-size:12px;background:#f0f3f8;padding:4px 8px;border-radius:4px;display:inline-block;margin-top:6px;">${location.href}</span>`;
    }
  });
  el.querySelector(".inapp-modal-close").addEventListener("click", () => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 200);
  });
}

/* ============================================================
 * 個股詳情頁動態 JSON-LD（GEO 用，讓 AI 助手能精準抽取個股資料）
 * ============================================================ */
function injectStockJsonLd() {
  // 只在 stock-detail.html 跑
  if (!location.pathname.includes("stock-detail")) return;
  const code = new URLSearchParams(location.search).get("code");
  if (!code) return;
  const s = findStock(code);
  if (!s) return;

  const marketLabel = s.market === "listed"   ? "上市"
                    : s.market === "otc"      ? "上櫃"
                    : s.market === "emerging" ? "興櫃" : (s.status || "");
  const co = (STOCK_DATA.companies && STOCK_DATA.companies[code]) || null;
  const rev = (STOCK_DATA.revenue && STOCK_DATA.revenue[code]) || null;
  const val = (STOCK_DATA.valuation && STOCK_DATA.valuation[code]) || null;
  const inst = (STOCK_DATA.institutional && STOCK_DATA.institutional[code]) || null;
  const url = SITE_ORIGIN + "/pages/stock-detail.html?code=" + code;
  const pct = pctChange(s.price, s.change);

  // ── 動態 SEO：每檔個股都有獨特 title / meta description / og tags ──
  const dirText = s.change > 0 ? "上漲" : s.change < 0 ? "下跌" : "持平";
  const pctText = (s.change >= 0 ? "+" : "") + pct.toFixed(2) + "%";

  // 1) <title>：「2330 台積電 股價 2,265 上漲 5.30% | 即時報價、月營收、本益比 - 領富 AI」
  const seoTitle = `${s.code} ${s.name} 股價 ${fmtPrice(s.price)} ${dirText} ${pctText} | ${marketLabel} ${s.category} - 領富 AI`;
  document.title = seoTitle;
  const pageTitleEl = document.getElementById("pageTitle");
  if (pageTitleEl) pageTitleEl.textContent = seoTitle;

  // 2) <meta description>：含關鍵資料點，<160 字
  let descParts = [`${s.code} ${s.name}（${marketLabel}・${s.category}）即時報價 ${fmtPrice(s.price)} 元`];
  descParts.push(`今日${dirText} ${pctText}、成交量 ${s.volume.toLocaleString()} 張`);
  if (val) {
    if (val.pe_ratio) descParts.push(`本益比 ${val.pe_ratio.toFixed(2)}`);
    if (val.yield_pct) descParts.push(`殖利率 ${val.yield_pct.toFixed(2)}%`);
    if (val.pb_ratio) descParts.push(`股價淨值比 ${val.pb_ratio.toFixed(2)}`);
  }
  if (rev && typeof rev.yoy === "number") descParts.push(`月營收年增 ${rev.yoy.toFixed(1)}%`);
  if (co && co.chairman) descParts.push(`董事長 ${co.chairman}`);
  descParts.push("資料來源 TWSE/TPEx 公開 API，每日更新");
  const seoDesc = descParts.join("、").slice(0, 158);

  function setMeta(selector, attrName, attrVal, contentVal) {
    let el = document.head.querySelector(selector);
    if (!el) {
      el = document.createElement("meta");
      el.setAttribute(attrName, attrVal);
      document.head.appendChild(el);
    }
    el.setAttribute("content", contentVal);
  }

  setMeta('meta[name="description"]', "name", "description", seoDesc);
  setMeta('meta[name="keywords"]', "name", "keywords",
    `${s.code},${s.name},${s.name}股價,${s.name}本益比,${s.name}月營收,${marketLabel},${s.category},台股,${s.code}即時報價`);

  // 3) Open Graph：分享到 LINE/FB 時的卡片
  setMeta('meta[property="og:title"]', "property", "og:title",
    `${s.code} ${s.name} ${fmtPrice(s.price)} 元 ${dirText} ${pctText}`);
  setMeta('meta[property="og:description"]', "property", "og:description", seoDesc);
  setMeta('meta[property="og:type"]', "property", "og:type", "article");
  setMeta('meta[property="og:url"]', "property", "og:url", url);
  setMeta('meta[property="og:image"]', "property", "og:image", SITE_ORIGIN + "/icons/icon-512.png");
  setMeta('meta[property="og:locale"]', "property", "og:locale", "zh_TW");
  setMeta('meta[property="og:site_name"]', "property", "og:site_name", "領富 AI");

  // Twitter Card
  setMeta('meta[name="twitter:card"]', "name", "twitter:card", "summary");
  setMeta('meta[name="twitter:title"]', "name", "twitter:title",
    `${s.code} ${s.name} | 領富 AI`);
  setMeta('meta[name="twitter:description"]', "name", "twitter:description", seoDesc);

  // 4) Canonical（正規 URL）
  let canonical = document.head.querySelector('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.rel = "canonical";
    document.head.appendChild(canonical);
  }
  canonical.href = url;

  const additionalProperty = [
    { "@type": "PropertyValue", "name": "市場", "value": marketLabel },
    { "@type": "PropertyValue", "name": "股票代號", "value": s.code },
    { "@type": "PropertyValue", "name": "公司名稱", "value": s.name },
    { "@type": "PropertyValue", "name": "產業類別", "value": s.category },
    { "@type": "PropertyValue", "name": "目前股價",  "value": s.price, "unitCode": "TWD" },
    { "@type": "PropertyValue", "name": "今日漲跌",  "value": s.change.toFixed(2) },
    { "@type": "PropertyValue", "name": "今日漲跌幅", "value": pct.toFixed(2) + "%" },
    { "@type": "PropertyValue", "name": "今日成交量", "value": s.volume + " 張" }
  ];
  // 估值指標
  if (val) {
    if (val.pe_ratio) additionalProperty.push({ "@type": "PropertyValue", "name": "本益比 P/E", "value": val.pe_ratio.toFixed(2) });
    if (val.yield_pct) additionalProperty.push({ "@type": "PropertyValue", "name": "殖利率", "value": val.yield_pct.toFixed(2) + "%" });
    if (val.pb_ratio) additionalProperty.push({ "@type": "PropertyValue", "name": "股價淨值比 P/B", "value": val.pb_ratio.toFixed(2) });
  }
  // 三大法人買賣超
  if (inst) {
    if (typeof inst.foreign_net_lots === "number") additionalProperty.push({ "@type": "PropertyValue", "name": "外資買賣超", "value": inst.foreign_net_lots.toLocaleString() + " 張" });
    if (typeof inst.trust_net_lots === "number") additionalProperty.push({ "@type": "PropertyValue", "name": "投信買賣超", "value": inst.trust_net_lots.toLocaleString() + " 張" });
    if (typeof inst.total_net_lots === "number") additionalProperty.push({ "@type": "PropertyValue", "name": "三大法人合計", "value": inst.total_net_lots.toLocaleString() + " 張" });
  }
  if (co) {
    if (co.chairman) additionalProperty.push({ "@type": "PropertyValue", "name": "董事長",   "value": co.chairman });
    if (co.president)additionalProperty.push({ "@type": "PropertyValue", "name": "總經理",   "value": co.president });
    if (co.founded)  additionalProperty.push({ "@type": "PropertyValue", "name": "成立日期", "value": co.founded });
    if (co.listed)   additionalProperty.push({ "@type": "PropertyValue", "name": "上市日期", "value": co.listed });
    if (co.capital)  additionalProperty.push({ "@type": "PropertyValue", "name": "實收資本額", "value": co.capital });
    if (co.address)  additionalProperty.push({ "@type": "PropertyValue", "name": "公司地址", "value": co.address });
    if (co.website)  additionalProperty.push({ "@type": "PropertyValue", "name": "公司網站", "value": co.website });
  }
  if (rev) {
    if (rev.period)         additionalProperty.push({ "@type": "PropertyValue", "name": "最新月營收期間", "value": rev.period });
    if (rev.monthRevenueFmt)additionalProperty.push({ "@type": "PropertyValue", "name": "當月營收",       "value": rev.monthRevenueFmt });
    if (typeof rev.yoy === "number")additionalProperty.push({ "@type": "PropertyValue", "name": "年增率",   "value": rev.yoy + "%" });
    if (typeof rev.mom === "number")additionalProperty.push({ "@type": "PropertyValue", "name": "月增率",   "value": rev.mom + "%" });
  }

  const jsonld = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "FinancialProduct",
        "@id": url + "#stock",
        "name": s.code + " " + s.name,
        "alternateName": [s.code, s.name],
        "category": marketLabel + " ・ " + s.category,
        "url": url,
        "description": seoDesc,
        "provider": { "@id": "https://leadfuai.com/#organization" },
        "additionalProperty": additionalProperty,
        "audience": { "@type": "Audience", "name": "Taiwan retail investors" },
        "inLanguage": "zh-TW",
        "offers": {
          "@type": "Offer",
          "price": s.price,
          "priceCurrency": "TWD",
          "availability": "https://schema.org/InStock",
          "validFrom": STOCK_DATA.updatedAt || new Date().toISOString().split("T")[0]
        }
      },
      {
        "@type": "Article",
        "@id": url + "#article",
        "headline": seoTitle,
        "description": seoDesc,
        "url": url,
        "datePublished": new Date().toISOString().split("T")[0],
        "dateModified": new Date().toISOString().split("T")[0],
        "author": { "@id": "https://leadfuai.com/#organization" },
        "publisher": { "@id": "https://leadfuai.com/#organization" },
        "about": { "@id": url + "#stock" },
        "inLanguage": "zh-TW",
        "isAccessibleForFree": true
      },
      co ? {
        "@type": "Organization",
        "@id": url + "#company",
        "name": co.name || s.name,
        "alternateName": co.abbrev || s.name,
        "tickerSymbol": s.code,
        "address": co.address,
        "telephone": co.phone,
        "url": co.website || undefined,
        "foundingDate": co.founded || undefined,
        "leiCode": co.taxId || undefined,
        "areaServed": "TW"
      } : null,
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "首頁", "item": "https://leadfuai.com/" },
          { "@type": "ListItem", "position": 2, "name": "股價總覽", "item": "https://leadfuai.com/pages/stocks.html" },
          { "@type": "ListItem", "position": 3, "name": s.code + " " + s.name, "item": url }
        ]
      }
    ].filter(x => x)
  };

  const tag = document.createElement("script");
  tag.type = "application/ld+json";
  tag.id = "stock-jsonld";
  tag.textContent = JSON.stringify(jsonld);
  // 移除舊的避免重複
  const old = document.getElementById("stock-jsonld");
  if (old) old.remove();
  document.head.appendChild(tag);
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
 * 明示「純資訊平台、不介入交易」，符合興櫃股票資訊網的法律定位
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
        <strong>領富 AI 為興櫃／興櫃股票公開資訊整理平台。</strong>
        本站<strong>不介入任何股票買賣、不撮合交易、不代為下單或過戶、不收受投資款項</strong>，
        亦非證券投資顧問事業。所有內容（含 AI 功能）僅為公開資料之整理與摘要，不構成投資建議。
        興櫃股票買賣應透過合法券商辦理，謹防詐騙 — 請參閱
        <a href="${fraudHref}">投資人防詐須知</a>。
      </span>
    </div>`;
  footer.parentNode.insertBefore(bar, footer);
}

/* ============================================================
 * PWA 註冊 + 安裝提示橫幅
 * ============================================================ */
function setupPWA() {
  // 註冊 Service Worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" })
      .then(() => console.log("[領富 AI] ✅ Service Worker 已註冊"))
      .catch(e => console.log("[領富 AI] SW 註冊失敗:", e.message));
  }

  // 已在 PWA standalone 模式 → 已安裝，不顯示
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  if (isStandalone) return;

  const DISMISS_KEY = "leadfu_pwa_dismissed_until";
  const dismissedUntil = parseInt(localStorage.getItem(DISMISS_KEY) || "0", 10);
  if (Date.now() < dismissedUntil) return;

  // 偵測平台 → 不同提示策略
  const ua = navigator.userAgent || "";
  const isIOS = /iPhone|iPad|iPod/.test(ua) && !/Windows/.test(ua);
  const isIOSSafari = isIOS && /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
  const isAndroid = /Android/.test(ua);

  let deferredPrompt = null;

  // === Android Chrome：用原生 beforeinstallprompt ===
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    setTimeout(() => showInstallBanner("native"), 3500);
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    hideInstallBanner();
    showToast("✓ 已加到主畫面，下次直接從手機桌面開", "success");
  });

  // === iOS Safari：永遠不會 fire beforeinstallprompt，直接跳手動教學 ===
  if (isIOSSafari) {
    setTimeout(() => showInstallBanner("ios"), 4000);
  }

  // === Fallback：手機但非 iOS/Android（很少），給通用提示 ===
  // 或 Android Chrome 沒 fire beforeinstallprompt 時（例如已多次拒絕）
  if (!isIOSSafari && /Mobi|Android/i.test(ua)) {
    // 等 8 秒看有沒 fire，沒就跳通用版
    setTimeout(() => {
      if (!deferredPrompt && !document.getElementById("pwaInstallBanner")) {
        showInstallBanner("generic");
      }
    }, 8000);
  }

  function showInstallBanner(kind) {
    if (document.getElementById("pwaInstallBanner")) return;
    const banner = document.createElement("div");
    banner.id = "pwaInstallBanner";
    banner.className = "pwa-install-banner pwa-install-" + kind;

    let inner = "";
    if (kind === "native") {
      inner = `
        <div class="pwa-icon">📱</div>
        <div class="pwa-text">
          <strong>加到主畫面</strong>
          <small>當 app 用，下次一鍵打開</small>
        </div>
        <button id="pwaInstallBtn" class="pwa-action">安裝</button>
        <button class="pwa-dismiss" id="pwaDismissBtn" aria-label="關閉">✕</button>`;
    } else if (kind === "ios") {
      inner = `
        <div class="pwa-icon">📱</div>
        <div class="pwa-text">
          <strong>把領富 AI 加到 iPhone 桌面</strong>
          <small>① 點下方 <svg width="14" height="14" viewBox="0 0 24 24" fill="#C5A572" style="vertical-align:-2px;"><path d="M16 5l-1.42 1.42-1.59-1.59V16h-1.98V4.83L9.42 6.42 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z"/></svg> 分享圖示　② 選「加到主畫面」</small>
        </div>
        <button class="pwa-action" id="pwaIosOkBtn">知道了</button>
        <button class="pwa-dismiss" id="pwaDismissBtn" aria-label="關閉">✕</button>`;
    } else {
      inner = `
        <div class="pwa-icon">📱</div>
        <div class="pwa-text">
          <strong>把領富 AI 加到桌面</strong>
          <small>點瀏覽器選單 <strong>⋮</strong> → 「<strong>加到主畫面</strong>」</small>
        </div>
        <button class="pwa-dismiss" id="pwaDismissBtn" aria-label="關閉">✕</button>`;
    }
    banner.innerHTML = inner;
    document.body.appendChild(banner);
    requestAnimationFrame(() => banner.classList.add("show"));

    const installBtn = banner.querySelector("#pwaInstallBtn");
    if (installBtn) {
      installBtn.addEventListener("click", async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        const result = await deferredPrompt.userChoice;
        deferredPrompt = null;
        hideInstallBanner();
        if (result.outcome === "dismissed") {
          localStorage.setItem(DISMISS_KEY, (Date.now() + 3 * 86400000).toString());
        }
      });
    }
    // iOS 「知道了」按鈕 → 壓 3 天不再跳
    const iosOkBtn = banner.querySelector("#pwaIosOkBtn");
    if (iosOkBtn) {
      iosOkBtn.addEventListener("click", () => {
        localStorage.setItem(DISMISS_KEY, (Date.now() + 3 * 86400000).toString());
        hideInstallBanner();
      });
    }
    banner.querySelector("#pwaDismissBtn").addEventListener("click", () => {
      // 主動關 → 暫停 3 天（之前 7 天太久，3 天剛好）
      localStorage.setItem(DISMISS_KEY, (Date.now() + 3 * 86400000).toString());
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

  // 壓 6 小時（不是整天），讓使用者一天能多看到 2-3 次
  const SUPPRESS_HOURS = 6;
  const dismissKey = "leadfu_ai_alert_dismissed_until";
  const dismissedUntil = parseInt(localStorage.getItem(dismissKey) || "0", 10);
  if (Date.now() < dismissedUntil) return;

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
      // 壓 6 小時不再跳
      localStorage.setItem(dismissKey, String(Date.now() + SUPPRESS_HOURS * 3600 * 1000));
      // 清理舊版 key（按日期的，現在改用 *_dismissed_until）
      Object.keys(localStorage).forEach(k => {
        if (k.startsWith("leadfu_ai_alert_") && k !== "leadfu_ai_alert_dismissed_until") {
          localStorage.removeItem(k);
        }
      });
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
  // 第 1 層 AI 問答工具（ai.html 用）
  parseAiQuery, aiQueryUrl, isNaturalLanguageQuery, normalizeSearchQuery,
  startStockLive,  // 個股詳情頁即時報價 polling
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

/* ============================================================
 * 即時行情列（5 秒延遲 - TWSE MIS 公開 API via /api/quote）
 * 只在首頁有 #liveQuoteBar 元素時運作。
 * 自動暫停：頁面 hidden 時不 poll；台股盤外（非 9:00-13:30）改為 30 秒一次
 * ============================================================ */
const LQ_POLL_OPEN  = 10_000;   // 盤中 10 秒
const LQ_POLL_CLOSED = 60_000;  // 盤外 60 秒（拿最後收盤）
const LQ_TIMEOUT     = 5_000;

let _lqTimer = null;
let _lqLast = {};   // code → 上一筆值（給閃爍動畫用）

function isMarketOpen() {
  const now = new Date();
  // 轉成台灣時區 — 簡單做：用 Asia/Taipei 偏移計算
  const tw = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Taipei" }));
  const day = tw.getDay();   // 0=日 6=六
  if (day === 0 || day === 6) return false;
  const m = tw.getHours() * 60 + tw.getMinutes();
  return m >= 9 * 60 && m <= 13 * 60 + 30;
}

function lqFlash(el, oldVal, newVal) {
  if (!el) return;
  if (oldVal === undefined || oldVal === null) return;
  if (newVal === oldVal) return;
  el.classList.remove("lq-flash-up", "lq-flash-down");
  // 強制重排觸發動畫
  void el.offsetWidth;
  el.classList.add(newVal > oldVal ? "lq-flash-up" : "lq-flash-down");
}

function fmtIndexValue(v) {
  if (v == null || v === "-" || v === "") return "--";
  const n = parseFloat(v);
  if (isNaN(n)) return "--";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function lqUpdateIndex(blockId, q) {
  const block = document.getElementById(blockId);
  if (!block || !q) return;
  const valEl = block.querySelector(".lq-value");
  const chEl  = block.querySelector(".lq-change");

  const z = parseFloat(q.z);  // 當前
  const y = parseFloat(q.y);  // 昨收
  if (isNaN(z) || isNaN(y) || z <= 0 || y <= 0) return;

  const change = z - y;
  const pct = (change / y * 100);

  const cls = change > 0 ? "up" : (change < 0 ? "down" : "flat");
  const arrow = change > 0 ? "▲" : (change < 0 ? "▼" : "─");

  const prev = _lqLast[blockId];
  valEl.textContent = fmtIndexValue(z);
  chEl.textContent = `${arrow} ${Math.abs(change).toFixed(2)} (${change > 0 ? '+' : ''}${pct.toFixed(2)}%)`;
  chEl.className = "lq-change " + cls;
  valEl.className = "lq-value " + cls;
  lqFlash(valEl, prev, z);
  _lqLast[blockId] = z;
}

function lqUpdateWatchlistRow(rowEl, q) {
  if (!rowEl || !q) return;
  const code = rowEl.dataset.code;
  const priceEl = rowEl.querySelector(".lqw-price");
  const chEl    = rowEl.querySelector(".lqw-change");

  // MIS：z = 當前成交（盤中），如果是 "-" 就用 pz（上一筆成交）
  let z = parseFloat(q.z);
  if (isNaN(z) || z <= 0) z = parseFloat(q.pz);
  const y = parseFloat(q.y);
  if (isNaN(z) || isNaN(y) || z <= 0 || y <= 0) return;

  const change = z - y;
  const pct = (change / y * 100);
  const cls = change > 0 ? "up" : (change < 0 ? "down" : "flat");

  const prev = _lqLast["w_" + code];
  priceEl.textContent = z.toFixed(2);
  chEl.textContent = `${change > 0 ? '+' : ''}${pct.toFixed(2)}%`;
  priceEl.className = "lqw-price " + cls;
  chEl.className = "lqw-change " + cls;
  lqFlash(priceEl, prev, z);
  _lqLast["w_" + code] = z;
}

function lqBuildWatchlistRows() {
  const container = document.getElementById("lqWatchlist");
  if (!container) return [];

  // 自選股優先，沒有就用熱門前 5
  let codes = [];
  try {
    const wl = JSON.parse(localStorage.getItem("leadfu_watchlist") || "[]");
    codes = wl.slice(0, 5);
  } catch { /* ignore */ }
  let useFallback = codes.length === 0;
  if (useFallback) {
    codes = (STOCK_DATA.stocks || [])
      .filter(s => s.price > 0 && (s.market === "listed" || s.market === "otc"))
      .sort((a, b) => (b.volume || 0) - (a.volume || 0))
      .slice(0, 5)
      .map(s => s.code);
  }

  // 解析每檔的 market → ex_ch prefix
  const items = codes.map(c => {
    const s = (STOCK_DATA.stocks || []).find(x => x.code === c);
    const market = s ? s.market : "listed";
    return {
      code: c,
      name: s ? s.name : c,
      market,
      prefix: market === "otc" ? "otc_" : "tse_"
    };
  });

  // 興櫃股 MIS 沒有，跳過
  const visible = items.filter(it => it.market !== "emerging");

  container.innerHTML = `
    <div class="lq-watchlist-label">${useFallback ? "熱門" : "自選"}</div>
    ${visible.map(it => `
      <a class="lq-w-row" data-code="${it.code}" data-market="${it.market}" href="${pageHref('stock-detail.html?code=' + it.code)}">
        <span class="lqw-name">${it.code} ${it.name}</span>
        <span class="lqw-price">--</span>
        <span class="lqw-change">--</span>
      </a>
    `).join("")}
  `;
  return visible;
}

async function lqFetchQuotes(exChList) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), LQ_TIMEOUT);
  try {
    const resp = await fetch("/api/quote?ex_ch=" + encodeURIComponent(exChList.join("|")), {
      signal: ctrl.signal,
      cache: "no-store"
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return await resp.json();
  } finally {
    clearTimeout(t);
  }
}

async function lqTick(watchlistItems) {
  const statusEl = document.getElementById("lqStatusText");
  const updEl    = document.getElementById("lqUpdated");

  const exChs = [
    "tse_t00.tw",   // 加權指數
    "otc_o00.tw",   // 櫃買指數
    ...watchlistItems.map(it => `${it.prefix}${it.code}.tw`)
  ];

  try {
    const data = await lqFetchQuotes(exChs);
    if (!data || data.rtcode !== "0000") {
      statusEl.textContent = "離線";
      return;
    }
    const arr = data.msgArray || [];
    arr.forEach(q => {
      if (q.c === "t00") lqUpdateIndex("lqTaiex", q);
      else if (q.c === "o00") lqUpdateIndex("lqOtc", q);
      else {
        const row = document.querySelector(`.lq-w-row[data-code="${q.c}"]`);
        if (row) lqUpdateWatchlistRow(row, q);
      }
    });
    const open = isMarketOpen();
    statusEl.textContent = open ? "盤中" : "盤後";
    statusEl.parentElement.classList.toggle("open", open);
    if (updEl) {
      const now = new Date();
      updEl.textContent = "更新 " + now.toLocaleTimeString("zh-TW", { hour12: false });
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = "重試中…";
  }
}

function lqStart() {
  const bar = document.getElementById("liveQuoteBar");
  if (!bar) return;   // 不是首頁

  const items = lqBuildWatchlistRows();
  const tick = () => lqTick(items);

  // 立刻跑一次
  tick();

  function schedule() {
    clearTimeout(_lqTimer);
    if (document.hidden) return;
    const interval = isMarketOpen() ? LQ_POLL_OPEN : LQ_POLL_CLOSED;
    _lqTimer = setTimeout(() => {
      tick();
      schedule();
    }, interval);
  }
  schedule();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clearTimeout(_lqTimer);
    } else {
      tick();
      schedule();
    }
  });
}

/* ============================================================
 * 單檔個股即時報價（stock-detail.html 用）
 * 更新：價格、漲跌、成交量、五檔買賣、開高低、昨收
 * 用戶可隨時按 #liveToggle 暫停／恢復
 * ============================================================ */
const _SL = {
  timer: null,
  paused: false,
  last: null,    // 上一筆 z（給閃爍動畫）
  code: null,
  market: null
};
const SL_POLL_OPEN   = 10_000;
const SL_POLL_CLOSED = 60_000;

function _slParseQueue(str) {
  // MIS 五檔格式：價1_價2_價3_價4_價5_  (張數則在另一欄)
  // b="251.0_249.0_247.0_246.0_240.0_"
  // bidQty / askQty 在 g / f 欄（也是底線分隔）
  if (!str || str === "-") return [];
  return str.split("_").filter(Boolean).map(parseFloat);
}

function _slRenderLevels(listEl, prices, qtys, side) {
  if (!listEl) return;
  // 過濾掉無效價（0 或 NaN）+ 同步移除對應量
  const valid = prices.map((p, i) => ({ p, q: qtys[i] || 0 })).filter(x => x.p > 0);
  if (!valid.length) {
    listEl.innerHTML = `<li class="ba-empty">無報價</li>`;
    return;
  }
  const maxQ = Math.max(1, ...valid.map(x => x.q));
  listEl.innerHTML = valid.map(({ p, q }) => {
    const pct = Math.min(100, (q / maxQ) * 100);
    return `<li class="ba-row">
      <span class="ba-bar ${side}" style="width:${pct}%;"></span>
      <span class="ba-price">${p.toFixed(2)}</span>
      <span class="ba-qty">${q.toLocaleString()}</span>
    </li>`;
  }).join("");
}

function _slFlash(el, oldV, newV) {
  if (!el || oldV == null) return;
  if (oldV === newV) return;
  el.classList.remove("sl-flash-up", "sl-flash-down");
  void el.offsetWidth;
  el.classList.add(newV > oldV ? "sl-flash-up" : "sl-flash-down");
}

function _slUpdate(q) {
  if (!q) return;

  // 主價格 — z 是當日成交、pz 是上一筆成交、若都沒有就用 y（昨收）保持顯示
  let z = parseFloat(q.z);
  if (isNaN(z) || z <= 0) z = parseFloat(q.pz);
  const y = parseFloat(q.y);
  const hasLivePrice = !isNaN(z) && !isNaN(y) && z > 0 && y > 0;

  if (hasLivePrice) {
    const change = z - y;
    const pct = (change / y * 100);
    const cls = change > 0 ? "up" : (change < 0 ? "down" : "flat");
    const arrowChar = change > 0 ? "▲" : (change < 0 ? "▼" : "─");

    const priceEl = document.getElementById("stockPrice");
    const chgEl   = document.getElementById("stockChange");
    const volEl   = document.getElementById("qsVol");

    if (priceEl) {
      _slFlash(priceEl, _SL.last, z);
      priceEl.textContent = z.toFixed(2);
      priceEl.classList.remove("up", "down", "flat");
      priceEl.classList.add(cls);
      _SL.last = z;
    }
    if (chgEl) {
      chgEl.textContent = `${arrowChar} ${Math.abs(change).toFixed(2)} (${change > 0 ? '+' : ''}${pct.toFixed(2)}%)`;
      chgEl.classList.remove("up", "down", "flat");
      chgEl.classList.add(cls);
    }
    // 成交量（張）
    const v = parseFloat(q.v);
    if (volEl && !isNaN(v)) volEl.textContent = v.toLocaleString() + " 張";
  }

  // 五檔買賣 — 即使沒成交，五檔還是有掛單，要顯示
  const panel = document.getElementById("bidAskPanel");
  if (panel) {
    panel.style.display = "block";
    const bidPrices = _slParseQueue(q.b);
    const askPrices = _slParseQueue(q.a);
    const bidQtys   = _slParseQueue(q.g);
    const askQtys   = _slParseQueue(q.f);
    _slRenderLevels(document.getElementById("bidList"), bidPrices, bidQtys, "bid");
    _slRenderLevels(document.getElementById("askList"), askPrices, askQtys, "ask");

    // OHLY
    const setNum = (id, val) => {
      const el = document.getElementById(id);
      if (!el) return;
      const n = parseFloat(val);
      el.textContent = (isNaN(n) || n <= 0) ? "--" : n.toFixed(2);
    };
    setNum("baOpen", q.o);
    setNum("baHigh", q.h);
    setNum("baLow",  q.l);
    setNum("baYest", q.y);
  }

  // 時間 + 狀態
  const metaEl = document.getElementById("liveMeta");
  if (metaEl) {
    const open = isMarketOpen();
    metaEl.textContent = (open ? "盤中 " : "盤後 ") + (q.t || "");
  }
}

async function _slTick() {
  if (_SL.paused) return;
  const prefix = _SL.market === "otc" ? "otc_" : "tse_";
  const ex_ch = `${prefix}${_SL.code}.tw`;
  try {
    const resp = await fetch("/api/quote?ex_ch=" + encodeURIComponent(ex_ch), {
      cache: "no-store"
    });
    if (!resp.ok) return;
    const data = await resp.json();
    if (data && data.msgArray && data.msgArray[0]) {
      _slUpdate(data.msgArray[0]);
    }
  } catch (e) {
    // 靜默失敗，下一輪繼續
  }
}

function _slSchedule() {
  clearTimeout(_SL.timer);
  if (_SL.paused || document.hidden) return;
  const interval = isMarketOpen() ? SL_POLL_OPEN : SL_POLL_CLOSED;
  _SL.timer = setTimeout(async () => {
    await _slTick();
    _slSchedule();
  }, interval);
}

function _slSetButton(state) {
  const btn = document.getElementById("liveToggle");
  if (!btn) return;
  btn.classList.toggle("paused", state === "paused");
  const txt = btn.querySelector(".live-toggle-text");
  if (txt) txt.textContent = state === "paused" ? "已暫停" : "即時";
}

function startStockLive(code, stock) {
  if (!code || !stock) return;
  // 興櫃股 MIS 沒提供，不打
  if (stock.market === "emerging") return;

  _SL.code = code;
  _SL.market = stock.market || "listed";
  _SL.last = null;
  _SL.paused = false;
  _slSetButton("running");

  // 立刻跑一次
  _slTick().then(_slSchedule);

  // Toggle 暫停／恢復
  const btn = document.getElementById("liveToggle");
  if (btn && !btn._wired) {
    btn._wired = true;
    btn.addEventListener("click", () => {
      _SL.paused = !_SL.paused;
      _slSetButton(_SL.paused ? "paused" : "running");
      if (_SL.paused) {
        clearTimeout(_SL.timer);
      } else {
        _slTick().then(_slSchedule);
      }
    });
  }

  // 隱藏分頁暫停
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clearTimeout(_SL.timer);
    } else if (!_SL.paused) {
      _slTick().then(_slSchedule);
    }
  });
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

  // 7. 三大法人買賣超（上市 TWSE T86）
  try {
    const live = await fetchJson("institutional_live.json");
    if (live.data) {
      STOCK_DATA.institutional = live.data;
      STOCK_DATA.institutionalSourceDate = live.sourceDate;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆三大法人買賣超 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 三大法人未載入 (${e.message})`);
  }

  // 8. 估值指標（本益比/殖利率/股價淨值比 - TWSE BWIBBU_d）
  try {
    const live = await fetchJson("valuation_live.json");
    if (live.data) {
      STOCK_DATA.valuation = live.data;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆估值指標 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 估值指標未載入 (${e.message})`);
  }

  // 9. 融資融券（散戶籌碼面 - TWSE MI_MARGN）
  try {
    const live = await fetchJson("margin_live.json");
    if (live.data) {
      STOCK_DATA.margin = live.data;
      STOCK_DATA.marginSourceDate = live.sourceDate;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆融資融券 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 融資融券未載入 (${e.message})`);
  }

  // 10. 上櫃融資融券（TPEx margin balance）
  try {
    const live = await fetchJson("margin_tpex_live.json");
    if (live.data) {
      STOCK_DATA.marginTpex = live.data;
      STOCK_DATA.marginTpexSourceDate = live.sourceDate;
      // 合併到 margin 主表（前端可用 market 欄區分）
      STOCK_DATA.margin = Object.assign({}, STOCK_DATA.margin || {}, live.data);
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆上櫃融資融券 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 上櫃融資融券未載入 (${e.message})`);
  }

  // 11. 借券（融券 + 借券賣出 - TWSE TWT93U）
  try {
    const live = await fetchJson("sbl_live.json");
    if (live.data) {
      STOCK_DATA.sbl = live.data;
      STOCK_DATA.sblSourceDate = live.sourceDate;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆借券資料 (${live.sourceDate})`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 借券資料未載入 (${e.message})`);
  }

  // 12. 技術指標（KD / MACD / 布林 / RSI / MA - 由 calc_indicators.py 計算）
  try {
    const live = await fetchJson("indicators_live.json");
    if (live.data) {
      STOCK_DATA.indicators = live.data;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆技術指標`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 技術指標未載入 (${e.message})`);
  }

  // 13. 大股東名單（MOPS t187ap02）
  try {
    const live = await fetchJson("insider_live.json");
    if (live.data) {
      STOCK_DATA.insider = live.data;
      console.log(`[領富 AI] ✅ ${live.count || 0} 筆大股東名單`);
    }
  } catch (e) {
    console.log(`[領富 AI] ℹ️ 大股東名單未載入 (${e.message})`);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  setupSEO();
  loadGA();
  setupMobileNav();
  setupBottomTabBar();
  setupHideableHeader();
  setupDisclaimer();
  setupInAppBrowserWarning();   // 偵測 LINE/FB/IG/WeChat 內建瀏覽器，跳警告擋掉 OAuth
  setupThemeToggle();           // 🎨 主題切換（墨綠 ↔ 喜氣紅）
  setupFeedbackWidget();        // 漂浮回饋按鈕，每頁右下角
  setupPWA();
  setupAntiFraudBanner();       // 📢 防詐騙官方資訊條（首頁、可關閉 7 天）
  injectFooterFraudReminder();  // 📢 全站 footer 防詐聲明（給 SEO + AI 爬蟲穩定錨點）
  setupOnboarding();            // 👋 首次訪客 3 步驟引導浮層（只首頁、且首次造訪）
  renderDate();

  // 先抓即時資料再渲染表格
  await loadLiveData();
  _resolveReady();   // 通知所有 inline script 資料就緒，可以開始 render

  injectStockJsonLd();  // GEO：個股詳情頁注入 JSON-LD（FinancialProduct + Organization + BreadcrumbList）
  renderTicker();
  lqStart();           // 即時行情列（首頁才有 #liveQuoteBar，其他頁自動跳過）
  renderHeroCards();   // 首頁三張卡片（其他頁沒有 #heroCards 會自動跳過）
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
