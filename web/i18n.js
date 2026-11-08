"use strict";
// Interface-only translations. Original source documents and conversation text stay intact.
(() => {
  const entries = `
出行概览|Overview
交通与路线|Transport & routes
查看出行概览|View overview
只查询你选择的内容，各来源同时查询。|Only selected sources are queried, in parallel.
步行／驾车|Walking / driving
出发地点|From
目的地点|To
出行方式|Travel mode
步行|Walking
驾车|Driving
骑行|Cycling
徒步|Hiking
路线由 OpenRouteService 规划，地图来自 OpenStreetMap。|Routes by OpenRouteService, maps by OpenStreetMap.
地图路线|Map route
逐步路线|Step-by-step directions
打开地图导航|Open directions
请输入起点和终点。|Please enter an origin and destination.
正在查询|Checking information
正在整理查询需求|Understanding your request
正在检索参考资料|Finding reference material
正在检索目的地资料|Finding destination references
目的地资料检索完成|Destination references ready
正在整理回答|Preparing your answer
正在查找附近美食|Finding nearby food
正在规划路线|Planning your route
正在查询港铁换乘|Checking MTR transfers
正在查询列车到站|Checking train arrivals
正在检索出行指南|Searching local guides
正在查询天气资料|Checking weather information
查询已结束|Search finished
参考资料|References
出行指南|Local guides
先了解，再出发|Know before you go
参考资料附有来源与日期，不代表实时营业或价格。|References include sources and dates, not live opening hours or prices.
想了解什么|What would you like to know?
查找指南|Find a guide
参考指南|Reference guides
语义 + 关键词|Semantic + keyword
关键词检索|Keyword search
没有找到相关资料，请换个问题。|No relevant references found. Please try another question.

天气与预报|Weather
出门前，看看天|Before you head out
查询天气|Check weather
香港天文台资料，观测时间随结果显示。|Hong Kong Observatory data, with observation times shown.
附近美食|Nearby food
附近有什么好吃的|What's nearby to eat?
寻找餐厅|Find restaurants
按直线距离查看附近持牌餐厅，营业安排请向店家确认。|Browse licensed restaurants by straight-line distance. Check opening arrangements with the venue.
景点探索|Things to do
找个值得去的地方|Find your next stop
发现景点|Explore nearby
发现附近景点。出发前请确认开放时间。|Explore nearby sights. Check opening hours before visiting.
地铁查询|MTR
下一站，怎么走|Find your way there
查询地铁|Check the MTR
港铁路线和列车到站。|MTR routes and train arrivals.
出行助手|Travel assistant
港行 · 香港天气与出行助手|Harbour Days · Hong Kong travel companion
港行 · 香港天气与出行|Harbour Days · Hong Kong
港行首页|Harbour Days home
港行|Harbour Days
港|HK
探索这座城市|Explore Hong Kong
主要功能|Main navigation
香港，慢慢逛。|Take your time here.
天气 · 街角小店 · 下一站|Weather · Local finds · Your next stop
正在连接服务|Connecting…
本地数据查询|Hong Kong travel guide
香港天气与出行|Hong Kong travel guide
重新检查服务|Reconnect
我的香港|My Hong Kong
香港时间|Hong Kong time
今天的香港，|Hong Kong today.
想去哪一站？|Where to next?
查查天气，找家餐厅，看看怎么去。|Check the sky, find a table, plan your way there.
天气|Weather
美食|Food
景点|Sights
地铁|MTR
维港两岸，街巷之间。|Across the harbour. Around the corner.
今天，想去哪里？|Where are you heading?
港铁路线|MTR route
列车到站|Train arrivals
正在向数据来源查询，请稍候…|Checking the latest information…
取消显示|Stop waiting
从这里开始|Start exploring
上一页|Previous
下一页|Next
出门前，看看天|Before you head out
当前气温、未来预报与天气提醒。|Current conditions, forecasts and weather alerts.
查看天气|Check the weather
看看附近美食的地址和距离。|Find nearby food, addresses and distances.
下一站，怎么走|Find your way there
查港铁换乘，看看还有多久到站。|Plan MTR transfers and check upcoming arrivals.
查询地铁|Check the MTR
输入目的地，看看附近有什么。|Enter a destination to explore the neighbourhood.
下一站，一起想想。|Let's plan your next stop.
新对话|New chat
正在连接…|Connecting…
港行助手|Travel companion
想去哪儿？告诉我时间、地点和同行的人，一起看看天气、吃什么、怎么走。|Where would you like to go? Tell me when, where and who you’re going with. We can check the weather, find somewhere to eat and plan the journey.
尖沙咀的一日出行|A day in Tsim Sha Tsui
明天去西贡|Sai Kung tomorrow
输入你的问题|Your message
例如：今天从沙田去尖沙咀，有什么餐厅，港铁怎么坐？|For example: I'm going from Sha Tin to Tsim Sha Tsui today. Where can I eat, and which MTR route should I take?
Enter 发送 · Shift + Enter 换行|Enter to send · Shift + Enter for a new line
发送|Send
出行指南|Local guides
天气与港铁以最新发布资料为准。|Refer to the latest weather and MTR updates.
500 米|500 m
1 公里|1 km
2 公里|2 km
3 公里|3 km
该站全部线路|Every line at this station
荃湾线 · TWL|Tsuen Wan Line · TWL
东铁线 · EAL|East Rail Line · EAL
屯马线 · TML|Tuen Ma Line · TML
观塘线 · KTL|Kwun Tong Line · KTL
港岛线 · ISL|Island Line · ISL
将军澳线 · TKL|Tseung Kwan O Line · TKL
东涌线 · TCL|Tung Chung Line · TCL
南港岛线 · SIL|South Island Line · SIL
迪士尼线 · DRL|Disneyland Resort Line · DRL
机场快线 · AEL|Airport Express · AEL
目的地|Destination
输入香港地名，例如尖沙咀、沙田|Enter a Hong Kong place, e.g. Tsim Sha Tsui
出行日期|Visit date
想吃什么|What would you like to eat?
全部饮食|All food
餐厅|Restaurants
咖啡店|Cafés
快餐|Fast food
美食广场|Food courts
酒吧|Bars
酒馆|Pubs
冰淇淋店|Ice cream
啤酒花园|Beer gardens
想探索什么|What would you like to explore?
所有景点|All sights
博物馆|Museums
画廊|Galleries
观景点|Viewpoints
主题乐园|Theme parks
动物园|Zoos
附近范围|Search radius
官方持牌食肆 · 按距离排序|Licensed restaurants · Sorted by distance
天气资料|Weather information
当前天气报告|Current conditions
本港天气预报|Local forecast
九天预报|Nine-day forecast
正在生效的警告|Warnings in force
警告详情|Warning details
特别天气提示|Special weather tips
当前气温|Current temperature
当前湿度|Current humidity
当前风向风速|Current wind
暑热指数|Heat index
全港紫外线|Territory UV index
能见度|Visibility
地点（可选）|Place (optional)
留空列出各站，例如黄埔则查最近的站|Leave blank for all stations, or enter a place such as Whampoa
全港报告和紫外线不用填地点。分区资料留空列出各站，填写地名则查最近的站。|Territory reports and UV need no place. Leave station data blank to list every station, or enter a place for the nearest one.
资料语言|Source language
简体中文|Simplified Chinese
繁體中文|Traditional Chinese
实际观测与预报时间随资料显示|Observation and forecast times are shown with the data
出发站|From station
目的站|To station
机场快线|Airport Express
不使用机场快线|Exclude Airport Express
允许使用机场快线|Include Airport Express
先最少线路换乘，再最少站间路段|Fewest line changes, then fewest station-to-station legs
港铁车站|MTR station
所属线路|MTR line
保留月台、终点、预计到站及延误信息|Platform, destination, expected arrival and delay information
服务正常|Connected
暂时无法连接|Unable to connect
请稍后刷新重试|Please refresh and try again
出行助手暂时不可用，可以先查询天气、餐厅和地铁。|The assistant is unavailable. You can still check weather, food and the MTR.
连接暂时中断，请稍后重试。|Connection interrupted. Please try again shortly.
服务暂时没有响应，请稍后重试。|The service is not responding. Please try again.
出行助手暂时不可用，请先使用其他查询。|The assistant is unavailable. Please use the other searches.
出行助手暂时没有响应，请稍后再试。|The assistant is not responding. Please try again later.
这次回答未完成，请重新发送。|The reply could not be completed. Please send again.
请求未完成，请重试。|The request could not be completed. Please try again.
请先输入目的地。|Please enter a destination.
请输入小区或地标，例如黄埔。|Please enter a neighbourhood or landmark, such as Whampoa.
分区气温只适用于“当前天气”，其他资料请清空分区字段。|Station temperature is only available for current conditions. Clear the station field for other reports.
请输入出发站和目的站。|Please enter the origin and destination stations.
请输入港铁车站。|Please enter an MTR station.
请选择港铁路线或列车到站。|Choose an MTR route or train arrivals.
未提供|Not provided
香港天文台|Hong Kong Observatory
此项查询未完成。|This search could not be completed.
未找到对应日期的预报。|No forecast was found for that date.
观测站|Observation station
相对湿度|Relative humidity
当前未返回天气警告或提示。|No weather warnings or tips were returned.
官方牌照|Official licence
社区地图|Community map
地点资料|Place information
资料暂时不可用。|Information is temporarily unavailable.
本次查询没有匹配结果；不代表当地没有相关地点。|No matching records were found. This does not mean there are no places in the area.
未提供名称|Unnamed place
在地图查看|View on map
OSM 记录|OSM record
按直线距离排序 · 非评分榜单 · 实时营业状态未知|Straight-line distance · Not a rating · Live opening status unknown
© OpenStreetMap contributors · 资料可能不完整|© OpenStreetMap contributors · Coverage may be incomplete
没有匹配记录。|No matching records.
页面展示前50条，完整记录可展开或导出。|Showing the first 50 records. Expand or save results for the full data.
此项未完成。|This search could not be completed.
官方接口没有返回匹配记录。|No matching records were returned by the provider.
换乘方案|Route plan
无法规划路线。|Unable to plan this route.
这一路段可能需要同线换车，不应理解为一班直达。|A same-line train change may be required on this segment.
按最少线路换乘、再最少站间路段选择。不含不同站码的步行连接、实时停运、票价及耗时保证。|Routes minimise line changes, then station-to-station legs. Walking links, live closures, fares and journey times are not included.
港铁列车到站|MTR train arrivals
港铁官方|MTR official data
暂无可用列车资料。|No train information is available.
官方资料显示延误，请结合原始信息确认。|The operator reports a delay. Check the service details.
行驶方向 / 终点|Direction / destination
月台|Platform
预计分钟|Minutes
预计到站时间|Expected arrival
有效性|Status
已提供|Provided
待确认|Unconfirmed
查询结果|Results
查询未完成。|The search could not be completed.
已取得资料，可在下方展开完整数据。|Information is available. Expand the details below to view it.
附近持牌餐厅|Nearby licensed restaurants
附近景点|Nearby sights
天气预报|Forecast
当前天气观测|Current observations
当前警告资料|Current warnings
来源与说明|Sources and notes
暂时没查到|No results available
已取得部分查询结果|Some results are available
餐厅|Restaurants
预报|Forecast
当前天气|Current weather
当前警告|Current warnings
地点天气参考|Local weather reference
附近气象站参考值，不是该地点实测温度。|Reference from a nearby station, not a measurement at this location.
香港整体预报，非目的地独立预报|Hong Kong-wide forecast, not a location-specific forecast
没有可用参考站或该日期预报。|No reference station or forecast is available for this date.
天气查询|Weather results
也可以看看这些去处|Other ideas to explore
详细资料|Full details
正在并行查询多个来源，单项最多等待20秒…|Checking multiple sources. Each source may take up to 20 seconds…
正在查找附近景点，可能需要一点时间…|Finding nearby sights. This may take a moment…
正在查询，请稍候…|Searching…
查询暂时未完成|Search not completed
已取消等待显示；后端只读查询会自行结束。|Stopped waiting. The search will finish in the background.
站点已填入，请确认路线与方向后查询。|Stop selected. Check the route and direction before searching.
室内活动|Indoor activities
亲子出行|Family outing
少走路／无障碍设施|Less walking / accessible facilities
加上目的地和日期，我再帮你整理。|Add a destination and date to organise your plans.
你|You
查询未完成|Search not completed
查询记录|Search history
目的地天气|Destination weather
气象站观测|Station observations
持牌餐厅|Licensed restaurants
地点定位|Place lookup
资料查询|Information lookup
已完成|Completed
暂未完成|Not completed
本次出行条件|Your trip preferences
暂时没有找到相关参考资料。|No relevant reference material was found.
出行助手暂时不可用，可以先使用天气、餐厅和地铁查询。|The assistant is unavailable. Weather, food and MTR searches are still available.
正在帮你查找…|Looking that up for you…
回答处理中，请稍后清空。|A reply is in progress. Please wait before clearing the chat.
会话已清空。下一站想去哪里？|New conversation. Where would you like to go next?
正在检索…|Searching…
检索失败|Search failed
暂时没有找到相关指南，试试换个关键词。|No guide found. Try a different keyword.
官方来源|Official source
正在整理…|Organising…
`;
  const dictionary = Object.fromEntries(
    entries
      .trim()
      .split("\n")
      .map((line) => {
        const i = line.indexOf("|");
        return [line.slice(0, i), line.slice(i + 1)];
      }),
  );
  let language = "zh";
  try {
    language = localStorage.getItem("hk-language") === "en" ? "en" : "zh";
  } catch {}
  const texts = new WeakMap(),
    attributes = new WeakMap();
  const patterns = [
    [/^已完成 · (\d+)秒$/, (m) => `Completed · ${m[1]} s`],
    [/^官方更新时间：(.*)$/s, (m) => `Official update: ${m[1]}`],
    [/^展望：(.*)$/s, (m) => `Outlook: ${m[1]}`],
    [/^(\d+) 米$/, (m) => `${m[1]} m`],
    [
      /^牌照：(.*) · 到期日：(.*)$/s,
      (m) => `Licence: ${m[1]} · Expiry: ${m[2]}`,
    ],
    [
      /^登记营业时间：(.*)（未经实时确认）$/s,
      (m) => `Listed hours: ${m[1]} (not verified live)`,
    ],
    [/^菜系标签：(.*)$/s, (m) => `Cuisine tag: ${m[1]}`],
    [/^预计到站：(.*)$/s, (m) => `Expected arrival: ${m[1]}`],
    [/^第 (\d+) 站$/, (m) => `Stop ${m[1]}`],
    [/^(\d+) 次线路换乘$/, (m) => `${m[1]} line changes`],
    [/^(\d+) 个站间路段$/, (m) => `${m[1]} station-to-station legs`],
    [
      /^官方资料时间：(.*)（香港时间）$/s,
      (m) => `Provider time: ${m[1]} (Hong Kong)`,
    ],
    [/^查询时间：(.*)$/s, (m) => `Search time: ${m[1]}`],
    [
      /^下载时间：(.*)$/s,
      (m) => `Retrieved: ${m[1].replace(" · 使用有效期内缓存", " · cached")}`,
    ],
    [/^资料时间：(.*)$/s, (m) => `Source timestamps: ${m[1]}`],
    [/^(\S+) 秒 · (.*)$/s, (m) => `${m[1]} s · ${m[2]}`],
    [/^思考 (\d+)秒$/, (m) => `Thought ${m[1]}s`],
    [/^思考中$/, () => "Thinking"],
    [
      /^部分来源未完成：(.*)。其他已取得的结果保留如下。$/s,
      (m) =>
        `Some sources are unavailable: ${m[1]
          .split("、")
          .map((x) => dictionary[x] || x)
          .join(", ")}. Available results are shown below.`,
    ],
    [
      /^(.*) · 距定位点约 (\d+) 米$/,
      (m) =>
        `${dictionary[m[1]] || m[1]} · approximately ${m[2]} m from the selected location`,
    ],
    [/^观测时间：(.*)$/s, (m) => `Observed: ${m[1]}`],
    [/^请选择：(.*)$/s, (m) => `Please choose: ${m[1]}`],
    [/^相关参考 · (\d+) 篇$/, (m) => `Related references · ${m[1]}`],
    [/^资料更新：(.*)$/s, (m) => `Reference checked: ${m[1]}`],
    [
      /^(.*) · (已完成|暂未完成)$/,
      (m) => `${dictionary[m[1]] || m[1]} · ${dictionary[m[2]]}`,
    ],
  ];
  function translate(value) {
    if (language !== "en") return value;
    const key = value.trim();
    let result = dictionary[key];
    if (result === undefined)
      for (const [regex, fn] of patterns) {
        const match = key.match(regex);
        if (match) {
          result = fn(match);
          break;
        }
      }
    return result === undefined ? value : value.replace(key, result);
  }
  function apply(root = document.body) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (
        node.parentElement?.closest(
          "script,style,pre,.source-text,.chat-message.user,[data-original-content]",
        )
      )
        continue;
      let record = texts.get(node);
      if (!record || node.data !== record.rendered)
        record = { source: node.data, rendered: node.data };
      const next = translate(record.source);
      record.rendered = next;
      texts.set(node, record);
      if (node.data !== next) node.data = next;
    }
    for (const element of root.querySelectorAll(
      "[placeholder],[title],[aria-label]",
    )) {
      let records = attributes.get(element) || {};
      for (const name of ["placeholder", "title", "aria-label"]) {
        if (!element.hasAttribute(name)) continue;
        const value = element.getAttribute(name);
        let record = records[name];
        if (!record || value !== record.rendered)
          record = { source: value, rendered: value };
        record.rendered = translate(record.source);
        records[name] = record;
        if (value !== record.rendered)
          element.setAttribute(name, record.rendered);
      }
      attributes.set(element, records);
    }
    document.documentElement.lang = language === "en" ? "en" : "zh-CN";
    const title =
      language === "en"
        ? "Harbour Days · Hong Kong travel companion"
        : "港行 · 香港天气与出行助手";
    if (document.title !== title) document.title = title;
  }
  window.uiLanguage = () => language;
  window.uiText = translate;
  function choose(next) {
    language = next === "en" ? "en" : "zh";
    try {
      localStorage.setItem("hk-language", language);
    } catch {}
    for (const b of document.querySelectorAll("[data-language]"))
      b.setAttribute("aria-pressed", String(b.dataset.language === language));
    apply();
    document.dispatchEvent(
      new CustomEvent("languagechange", { detail: language }),
    );
  }
  document.addEventListener("DOMContentLoaded", () => {
    document
      .querySelectorAll("[data-language]")
      .forEach((b) =>
        b.addEventListener("click", () => choose(b.dataset.language)),
      );
    choose(language);
    let queued = false;
    let active = true;
    const observer = new MutationObserver(() => {
      if (!queued) {
        queued = true;
        queueMicrotask(() => {
          queued = false;
          if (active) apply();
        });
      }
    });
    const options = {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label"],
    };
    observer.observe(document.body, options);
    window.addEventListener("pagehide", () => {
      active = false;
      observer.disconnect();
    });
    window.addEventListener("pageshow", () => {
      active = true;
      observer.observe(document.body, options);
      apply();
    });
  });
})();
