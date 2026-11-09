"use strict";
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const state = {
  view: "chat",
  transport: "route",
  request: 0,
  controller: null,
  last: null,
  ready: false,
  chatAvailable: false,
  chatBusy: false,
};
let sessionId = sessionStorage.getItem("hk-chat-session");
if (!sessionId) {
  sessionId = crypto.randomUUID();
  sessionStorage.setItem("hk-chat-session", sessionId);
}
const welcome = $("#result-content").cloneNode(true);
const views = {
  knowledge: {
    label: "出行指南",
    title: "先了解，再出发",
    kicker: "LOCAL KNOWLEDGE",
    button: "查找指南",
    note: "参考资料附有来源与日期，不代表实时营业或价格。",
  },
  overview: {
    label: "出行概览",
    title: "今天，想去哪里？",
    kicker: "YOUR NEXT STOP",
    button: "查看出行概览",
    note: "只查询你选择的内容，各来源同时查询。",
  },
  weather: {
    label: "天气与预报",
    title: "出门前，看看天",
    kicker: "A LOOK AT THE SKY",
    button: "查询天气",
    note: "香港天文台资料，观测时间随结果显示。",
  },
  food: {
    label: "附近美食",
    title: "附近有什么好吃的",
    kicker: "A TASTE OF THE NEIGHBOURHOOD",
    button: "寻找餐厅",
    note: "按直线距离查看 OpenStreetMap 上的餐厅和饮食店。",
  },
  attractions: {
    label: "景点探索",
    title: "找个值得去的地方",
    kicker: "SOMETHING WORTH A DETOUR",
    button: "发现景点",
    note: "发现附近景点。出发前请确认开放时间。",
  },
  transport: {
    label: "地铁查询",
    title: "下一站，怎么走",
    kicker: "FIND YOUR WAY",
    button: "查询地铁",
    note: "港铁路线和列车到站。",
  },
  chat: { label: "出行助手" },
};
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = String(text);
  return e;
}
function icon(name) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const u = document.createElementNS(s.namespaceURI, "use");
  u.setAttribute("href", `#i-${name}`);
  s.append(u);
  s.setAttribute("aria-hidden", "true");
  return s;
}
function cleanURL(value) {
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) ? u.href : null;
  } catch {
    return null;
  }
}
function link(text, url) {
  const a = el("a", "", text);
  const href = cleanURL(url);
  if (href) {
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  }
  return a;
}
function hkDay(date = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Hong_Kong",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}
function clock() {
  $("#hong-kong-date").textContent = new Intl.DateTimeFormat(
    window.uiLanguage?.() === "en" ? "en-HK" : "zh-CN",
    {
      timeZone: "Asia/Hong_Kong",
      month: "long",
      day: "numeric",
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
  ).format(new Date());
}
clock();
setInterval(clock, 30000);
function field(
  name,
  label,
  {
    value = "",
    placeholder = "",
    type = "text",
    options = null,
    wide = false,
    hint = "",
  } = {},
) {
  const wrap = el("div", `field${wide ? " wide" : ""}`);
  const lab = el("label", "", label);
  lab.htmlFor = `f-${name}`;
  wrap.append(lab);
  let input;
  if (options) {
    input = el("select");
    for (const [v, t] of options) {
      const o = el("option", "", t);
      o.value = v;
      input.append(o);
    }
    input.value = value || options[0][0];
  } else {
    input = el("input");
    input.type = type;
    input.value = value;
    input.placeholder = placeholder;
    input.maxLength = 120;
    if (type === "date") {
      input.min = hkDay();
      input.max = hkDay(new Date(Date.now() + 9 * 86400000));
    }
  }
  input.id = `f-${name}`;
  input.name = name;
  wrap.append(input);
  if (hint) wrap.append(el("small", "", hint));
  return wrap;
}
function fval(name) {
  return $(`#f-${name}`)?.value?.trim() || "";
}
const radii = [
  ["500", "500 米"],
  ["1000", "1 公里"],
  ["2000", "2 公里"],
  ["3000", "3 公里"],
];
const lines = [
  ["", "该站全部线路"],
  ["TWL", "荃湾线 · TWL"],
  ["EAL", "东铁线 · EAL"],
  ["TML", "屯马线 · TML"],
  ["KTL", "观塘线 · KTL"],
  ["ISL", "港岛线 · ISL"],
  ["TKL", "将军澳线 · TKL"],
  ["TCL", "东涌线 · TCL"],
  ["SIL", "南港岛线 · SIL"],
  ["DRL", "迪士尼线 · DRL"],
  ["AEL", "机场快线 · AEL"],
];
function buildForm() {
  const v = state.view,
    fields = $("#form-fields"),
    extra = $("#form-extra");
  fields.replaceChildren();
  extra.replaceChildren();
  const config = views[v];
  if (v === "chat") return;
  $("#page-label").textContent = config.label;
  $("#workspace-title").textContent = config.title;
  $("#form-kicker").textContent = config.kicker;
  $("#query-button-text").textContent = config.button;
  $("#form-note").textContent = config.note;
  $("#transport-modes").hidden = v !== "transport";
  const add = (...args) => fields.append(field(...args));
  if (v === "knowledge")
    add("knowledge-query", "想了解什么", {
      value: "雨天带老人去室内博物馆，轮椅设施",
      wide: true,
    });
  if (v === "overview") {
    add("location", "目的地", { value: "香港理工大学" });
    add("radius", "附近范围", { value: "1000", options: radii });
    for (const [id, label, checked] of [
      ["overview-food", "附近美食", true],
      ["overview-attractions", "附近景点", false],
    ]) {
      const wrap = el("label"),
        check = el("input");
      check.type = "checkbox";
      check.id = id;
      check.checked = checked;
      wrap.append(check, document.createTextNode(label));
      extra.append(wrap);
    }
  }
  if (["food", "attractions"].includes(v)) {
    add("location", "目的地", {
      value: "尖沙咀",
      placeholder: "输入香港地名，例如尖沙咀、沙田",
    });
    if (v === "food")
      add("category", "想吃什么", {
        value: "all",
        options: [
          ["all", "全部饮食"],
          ["restaurant", "餐厅"],
          ["cafe", "咖啡店"],
          ["fast_food", "快餐"],
          ["food_court", "美食广场"],
          ["bar", "酒吧"],
          ["pub", "酒馆"],
          ["ice_cream", "冰淇淋店"],
          ["biergarten", "啤酒花园"],
        ],
      });
    else
      add("category", "想探索什么", {
        value: "all",
        options: [
          ["all", "所有景点"],
          ["museum", "博物馆"],
          ["gallery", "画廊"],
          ["viewpoint", "观景点"],
          ["attraction", "景点"],
          ["theme_park", "主题乐园"],
          ["zoo", "动物园"],
        ],
      });
    add("radius", "附近范围", {
      value: v === "food" ? "500" : "1000",
      options: radii,
    });
    extra.textContent =
      v === "food"
        ? "© OpenStreetMap contributors · 按直线距离排序"
        : "© OpenStreetMap contributors";
  }
  if (v === "weather") {
    add("kind", "天气资料", {
      value: "rhrread",
      options: [
        ["rhrread", "当前天气报告"],
        ["flw", "本港天气预报"],
        ["fnd", "九天预报"],
        ["warnsum", "正在生效的警告"],
        ["warningInfo", "警告详情"],
        ["swt", "特别天气提示"],
        ["temperature", "当前气温"],
        ["humidity", "当前湿度"],
        ["wind", "当前风向风速"],
        ["heat_index", "暑热指数"],
        ["uv", "全港紫外线"],
        ["visibility", "能见度"],
      ],
    });
    add("place", "地点（可选）", {
      placeholder: "留空列出各站，例如黄埔则查最近的站",
    });
    add("language", "资料语言", {
      value: window.uiLanguage?.() === "en" ? "en" : "sc",
      options: [
        ["sc", "简体中文"],
        ["tc", "繁體中文"],
        ["en", "English"],
      ],
    });
    extra.textContent =
      "全港报告和紫外线不用填地点。分区资料留空列出各站，填写地名则查最近的站。";
    syncWeatherFields();
    $("#f-kind").addEventListener("change", syncWeatherFields);
  }
  if (v === "transport") {
    $$("#transport-modes button").forEach((b) =>
      b.classList.toggle("selected", b.dataset.transport === state.transport),
    );
    if (state.transport === "map") {
      add("origin", "出发地点", { value: "香港理工大学" });
      add("destination", "目的地点", { value: "尖沙咀海滨" });
      add("mode", "出行方式", {
        options: [
          ["foot-walking", "步行"],
          ["driving-car", "驾车"],
          ["cycling-regular", "骑行"],
          ["foot-hiking", "徒步"],
        ],
      });
      extra.textContent =
        "路线由 OpenRouteService 规划，地图来自 OpenStreetMap。";
    } else if (state.transport === "route") {
      add("origin", "出发站", { value: "沙田" });
      add("destination", "目的站", { value: "尖沙咀" });
      add("airport", "机场快线", {
        options: [
          ["no", "不使用机场快线"],
          ["yes", "允许使用机场快线"],
        ],
      });
      extra.textContent = "先最少线路换乘，再最少站间路段";
    } else if (state.transport === "mtr") {
      add("station", "港铁车站", { value: "尖沙咀" });
      add("line", "所属线路", { value: "TWL", options: lines, wide: true });
      extra.textContent = "保留月台、终点、预计到站及延误信息";
    }
  }
}
const stationWeather = new Set([
  "temperature",
  "humidity",
  "wind",
  "heat_index",
  "visibility",
]);
function syncWeatherFields() {
  const place = $("#f-place");
  if (!place) return;
  place.closest(".field").hidden = !stationWeather.has(fval("kind"));
}
function resetResults() {
  state.last = null;
  $("#export-results").hidden = true;
  $("#result-meta").textContent = "";
  $("#results-title").textContent = "从这里开始";
  $("#result-content").replaceChildren(
    ...[...welcome.children].map((e) => e.cloneNode(true)),
  );
}
function setView(view) {
  if (!views[view]) return;
  if (state.controller) state.controller.abort();
  state.request++;
  state.view = view;
  document.body.classList.toggle("chat-view", view === "chat");
  $(".hero").hidden = view === "chat";
  state.controller = null;
  $("#query-progress").hidden = true;
  $("#query-button").disabled = false;
  $$(".nav-item").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
    if (b.dataset.view === view) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  $("#page-label").textContent = views[view].label;
  $("#query-workspace").hidden = view === "chat";
  $("#chat-workspace").hidden = view !== "chat";
  if (view !== "chat") {
    buildForm();
    resetResults();
  }
}
function showToast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  setTimeout(() => (t.hidden = true), 2600);
}
async function api(path, body, signal) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("服务暂时没有响应，请稍后重试。");
  }
  if (!response.ok) {
    const messages = {
      CHAT_NOT_CONFIGURED: "出行助手暂时不可用，请先使用其他查询。",
      MODEL_ERROR: "出行助手暂时没有响应，请稍后再试。",
      CHAT_ERROR: "这次回答未完成，请重新发送。",
    };
    throw new Error(
      messages[data.error?.code] ||
        data.error?.message ||
        "请求未完成，请重试。",
    );
  }
  return data;
}
async function refreshStatus() {
  try {
    const data = await api("/api/status");
    state.ready = true;
    state.chatAvailable = data.chat_available;
    $("#connection-dot").className = "status-dot ready";
    $("#connection-text").textContent = "服务正常";
    $("#tool-count").textContent = "香港天气与出行";
    $("#chat-config-note").className = "notice warning";
    $("#chat-config-note").hidden = data.chat_available;
    $("#chat-config-note").textContent =
      "出行助手暂时不可用，可以先查询天气、餐厅和地铁。";
    $("#chat-send").disabled = !state.chatAvailable;
  } catch (e) {
    state.ready = false;
    $("#connection-dot").className = "status-dot failed";
    $("#connection-text").textContent = "暂时无法连接";
    $("#tool-count").textContent = "请稍后刷新重试";
    $("#chat-config-note").hidden = false;
    $("#chat-config-note").textContent = "连接暂时中断，请稍后重试。";
  }
}
function requestForForm() {
  const v = state.view,
    location = fval("location"),
    radius = Number(fval("radius") || 1000);
  if (["food", "attractions"].includes(v) && !location)
    throw new Error("请先输入目的地。");
  if (v === "knowledge")
    return {
      tool: "search_travel_knowledge",
      arguments: { query: fval("knowledge-query"), limit: 5 },
    };
  if (v === "overview")
    return {
      tool: "get_outing_overview",
      arguments: {
        location,
        radius_m: radius,
        include_food: $("#overview-food").checked,
        include_attractions: $("#overview-attractions").checked,
      },
    };
  if (v === "food")
    return {
      tool: "search_restaurants",
      arguments: {
        location,
        radius_m: radius,
        category: fval("category"),
      },
    };
  if (v === "attractions")
    return {
      tool: "search_attractions",
      arguments: {
        location,
        radius_m: radius,
        category: fval("category"),
      },
    };
  if (v === "weather") {
    return {
      tool: "get_weather",
      arguments: {
        kind: fval("kind"),
        place: stationWeather.has(fval("kind")) ? fval("place") : "",
      },
    };
  }
  if (state.transport === "map") {
    if (!fval("origin") || !fval("destination"))
      throw new Error("请输入起点和终点。");
    return {
      tool: "get_route",
      arguments: {
        origin: fval("origin"),
        destination: fval("destination"),
        mode: fval("mode"),
      },
    };
  }
  if (state.transport === "route") {
    if (!fval("origin") || !fval("destination"))
      throw new Error("请输入出发站和目的站。");
    return {
      tool: "plan_mtr_route",
      arguments: {
        origin: fval("origin"),
        destination: fval("destination"),
        include_airport_express: fval("airport") === "yes",
      },
    };
  }
  if (state.transport === "mtr") {
    if (!fval("station")) throw new Error("请输入港铁车站。");
    return {
      tool: "get_mtr_arrivals",
      arguments: {
        station: fval("station"),
        line: fval("line"),
        lang: window.uiLanguage?.() === "en" ? "EN" : "TC",
      },
    };
  }
  throw new Error("请选择港铁路线或列车到站。");
}
function notice(message, type = "info") {
  return el("div", `notice ${type}`, message);
}
function card(title, badgeText = "", badgeClass = "") {
  const root = el("article", "result-card");
  const head = el("div", "card-head");
  head.append(el("h3", "", title));
  if (badgeText) head.append(el("span", `badge ${badgeClass}`, badgeText));
  root.append(head);
  return root;
}
function textBlock(parent, text) {
  if (text) parent.append(el("p", "prose", text));
}
function item(title, meta, badgeText) {
  const e = el("div", "data-item"),
    h = el("div", "item-title");
  h.append(el("span", "", title));
  if (badgeText) h.append(el("span", "badge", badgeText));
  e.append(h);
  if (meta) e.append(el("div", "item-meta", meta));
  return e;
}
function valueText(value) {
  return value === undefined || value === null || value === ""
    ? "未提供"
    : String(value);
}
function isBad(r) {
  return (
    !r ||
    r.ok === false ||
    ["error", "timeout", "service_unavailable", "no_forecast"].includes(
      r.status,
    )
  );
}
function weatherCard(r, title = "天气资料") {
  const d = r.data || {};
  const c = card(title, "香港天文台");
  if (isBad(r)) {
    c.append(notice(r.error?.message || "此项查询未完成。", "warning"));
    return [c];
  }
  if (Array.isArray(d.rows)) {
    c.append(table(d.rows));
    return [c];
  }
  if (Array.isArray(d.weatherForecast)) {
    if (!d.weatherForecast.length) {
      textBlock(c, "未找到对应日期的预报。");
      return [c];
    }
    const list = el("div", "data-list");
    for (const row of d.weatherForecast) {
      const min = row.forecastMintemp?.value,
        max = row.forecastMaxtemp?.value;
      const temp =
        min !== undefined && max !== undefined ? `${min}–${max} °C` : "";
      const rowItem = item(
        [row.forecastDate, row.week].filter(Boolean).join(" · "),
        row.forecastWeather,
        temp,
      );
      if (row.forecastWind)
        rowItem.append(el("div", "item-meta", row.forecastWind));
      list.append(rowItem);
    }
    c.append(list);
    return [c];
  }
  const temps = d.temperature?.data;
  const humidity = d.humidity?.data;
  if (Array.isArray(temps) && temps.length) {
    const hko =
      temps.find((t) => /天文台|observatory/i.test(t.place)) || temps[0];
    const metrics = el("div", "metrics");
    const m = el("div", "metric"),
      number = el("strong", "", valueText(hko.value));
    number.append(el("span", "unit", hko.unit === "C" ? "°C" : hko.unit || ""));
    m.append(number, el("small", "", hko.place || "观测站"));
    metrics.append(m);
    if (humidity?.length) {
      const h = el("div", "metric");
      h.append(
        el("strong", "", `${valueText(humidity[0].value)}%`),
        el("small", "", "相对湿度"),
      );
      metrics.append(h);
    }
    c.append(metrics);
    if (d.updateTime)
      c.append(el("p", "item-meta", `官方更新时间：${d.updateTime}`));
  }
  if (d.forecastDesc || d.forecastPeriod) {
    textBlock(c, [d.forecastPeriod, d.forecastDesc].filter(Boolean).join("\n"));
    if (d.outlook) textBlock(c, `展望：${d.outlook}`);
  }
  if (d.generalSituation && !d.forecastDesc) textBlock(c, d.generalSituation);
  if (!temps && !d.forecastDesc && !d.generalSituation) {
    const values = Array.isArray(d) ? d : Object.values(d);
    if (!values.length) textBlock(c, "当前未返回天气警告或提示。");
    else {
      for (const entry of values) {
        if (entry && typeof entry === "object" && !Array.isArray(entry)) {
          const lines = [
            entry.name,
            entry.type,
            entry.code,
            entry.actionCode,
            entry.desc,
            ...(Array.isArray(entry.contents) ? entry.contents : []),
          ].filter(Boolean);
          if (lines.length)
            c.append(item(lines[0], lines.slice(1).join(" · ")));
        } else if (Array.isArray(entry))
          for (const x of entry)
            textBlock(c, x.desc || x.name || JSON.stringify(x));
        else if (typeof entry === "string") textBlock(c, entry);
      }
    }
  }
  return [c];
}
function placeResultCard(row) {
  const c = card(
    row.name || "未提供名称",
    Number.isFinite(row.distance_m) ? `${row.distance_m} 米` : "",
    "community",
  );
  if (row.address) c.append(el("p", "item-meta", row.address));
  if (row.opening_hours_raw)
    c.append(
      el(
        "div",
        "item-meta",
        `登记营业时间：${row.opening_hours_raw}（未经实时确认）`,
      ),
    );
  if (row.cuisine) c.append(el("div", "item-meta", `菜系标签：${row.cuisine}`));
  if (row.text) c.append(el("p", "prose", row.text));
  const actions = el("div", "item-actions");
  if (Number.isFinite(row.latitude) && Number.isFinite(row.longitude))
    actions.append(
      link(
        "在地图查看",
        `https://www.openstreetmap.org/?mlat=${row.latitude}&mlon=${row.longitude}#map=18/${row.latitude}/${row.longitude}`,
      ),
    );
  if (row.osm_url) actions.append(link("OSM 记录", row.osm_url));
  if (actions.children.length) c.append(actions);
  return c;
}
function pagedResults(r, title) {
  const wrap = el("div", "paged-results");
  if (isBad(r)) {
    const c = card(title, "社区地图", "community");
    c.append(notice(r.error?.message || "资料暂时不可用。", "warning"));
    wrap.append(c);
    return [wrap];
  }
  const rows = Array.isArray(r.data) ? r.data : [];
  if (!rows.length) {
    const c = card(title, "社区地图", "community");
    textBlock(c, "本次查询没有匹配结果；不代表当地没有相关地点。");
    wrap.append(c);
    return [wrap];
  }
  const pageSize = 4;
  let page = 0;
  const grid = el("div", "result-grid");
  const pager = el("div", "result-pager");
  const prev = el("button", "secondary-button", "上一页");
  const next = el("button", "secondary-button", "下一页");
  const label = el("span", "", "");
  prev.type = "button";
  next.type = "button";
  pager.append(prev, label, next);
  function show() {
    const pages = Math.max(1, Math.ceil(rows.length / pageSize));
    page = Math.min(page, pages - 1);
    grid.replaceChildren(
      ...rows
        .slice(page * pageSize, page * pageSize + pageSize)
        .map(placeResultCard),
    );
    label.textContent = `${page + 1} / ${pages}`;
    prev.disabled = page === 0;
    next.disabled = page >= pages - 1;
    pager.hidden = rows.length <= pageSize;
  }
  prev.addEventListener("click", () => {
    page -= 1;
    show();
  });
  next.addEventListener("click", () => {
    page += 1;
    show();
  });
  show();
  wrap.append(grid, pager);
  return [wrap];
}
function table(rows) {
  const wrap = el("div", "table-wrap");
  if (!rows.length) {
    wrap.append(el("p", "prose", "没有匹配记录。"));
    return wrap;
  }
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))].slice(0, 8),
    t = el("table"),
    head = el("thead"),
    tr = el("tr");
  for (const k of keys) tr.append(el("th", "", k));
  head.append(tr);
  t.append(head);
  const body = el("tbody");
  for (const row of rows.slice(0, 50)) {
    const line = el("tr");
    for (const key of keys)
      line.append(
        el(
          "td",
          "",
          typeof row[key] === "object"
            ? JSON.stringify(row[key])
            : valueText(row[key]),
        ),
      );
    body.append(line);
  }
  t.append(body);
  wrap.append(t);
  if (rows.length > 50)
    wrap.append(el("p", "item-meta", "页面展示前50条，完整记录可展开或导出。"));
  return wrap;
}
function routeCard(r) {
  const c = card("港铁路线", "换乘方案");
  c.classList.add("full");
  if (isBad(r)) {
    c.append(notice(r.error?.message || "无法规划路线。", "warning"));
    return [c];
  }
  const d = r.data;
  const summary = el("div", "route-summary");
  summary.append(
    el("strong", "", `${d.origin.name_zh} → ${d.destination.name_zh}`),
    el("span", "badge", `${d.line_changes} 次线路换乘`),
    el("span", "badge", `${d.ride_stop_count} 个站间路段`),
  );
  c.append(summary);
  for (const segment of d.segments || []) {
    const e = el("div", "route-segment");
    e.append(
      el("span", `line-badge line-${segment.line.toLowerCase()}`, segment.line),
      el(
        "div",
        "route-stations",
        segment.stations.map((s) => s.name_zh || s.code).join(" → "),
      ),
    );
    if (segment.may_require_same_line_train_change)
      e.append(
        el(
          "p",
          "route-transfer",
          "这一路段可能需要同线换车，不应理解为一班直达。",
        ),
      );
    c.append(e);
  }
  textBlock(
    c,
    "按最少线路换乘、再最少站间路段选择。不含不同站码的步行连接、实时停运、票价及耗时保证。",
  );
  return [c];
}
function mtrCard(r) {
  const c = card("港铁列车到站", "港铁官方");
  c.classList.add("full");
  if (isBad(r)) {
    c.append(
      notice(
        r.error?.message || r.data?.message || "暂无可用列车资料。",
        "warning",
      ),
    );
    return [c];
  }
  const raw = r.data;
  if (raw.isdelay === "Y")
    c.append(notice("官方资料显示延误，请结合原始信息确认。", "warning"));
  const records = Object.values(raw.data || {});
  for (const station of records) {
    if (station.line_name) c.append(el("h3", "", station.line_name));
    for (const direction of ["UP", "DOWN"]) {
      const trains = station[direction] || [];
      if (!trains.length) {
        c.append(el("p", "item-meta", `${direction}：这个方向现在没有班次。`));
        continue;
      }
      const dests = [
        ...new Set(
          trains.map(
            (train) => r.destination_names?.[train.dest] || train.dest,
          ),
        ),
      ];
      c.append(el("p", "", `${direction} · 开往${dests.join("、")}`));
      const wrap = el("div", "table-wrap"),
        t = el("table"),
        head = el("tr");
      for (const name of [
        "行驶方向 / 终点",
        "月台",
        "预计分钟",
        "预计到站时间",
        "有效性",
      ])
        head.append(el("th", "", name));
      const thead = el("thead");
      thead.append(head);
      t.append(thead);
      const body = el("tbody");
      for (const train of trains) {
        const row = el("tr");
        for (const value of [
          `${direction} · ${r.destination_names?.[train.dest] || train.dest}`,
          train.plat,
          train.ttnt,
          train.time,
          train.valid === "Y" ? "已提供" : "待确认",
        ])
          row.append(el("td", "", valueText(value)));
        body.append(row);
      }
      t.append(body);
      wrap.append(t);
      c.append(wrap);
    }
  }
  if (raw.curr_time)
    c.append(
      el("p", "item-meta", `官方资料时间：${raw.curr_time}（香港时间）`),
    );
  return [c];
}
function genericCard(r, title) {
  const c = card(title, r.provider || "查询结果");
  if (isBad(r)) c.append(notice(r.error?.message || "查询未完成。", "warning"));
  else if (Array.isArray(r.data)) c.append(table(r.data));
  else if (r.data?.rows) c.append(table(r.data.rows));
  else textBlock(c, "已取得资料，可在下方展开完整数据。");
  return [c];
}
function sourcesPanel(r) {
  const panel = el("details", "sources-panel");
  panel.append(el("summary", "", "来源与说明"));
  const urls = new Set();
  function visit(x) {
    if (!x || typeof x !== "object") return;
    if (x.source) urls.add(x.source);
    if (Array.isArray(x.sources)) for (const u of x.sources) urls.add(u);
    if (x.data && !Array.isArray(x.data))
      for (const [key, v] of Object.entries(x.data))
        if (v && typeof v === "object" && "ok" in v) visit(v);
  }
  visit(r);
  for (const u of urls) {
    const valid = cleanURL(u);
    if (valid) panel.append(link(new URL(valid).hostname, valid));
  }
  if (r.queried_at) panel.append(el("p", "", `查询时间：${r.queried_at}`));
  if (r.fetched_at)
    panel.append(
      el(
        "p",
        "",
        `下载时间：${r.fetched_at}${r.cached ? " · 使用有效期内缓存" : ""}`,
      ),
    );
  if (r.source_times?.length)
    panel.append(
      el("p", "", `资料时间：${r.source_times.slice(0, 5).join("；")}`),
    );
  for (const note of (r.notes || []).slice(0, 7))
    panel.append(el("p", "", note));
  return panel;
}

function roadRouteCard(r) {
  const c = card("地图路线", "OpenRouteService");
  if (!r.ok) c.append(notice(r.error?.message || "路线暂不可用。", "warning"));
  if (r.ok && r.data) {
    const d = r.data;
    c.append(
      el(
        "h3",
        "",
        `${(d.distance_m / 1000).toFixed(2)} km · ${Math.round(d.duration_s / 60)} min`,
      ),
    );
    c.append(el("p", "", `${d.origin.name} → ${d.destination.name}`));
    if (d.geometry && window.L) {
      const surface = el("div", "route-map");
      surface.setAttribute("aria-label", "Route map");
      c.append(surface);
      requestAnimationFrame(() => {
        if (!surface.isConnected) return;
        const map = L.map(surface, { scrollWheelZoom: false });
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution:
            '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
        const route = L.geoJSON(
          { type: "Feature", geometry: d.geometry, properties: {} },
          { style: { color: "#315e4d", weight: 5 } },
        ).addTo(map);
        map.fitBounds(route.getBounds(), { padding: [20, 20] });
        L.marker([d.origin.latitude, d.origin.longitude])
          .addTo(map)
          .bindTooltip(el("span", "", d.origin.name));
        L.marker([d.destination.latitude, d.destination.longitude])
          .addTo(map)
          .bindTooltip(el("span", "", d.destination.name));
      });
    }
    const directions = el("details", "route-directions");
    directions.append(el("summary", "", "逐步路线"));
    const list = el("ol");
    for (const step of d.steps || [])
      list.append(
        el(
          "li",
          "",
          `${step.instruction || ""} · ${Math.round(step.distance || 0)} m`,
        ),
      );
    directions.append(list);
    c.append(directions);
  }
  if (r.external_url) c.append(link("打开地图导航", r.external_url));
  return [c];
}

function renderResponse(payload) {
  const r = payload.result,
    container = $("#result-content");
  container.replaceChildren();
  state.last = payload;
  $("#export-results").hidden = false;
  $("#results-title").textContent = isBad(r)
    ? "暂时没查到"
    : r.status === "partial"
      ? "已取得部分查询结果"
      : "查询结果";
  $("#result-meta").textContent =
    `${(payload.elapsed_ms / 1000).toFixed(1)} 秒 · ${new Intl.DateTimeFormat(window.uiLanguage?.() === "en" ? "en-HK" : "zh-CN", { timeZone: "Asia/Hong_Kong", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date())}`;
  if (r.status === "partial") {
    const names = {
      attractions: "景点",
      restaurants: "餐厅",
      forecast: "预报",
      current_weather: "当前天气",
      current_warnings: "当前警告",
    };
    container.append(
      notice(
        `部分来源未完成：${(r.failed_sections || []).map((n) => names[n] || n).join("、")}。其他已取得的结果保留如下。`,
        "warning",
      ),
    );
  }
  const grid = el("div", "result-grid");
  if (payload.tool === "search_travel_knowledge") {
    const summary = card(
      "参考指南",
      r.method?.startsWith("hybrid") ? "语义 + 关键词" : "关键词检索",
    );
    if (!r.data?.length)
      summary.append(el("p", "", "没有找到相关资料，请换个问题。"));
    for (const doc of r.data || []) {
      summary.append(
        el("h3", "", doc.name),
        el("p", "source-text", doc.text),
        link(`[${doc.chunk_id}] 来源`, doc.source),
        el("p", "item-meta", doc.source_date || ""),
      );
      if (doc.distance_km != null)
        summary.append(
          el("p", "item-meta", `${doc.distance_km.toFixed(1)} km`),
        );
    }
    grid.append(summary);
  } else if (payload.tool === "get_outing_overview") {
    for (const [key, section] of Object.entries(r.data || {})) {
      const title =
        {
          weather: "天气预报",
          restaurants: "附近美食",
          attractions: "附近景点",
        }[key] || key;
      if (section.text) {
        const c = card(title);
        textBlock(c, section.text);
        grid.append(c);
      } else
        for (const c of key === "restaurants" || key === "attractions"
          ? pagedResults(section, title)
          : genericCard(section, title))
          grid.append(c);
    }
  } else {
    let cards;
    if (payload.tool === "get_route") cards = roadRouteCard(r);
    else if (typeof r.text === "string") {
      const titles = {
        get_weather: "天气查询",
        get_station_weather: "气象站气温",
        get_place_weather: "地点天气参考",
        plan_mtr_route: "港铁路线",
      };
      const c = card(titles[payload.tool] || "查询结果");
      if (isBad(r))
        c.append(notice(r.error?.message || "查询未完成。", "warning"));
      textBlock(c, r.text);
      cards = [c];
    } else if (payload.tool === "get_place_weather") {
      const c = card("地点天气参考", "weather");
      if (r.data?.is_reference) {
        c.append(
          el("h3", "", `${r.data.value} °${r.data.unit || "C"}`),
          el(
            "p",
            "",
            `${r.data.station_name} · 距定位点约 ${r.data.distance_m} 米`,
          ),
          el("p", "", `观测时间：${r.observed_at || "未知"}`),
          notice("附近气象站参考值，不是该地点实测温度。", "info"),
        );
      } else if (Array.isArray(r.data)) {
        c.append(el("p", "", "香港整体预报，非目的地独立预报"));
        for (const row of r.data)
          c.append(
            el("p", "", `${row.forecastDate} · ${row.forecastWeather || ""}`),
          );
      } else
        c.append(
          notice(
            r.error?.message ||
              (r.candidates
                ? `请选择：${r.candidates.join("、")}`
                : "没有可用参考站或该日期预报。"),
            "warning",
          ),
        );
      cards = [c];
    } else if (payload.tool === "plan_mtr_route") cards = routeCard(r);
    else if (payload.tool === "get_mtr_arrivals") cards = mtrCard(r);
    else if (
      ["search_restaurants", "search_licensed_restaurants"].includes(
        payload.tool,
      )
    )
      cards = pagedResults(r, "附近美食");
    else if (payload.tool === "search_attractions")
      cards = pagedResults(r, "附近景点");
    else if (
      payload.tool === "get_weather" ||
      payload.tool === "get_station_weather"
    )
      cards = weatherCard(r, "天气查询");
    else cards = genericCard(r, "查询结果");
    for (const c of cards) grid.append(c);
  }
  container.append(grid, sourcesPanel(r));
  if (r.static_alternatives?.data?.length) {
    const details = el("details", "raw-data");
    details.append(
      el("summary", "", "也可以看看这些去处"),
      el("p", "", r.static_alternatives_scope),
    );
    for (const doc of r.static_alternatives.data)
      details.append(
        link(doc.title, doc.url),
        el("p", "source-text", doc.text),
      );
    container.append(details);
  }
  const raw = el("details", "raw-data");
  raw.append(
    el("summary", "", "详细资料"),
    el("pre", "", JSON.stringify(payload, null, 2)),
  );
  container.append(raw);
}
$("#query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  let body;
  try {
    body = requestForForm();
  } catch (e) {
    showToast(e.message);
    return;
  }
  if (state.controller) state.controller.abort();
  const controller = new AbortController(),
    request = ++state.request;
  state.controller = controller;
  $("#query-button").disabled = true;
  $("#query-progress").hidden = false;
  $("#progress-label").textContent =
    state.view === "attractions"
      ? "正在查找附近景点，可能需要一点时间…"
      : "正在查询，请稍候…";
  try {
    const payload = await api("/api/query", body, controller.signal);
    if (request === state.request) renderResponse(payload);
  } catch (e) {
    if (e.name !== "AbortError" && request === state.request) {
      $("#result-content").replaceChildren(notice(e.message, "error"));
      $("#results-title").textContent = "查询暂时未完成";
      $("#export-results").hidden = true;
      state.last = null;
    }
  } finally {
    if (request === state.request) {
      $("#query-button").disabled = false;
      $("#query-progress").hidden = true;
      state.controller = null;
    }
  }
});
$("#cancel-query").addEventListener("click", () => {
  state.controller?.abort();
  showToast("已取消等待显示；后端只读查询会自行结束。");
});
$$(".nav-item").forEach((b) =>
  b.addEventListener("click", () => setView(b.dataset.view)),
);
$$("#transport-modes button").forEach((b) =>
  b.addEventListener("click", () => {
    state.controller?.abort();
    state.request++;
    state.controller = null;
    $("#query-progress").hidden = true;
    $("#query-button").disabled = false;
    state.transport = b.dataset.transport;
    buildForm();
    resetResults();
  }),
);
document.addEventListener("click", (event) => {
  const shortcut = event.target.closest("[data-shortcut]");
  if (shortcut) setView(shortcut.dataset.shortcut);
  const suggestion = event.target.closest("[data-prompt]");
  if (suggestion) {
    $("#chat-input").value = suggestion.dataset.prompt;
    $("#chat-input").focus();
  }
});
$("#refresh-status").addEventListener("click", refreshStatus);
$("#export-results").addEventListener("click", () => {
  if (!state.last) return;
  const blob = new Blob([JSON.stringify(state.last, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob),
    a = el("a");
  a.href = url;
  a.download = `港行-${state.last.tool}-${hkDay()}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

const taskNames = {
  weather: "天气",
  food: "餐厅",
  attractions: "景点",
  transport: "交通",
};
const preferenceNames = {
  indoor: "室内活动",
  children: "亲子出行",
  accessibility: "少走路／无障碍设施",
};
function appendPlan(root, plan) {
  const chips = el("div", "plan-chips");
  for (const place of plan.locations || [])
    chips.append(el("span", "plan-chip", place.name));
  if (plan.date) chips.append(el("span", "plan-chip", plan.date));
  for (const key of plan.intents || [])
    chips.append(el("span", "plan-chip", taskNames[key] || key));
  for (const key of plan.preferences || [])
    chips.append(el("span", "plan-chip", preferenceNames[key] || key));
  root.append(chips);
  for (const question of plan.clarifications || [])
    root.append(el("p", "", question));
  if (!chips.children.length && !plan.clarifications?.length)
    root.append(el("p", "", "加上目的地和日期，我再帮你整理。"));
}

function thoughtBlock(thought) {
  const details = el("details", "thought");
  const summary = el("summary", "", `思考 ${thought.seconds || 1}秒`);
  details.append(summary);
  const lines = el("div", "thought-lines");
  for (const line of thought.lines || []) lines.append(el("p", "", line));
  details.append(lines);
  return details;
}
function liveThought() {
  const details = el("details", "thought");
  details.open = true;
  const summary = el("summary", "", "正在查询");
  details.classList.add("is-working");
  const lines = el("div", "thought-lines");
  details.append(summary, lines);
  const rows = new Map();
  return {
    element: details,
    step(event) {
      let row = rows.get(event.id);
      if (!row) {
        row = el("p", "", event.text || "");
        rows.set(event.id, row);
        lines.append(row);
      } else if (event.text) {
        row.textContent = event.text;
      }
      row.classList.toggle("thought-active", event.state === "active");
      details.open = true;
    },
    finish(seconds) {
      summary.textContent = seconds ? `已完成 · ${seconds}秒` : "查询已结束";
      details.classList.remove("is-working");
      for (const row of rows.values()) row.classList.remove("thought-active");
    },
  };
}
async function streamChat(body, onStep) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error?.message || "请求未完成，请重试。");
    }
    return data;
  }
  if (!response.ok || !response.body) {
    throw new Error("请求未完成，请重试。");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalEvent = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      newline = buffer.indexOf("\n");
      if (!line) continue;
      const event = JSON.parse(line);
      if (["step", "token", "clear_tokens", "evidence"].includes(event.type))
        onStep(event);
      else if (event.type === "done" || event.type === "error")
        finalEvent = event;
    }
  }
  buffer += decoder.decode();
  if (buffer.trim()) {
    const event = JSON.parse(buffer);
    if (event.type === "done" || event.type === "error") finalEvent = event;
    else if (event.type !== "heartbeat") onStep(event);
  }
  if (!finalEvent) throw new Error("这次回答未完成，请重新发送。");
  if (finalEvent.type === "error") throw new Error(finalEvent.message);
  return finalEvent;
}
function addMessage(
  role,
  text,
  trace,
  retrieval,
  understanding,
  original = false,
  thought = null,
) {
  const item = el("div", `chat-message ${role}`);
  const avatar = el("span", "chat-avatar", role === "user" ? "你" : "港");
  const body = el("div");
  if (role === "assistant" && thought?.lines?.length)
    body.append(thoughtBlock(thought));
  body.append(
    el(
      "strong",
      "",
      role === "user" ? "你" : role === "error" ? "查询未完成" : "港行助手",
    ),
    el("p", original ? "source-text" : "", text),
  );
  if (trace?.length) {
    const details = el("details", "trace-list");
    details.append(el("summary", "", "查询记录"));
    const list = el("ul");
    const labels = {
      get_place_weather: "目的地天气",
      get_weather: "天气",
      get_station_weather: "气象站观测",
      search_restaurants: "附近美食",
      search_licensed_restaurants: "持牌餐厅",
      search_attractions: "附近景点",
      geocode_hk: "地点定位",
      plan_mtr_route: "港铁路线",
      get_route: "步行路线",
      get_mtr_route: "港铁路线",
      get_nearby_food: "附近美食",
      get_weather_info: "天气",
      get_nearest_temperature: "附近气温",
      get_mtr_arrivals: "列车到站",
      search_travel_knowledge: "出行指南",
    };
    for (const t of trace)
      list.append(
        el(
          "li",
          "",
          `${labels[t.tool] || "资料查询"} · ${t.status === "ok" ? "已完成" : "暂未完成"}`,
        ),
      );
    details.append(list);
    body.append(details);
  }
  if (understanding) {
    const details = el("details", "trace-list");
    details.append(el("summary", "", "本次出行条件"));
    appendPlan(details, understanding);
    body.append(details);
  }
  if (retrieval) {
    const details = el("details", "trace-list");
    details.append(el("summary", "", `相关参考 · ${retrieval.data.length} 篇`));
    for (const doc of retrieval.data) {
      details.append(
        link(doc.title, doc.url),
        el("p", "", `资料更新：${doc.verified_at}`),
        el("p", "source-text", doc.text),
      );
    }
    if (!retrieval.data.length)
      details.append(el("p", "", "暂时没有找到相关参考资料。"));
    body.append(details);
  }
  item.append(avatar, body);
  $("#chat-messages").append(item);
  item.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return item;
}
$("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#chat-input"),
    message = input.value.trim();
  if (!message || state.chatBusy) return;
  if (!state.chatAvailable) {
    showToast("出行助手暂时不可用，可以先使用天气、餐厅和地铁查询。");
    return;
  }
  state.chatBusy = true;
  $("#chat-send").disabled = true;
  input.value = "";
  addMessage("user", message);
  const item = el("div", "chat-message assistant");
  const body = el("div");
  const live = liveThought();
  const answer = el("p", "source-text", "");
  answer.hidden = true;
  body.append(live.element, el("strong", "", "港行助手"), answer);
  item.append(el("span", "chat-avatar", "港"), body);
  $("#chat-messages").append(item);
  item.scrollIntoView({ behavior: "smooth", block: "nearest" });
  try {
    const data = await streamChat(
      {
        session_id: sessionId,
        message,
        language: window.uiLanguage?.() || "zh",
      },
      (event) => {
        if (event.type === "token") {
          answer.hidden = false;
          answer.textContent += event.text;
          return;
        }
        if (event.type === "clear_tokens") {
          answer.textContent = "";
          answer.hidden = true;
          return;
        }
        if (event.type === "evidence") {
          item._evidence = event.retrieval;
          return;
        }
        live.step(event);
        item.scrollIntoView({ behavior: "smooth", block: "nearest" });
      },
    );
    live.finish(data.seconds);
    answer.hidden = false;
    answer.textContent = data.message || "";
    const evidence = item._evidence;
    if (evidence?.data?.length || evidence?.nearby?.length) {
      const refs = el("details", "trace-list");
      refs.append(el("summary", "", "参考资料"));
      for (const doc of evidence.data || [])
        refs.append(
          link(`${doc.name} [${doc.chunk_id}]`, doc.source),
          el("p", "", doc.source_date || ""),
        );
      if (evidence.nearby?.length) {
        refs.append(el("p", "", "按距离选出的附近景点"));
        for (const doc of evidence.nearby)
          refs.append(
            link(
              `${doc.name} [${doc.chunk_id}] 约 ${Number(doc.distance_km).toFixed(1)} 公里`,
              doc.source,
            ),
          );
      }
      body.append(refs);
    }
  } catch (e) {
    live.finish();
    item.classList.add("error");
    answer.hidden = false;
    answer.textContent = e.message;
  } finally {
    state.chatBusy = false;
    $("#chat-send").disabled = !state.chatAvailable;
  }
});
$("#chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $("#chat-form").requestSubmit();
  }
});
$("#reset-chat").addEventListener("click", async () => {
  if (state.chatBusy) {
    showToast("回答处理中，请稍后清空。");
    return;
  }
  try {
    await api("/api/chat/reset", { session_id: sessionId });
    $("#chat-messages").replaceChildren();
    addMessage("assistant", "会话已清空。下一站想去哪里？");
  } catch (e) {
    showToast(e.message);
  }
});
buildForm();
refreshStatus();

document.addEventListener("languagechange", () => {
  clock();
  const language = $("#f-language");
  if (language) language.value = window.uiLanguage() === "en" ? "en" : "sc";
});
