"use strict";

const MARKETS = {
  new: "新建商品住宅",
  resale: "二手住宅",
};

const AREAS = {
  all: "综合",
  below90: "90㎡以下",
  between90And144: "90–144㎡",
  above144: "144㎡以上",
};

const BASES = {
  yoy: {
    label: "同比",
    comparison: "上年同月",
  },
  mom: {
    label: "环比",
    comparison: "上月",
  },
  fixed: {
    label: "定基/累计",
    comparison: "对应基准",
  },
};

const DEFAULT_CITY_ADCODE = "110100";

// canvas 无法读 CSS 变量，这里的取值须与 styles.css 的调色板保持一致。
const CHART_COLORS = {
  line: "#0f6e63",
  surface: "#ffffff",
  grid: "#eef1f0",
  benchmark: "#b3bdbc",
  divider: "rgba(18, 24, 28, 0.28)",
  axis: "#8a969a",
  axisStrong: "#5c6b70",
};
const CHART_FONT = '"SF Mono", ui-monospace, Menlo, Consolas, monospace';
const NICE_STEPS = [0.2, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50];

// 定基/累计口径的分段边界。基期约每五年轮换一次，2023 年起改为年内累计同比、
// 每年 1 月重置，因此这些边界两侧的数值不可直接连成一条序列。
const FIXED_BASE_SEGMENTS = [
  { start: "2011-01", end: "2015-12", label: "2010年=100" },
  { start: "2016-01", end: "2020-12", label: "2015年=100" },
  { start: "2021-01", end: "2022-12", label: "2020年=100" },
];
const CUMULATIVE_BASIS_START = "2023-01";

const state = {
  data: null,
  series: new Map(),
  city: DEFAULT_CITY_ADCODE,
  market: "new",
  area: "all",
  basis: "yoy",
  range: 60,
  search: "",
};

const elements = {};
let chartModel = null;
let resizeFrame = null;
let activeCityOptionIndex = -1;
let buildVersion = "dev";
let pendingCityToken = 0;

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  try {
    cacheElements();
    bindEvents();
    buildVersion = document.documentElement.dataset.buildVersion || "dev";

    state.data = await fetchJson("./data/index.json");
    validateData(state.data);
    applyUrlState();
    // 首屏只需骨架加当前城市一片，其余 69 城按需加载。
    await loadCitySeries(state.city);
    initializeCityPicker();
    elements.dashboard.hidden = false;
    renderAll();
    elements.status.hidden = true;
  } catch (error) {
    const status = elements.status || document.getElementById("page-status");
    if (status) {
      status.textContent = `暂时无法加载数据：${error.message}`;
      status.classList.add("error");
    }
  }
}

async function fetchJson(path) {
  const response = await fetch(`${path}?v=${encodeURIComponent(buildVersion)}`);
  if (!response.ok) {
    throw new Error(`数据请求失败 (${response.status})`);
  }
  return response.json();
}

async function loadCitySeries(adcode) {
  const cached = state.series.get(adcode);
  if (cached) return cached;

  const series = await fetchJson(`./data/series/${adcode}.json`);
  state.series.set(adcode, series);
  return series;
}

function cacheElements() {
  const ids = [
    "area-control",
    "basis-control",
    "chart-city",
    "chart-note",
    "chart-tooltip",
    "city-coverage",
    "city-input",
    "city-options",
    "city-search",
    "city-toggle",
    "dashboard",
    "data-through",
    "falling-bar",
    "falling-count",
    "flat-bar",
    "flat-count",
    "hero-month",
    "history-city",
    "history-grid",
    "latest-explanation",
    "latest-month",
    "latest-status",
    "latest-value",
    "legend-label",
    "market-caption",
    "market-control",
    "month-coverage",
    "page-status",
    "point-change",
    "range-select",
    "ranking-body",
    "ranking-empty",
    "rising-bar",
    "rising-count",
    "snapshot-basis",
    "snapshot-city",
    "snapshot-grid",
    "snapshot-month",
    "trend-chart",
    "year-range",
  ];

  ids.forEach((id) => {
    const key = id.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    elements[key] = document.getElementById(id);
  });
  const missingIds = ids.filter((id) => !document.getElementById(id));
  if (missingIds.length) {
    throw new Error("页面资源版本不一致，请刷新页面");
  }
  elements.status = elements.pageStatus;
  elements.dashboard = document.getElementById("dashboard");
}

function bindEvents() {
  elements.cityInput.addEventListener("focus", (event) => {
    event.target.select();
    renderCityOptions("");
  });

  elements.cityInput.addEventListener("input", (event) => {
    renderCityOptions(event.target.value);
  });

  elements.cityInput.addEventListener("change", () => {
    const exactCity = findCityByQuery(elements.cityInput.value);
    if (exactCity) {
      selectCity(exactCity.adcode);
    } else {
      elements.cityInput.value = getSelectedCity().name;
    }
  });

  elements.cityInput.addEventListener("keydown", handleCityInputKeydown);
  elements.cityToggle.addEventListener("click", () => {
    if (elements.cityOptions.hidden) {
      elements.cityInput.focus();
    } else {
      closeCityOptions();
    }
  });
  elements.cityOptions.addEventListener("click", (event) => {
    const option = event.target.closest("[data-adcode]");
    if (option) selectCity(option.dataset.adcode);
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".city-picker")) closeCityOptions();
  });

  elements.marketControl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    state.market = button.dataset.value;
    setActiveButton(elements.marketControl, state.market);
    renderAllViews();
    syncUrl();
  });

  elements.areaControl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    state.area = button.dataset.value;
    setActiveButton(elements.areaControl, state.area);
    renderAllViews();
    syncUrl();
  });

  elements.basisControl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    state.basis = button.dataset.value;
    setActiveButton(elements.basisControl, state.basis);
    renderAllViews();
    syncUrl();
  });

  elements.snapshotGrid.addEventListener("click", (event) => {
    const card = event.target.closest("[data-market][data-area]");
    if (!card) return;
    state.market = card.dataset.market;
    state.area = card.dataset.area;
    setActiveButton(elements.marketControl, state.market);
    setActiveButton(elements.areaControl, state.area);
    renderAllViews();
    syncUrl();
    document.querySelector(".overview-grid").scrollIntoView({ behavior: "smooth" });
  });

  elements.rangeSelect.addEventListener("change", (event) => {
    state.range = event.target.value === "all" ? "all" : Number(event.target.value);
    renderChart();
    syncUrl();
  });

  elements.citySearch.addEventListener("input", (event) => {
    state.search = event.target.value.trim();
    renderRanking();
  });

  elements.rankingBody.addEventListener("click", selectRankingCity);
  elements.rankingBody.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectRankingCity(event);
    }
  });

  elements.trendChart.addEventListener("mousemove", showChartTooltip);
  elements.trendChart.addEventListener("mouseleave", hideChartTooltip);
  elements.trendChart.addEventListener("touchstart", showChartTooltip, { passive: true });
  window.addEventListener("resize", scheduleChartRender);
}

function validateData(data) {
  if (
    data.schemaVersion !== 3 ||
    !Array.isArray(data.dates) ||
    !Array.isArray(data.cities) ||
    typeof data.latest !== "object"
  ) {
    throw new Error("网页数据格式不受支持");
  }
}

function applyUrlState() {
  const params = new URLSearchParams(window.location.search);
  const city = params.get("city");
  const market = params.get("market") || params.get("metric");
  const area = params.get("area");
  const basis = params.get("basis");
  const range = params.get("range");

  if (city && state.data.latest[city]) state.city = city;
  if (market && MARKETS[market]) state.market = market;
  if (area && AREAS[area]) state.area = area;
  if (basis && BASES[basis]) state.basis = basis;
  if (range === "all") state.range = "all";
  if (["36", "60", "120"].includes(range)) state.range = Number(range);

  setActiveButton(elements.marketControl, state.market);
  setActiveButton(elements.areaControl, state.area);
  setActiveButton(elements.basisControl, state.basis);
  elements.rangeSelect.value = String(state.range);
}

function initializeCityPicker() {
  elements.cityInput.value = getSelectedCity().name;
  renderCityOptions("");
  closeCityOptions();
}

function renderCityOptions(query) {
  const normalizedQuery = query.trim().toLowerCase();
  const fragment = document.createDocumentFragment();
  const cities = state.data.cities.filter((city) => {
    return (
      city.name.toLowerCase().includes(normalizedQuery) ||
      city.adcode.includes(normalizedQuery)
    );
  });

  cities.forEach((city) => {
    const option = document.createElement("button");
    option.type = "button";
    option.tabIndex = -1;
    option.id = `city-option-${city.adcode}`;
    option.className = "city-option";
    option.dataset.adcode = city.adcode;
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(city.adcode === state.city));

    const name = document.createElement("span");
    name.textContent = city.name;
    const adcode = document.createElement("small");
    adcode.textContent = city.adcode;
    option.append(name, adcode);
    fragment.appendChild(option);
  });

  if (!cities.length) {
    const empty = document.createElement("p");
    empty.className = "city-option-empty";
    empty.textContent = "没有匹配的城市";
    fragment.appendChild(empty);
  }

  activeCityOptionIndex = -1;
  elements.cityInput.removeAttribute("aria-activedescendant");
  elements.cityOptions.replaceChildren(fragment);
  elements.cityOptions.hidden = false;
  elements.cityInput.setAttribute("aria-expanded", "true");
  elements.cityToggle.setAttribute("aria-expanded", "true");
}

function closeCityOptions() {
  elements.cityOptions.hidden = true;
  elements.cityInput.setAttribute("aria-expanded", "false");
  elements.cityToggle.setAttribute("aria-expanded", "false");
  elements.cityInput.removeAttribute("aria-activedescendant");
  activeCityOptionIndex = -1;
}

function findCityByQuery(query) {
  const normalizedQuery = query.trim().toLowerCase();
  return state.data.cities.find((city) => {
    return (
      city.name.toLowerCase() === normalizedQuery ||
      city.adcode === normalizedQuery
    );
  });
}

function handleCityInputKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeCityOptions();
    elements.cityInput.value = getSelectedCity().name;
    return;
  }

  if (elements.cityOptions.hidden && ["ArrowDown", "ArrowUp"].includes(event.key)) {
    renderCityOptions(elements.cityInput.value);
  }

  const options = [...elements.cityOptions.querySelectorAll("[data-adcode]")];
  if (!options.length) return;

  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    const direction = event.key === "ArrowDown" ? 1 : -1;
    activeCityOptionIndex =
      (activeCityOptionIndex + direction + options.length) % options.length;
    updateActiveCityOption(options);
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
    const activeOption = options[activeCityOptionIndex];
    const exactCity = findCityByQuery(elements.cityInput.value);
    if (activeOption) {
      selectCity(activeOption.dataset.adcode);
    } else if (exactCity) {
      selectCity(exactCity.adcode);
    }
  }
}

function updateActiveCityOption(options) {
  options.forEach((option, index) => {
    option.classList.toggle("active", index === activeCityOptionIndex);
  });
  const activeOption = options[activeCityOptionIndex];
  elements.cityInput.setAttribute("aria-activedescendant", activeOption.id);
  activeOption.scrollIntoView({ block: "nearest" });
}

async function selectCity(adcode, options = {}) {
  state.city = adcode;
  elements.cityInput.value = getSelectedCity().name;
  closeCityOptions();
  syncUrl();
  if (options.scrollToOverview) {
    document.querySelector(".overview-grid").scrollIntoView({ behavior: "smooth" });
  }

  if (state.series.has(adcode)) {
    renderCityViews();
    return;
  }

  // 分片按需加载：只渲染最后一次选择的结果，避免快速连点时旧响应覆盖新城市。
  const token = (pendingCityToken += 1);
  elements.dashboard.classList.add("is-loading");
  try {
    await loadCitySeries(adcode);
    if (token !== pendingCityToken) return;
    renderCityViews();
  } catch (error) {
    if (token !== pendingCityToken) return;
    elements.status.hidden = false;
    elements.status.textContent = `无法加载${getSelectedCity().name}的数据：${error.message}`;
    elements.status.classList.add("error");
  } finally {
    if (token === pendingCityToken) {
      elements.dashboard.classList.remove("is-loading");
    }
  }
}

function renderAll() {
  const { meta } = state.data;
  elements.dataThrough.textContent = formatMonth(meta.endMonth);
  elements.cityCoverage.textContent = `${meta.cityCount} 个`;
  elements.monthCoverage.textContent =
    `${meta.startMonth.replace("-", ".")} – ${meta.endMonth.replace("-", ".")}` +
    ` · ${meta.monthCount} 个月`;
  elements.heroMonth.textContent = `更新至 ${meta.endMonth.replace("-", ".")}`;
  renderAllViews();
}

function renderAllViews() {
  renderCityViews();
  renderMarket();
  renderRanking();
}

function renderCityViews() {
  const city = getSelectedCity();
  elements.cityInput.value = city.name;
  elements.chartCity.textContent = city.name;
  elements.historyCity.textContent = city.name;
  elements.snapshotCity.textContent = city.name;
  elements.legendLabel.textContent = `${getMetricLabel()} · ${BASES[state.basis].label}`;
  renderChartNote();
  renderChart();
  renderLatest();
  renderSnapshot();
  renderHistory();
}

function getSelectedCity() {
  return state.data.cities.find((city) => city.adcode === state.city);
}

function getSeries(adcode = state.city) {
  const series = state.series.get(adcode);
  return series[state.market][state.area][state.basis];
}

function getLatestMonth() {
  // 三种口径的数据终止月份可能不同，不能一律用 meta.endMonth。
  const byBasis = state.data.meta.latestMonthByBasis || {};
  return byBasis[state.basis] || state.data.meta.endMonth;
}

function getMetricLabel() {
  const area = state.area === "all" ? "" : ` · ${AREAS[state.area]}`;
  return `${MARKETS[state.market]}${area}`;
}

// 同比与环比是连续序列；定基/累计不是，必须按基期分段，
// 跨段的两个点之间不存在可比关系，不能连线。
function getSegmentLabel(month) {
  if (state.basis !== "fixed") return "";

  const segment = FIXED_BASE_SEGMENTS.find(
    (item) => month >= item.start && month <= item.end,
  );
  if (segment) return segment.label;
  if (month >= CUMULATIVE_BASIS_START) return `${month.slice(0, 4)} 年内累计`;
  return "";
}

function groupIntoSegments(points) {
  const segments = [];
  points.forEach((point, index) => {
    const label = getSegmentLabel(point.date);
    const current = segments.at(-1);
    if (current && current.label === label) current.indices.push(index);
    else segments.push({ label, short: shortenSegmentLabel(label), indices: [index] });
  });
  return segments;
}

// 年内累计的分段每年一小段，横向空间很窄，只标年份。
function shortenSegmentLabel(label) {
  return label.endsWith("年内累计") ? label.slice(0, 4) : label;
}

function renderChartNote() {
  const isFixed = state.basis === "fixed";
  elements.chartNote.hidden = !isFixed;
  if (!isFixed) return;

  elements.chartNote.textContent =
    "定基基期约每五年轮换一次（2010 → 2015 → 2020），2023 年起改为年内累计同比、每年 1 月重置。" +
    "虚线处两侧属于不同基期，数值不可直接比较，因此不连线。";
}

function renderLatest() {
  const values = getSeries();
  const latestIndex = findLastValueIndex(values);
  const previousIndex = findPreviousValueIndex(values, latestIndex);
  const latest = values[latestIndex];
  const previous = previousIndex >= 0 ? values[previousIndex] : null;
  const month = state.data.dates[latestIndex];
  const difference = previous === null ? null : latest - previous;
  const recentValues = values
    .slice(Math.max(0, latestIndex - 11), latestIndex + 1)
    .filter(isNumber);
  const status = classifyIndex(latest);
  const movement = latest - 100;

  elements.latestMonth.textContent = `${formatMonth(month)} · ${BASES[state.basis].label}`;
  elements.latestValue.textContent = formatIndex(latest);
  elements.latestStatus.textContent = status.label;
  elements.latestStatus.className = `status-pill ${status.className}`;
  elements.latestExplanation.textContent = buildIndexExplanation(movement);
  elements.pointChange.textContent = difference === null
    ? "—"
    : `${formatSigned(difference)} 点`;
  elements.yearRange.textContent = recentValues.length
    ? `${formatIndex(Math.min(...recentValues))}–${formatIndex(Math.max(...recentValues))}`
    : "—";
}

function buildIndexExplanation(movement) {
  const subject = getMetricLabel();
  const comparison = BASES[state.basis].comparison;
  if (Math.abs(movement) < 0.05) {
    return `${subject}价格与${comparison}基本持平。`;
  }

  const direction = movement > 0 ? "上涨" : "下降";
  return `${subject}价格较${comparison}${direction}约 ${Math.abs(movement).toFixed(1)}%。`;
}

function renderSnapshot() {
  const fragment = document.createDocumentFragment();

  elements.snapshotMonth.textContent = formatMonth(getLatestMonth());
  elements.snapshotBasis.textContent = `${BASES[state.basis].label}口径`;

  Object.entries(MARKETS).forEach(([market, marketLabel]) => {
    const group = document.createElement("article");
    group.className = "snapshot-market";

    const heading = document.createElement("div");
    heading.className = "snapshot-market-heading";
    const title = document.createElement("h3");
    title.textContent = marketLabel;
    const hint = document.createElement("span");
    hint.textContent = "指数 100 = 持平";
    heading.append(title, hint);

    const metrics = document.createElement("div");
    metrics.className = "snapshot-metrics";
    Object.entries(AREAS).forEach(([area, areaLabel]) => {
      metrics.appendChild(buildSnapshotMetric(market, area, areaLabel));
    });

    group.append(heading, metrics);
    fragment.appendChild(group);
  });

  elements.snapshotGrid.replaceChildren(fragment);
}

function buildSnapshotMetric(market, area, areaLabel) {
  const values = state.series.get(state.city)[market][area][state.basis];
  const latestIndex = findLastValueIndex(values);
  const previousIndex = findPreviousValueIndex(values, latestIndex);
  const value = latestIndex >= 0 ? values[latestIndex] : null;
  const previous = previousIndex >= 0 ? values[previousIndex] : null;
  const change = isNumber(value) && isNumber(previous) ? value - previous : null;
  const status = classifyIndex(value);
  const isActive = market === state.market && area === state.area;
  const button = document.createElement("button");

  button.type = "button";
  button.className = `snapshot-metric${isActive ? " active" : ""}`;
  button.dataset.market = market;
  button.dataset.area = area;
  button.setAttribute("aria-pressed", String(isActive));
  button.setAttribute(
    "aria-label",
    `${MARKETS[market]}${areaLabel}，指数 ${formatIndex(value)}，${status.label}`,
  );

  const top = document.createElement("span");
  top.className = "snapshot-metric-top";
  const label = document.createElement("span");
  label.textContent = areaLabel;
  const stateLabel = document.createElement("span");
  stateLabel.className = `snapshot-state direction-${status.className || "flat"}`;
  stateLabel.textContent = `${status.symbol} ${status.label}`;
  top.append(label, stateLabel);

  const metricValue = document.createElement("strong");
  metricValue.textContent = formatIndex(value);
  const changeLabel = document.createElement("small");
  changeLabel.className = directionClass(change);
  changeLabel.textContent = change === null
    ? "暂无上期对比"
    : `较上期读数 ${formatSigned(change)} 点`;

  button.append(top, metricValue, changeLabel);
  return button;
}

function renderMarket() {
  const latestMonth = getLatestMonth();
  const rows = buildRankingRows();
  const counts = rows.reduce(
    (result, row) => {
      result[classifyIndex(row.value).key] += 1;
      return result;
    },
    { rising: 0, flat: 0, falling: 0 },
  );

  elements.risingCount.textContent = counts.rising;
  elements.flatCount.textContent = counts.flat;
  elements.fallingCount.textContent = counts.falling;

  // 占比条：三段宽度按城市数分配，比三个孤立的数字更快读出比例。
  const total = counts.rising + counts.flat + counts.falling;
  const share = (count) => (total ? `${(count / total) * 100}%` : "0%");
  elements.risingBar.style.width = share(counts.rising);
  elements.flatBar.style.width = share(counts.flat);
  elements.fallingBar.style.width = share(counts.falling);

  elements.marketCaption.textContent =
    `${formatMonth(latestMonth)} · ${getMetricLabel()} · ${BASES[state.basis].label}指数`;
}

function buildRankingRows() {
  // 排行榜只需要每城的最新读数，直接读骨架里预计算的截面，
  // 不必为了排序把 70 城的完整序列都下载下来。
  return state.data.cities
    .map((city) => {
      const summary =
        state.data.latest[city.adcode]?.[state.market]?.[state.area]?.[state.basis];
      return {
        ...city,
        value: summary ? summary[0] : null,
        change: summary ? summary[1] : null,
      };
    })
    .filter((row) => isNumber(row.value))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, "zh-CN"));
}

function renderRanking() {
  const query = state.search.toLowerCase();
  const rankingRows = buildRankingRows();
  const ranks = new Map(
    rankingRows.map((row, index) => [row.adcode, index + 1]),
  );
  const rows = rankingRows.filter((row) => {
    return row.name.toLowerCase().includes(query) || row.adcode.includes(query);
  });
  const fragment = document.createDocumentFragment();

  rows.forEach((row) => {
    const status = classifyIndex(row.value);
    const tr = document.createElement("tr");
    tr.className = "city-row";
    tr.tabIndex = 0;
    tr.dataset.adcode = row.adcode;
    tr.setAttribute("aria-label", `查看${row.name}详细数据`);

    const rank = buildCell(String(ranks.get(row.adcode)), "rank-number");
    const city = buildCell(row.name, "city-name-cell");
    const index = buildCell(formatIndex(row.value), "index-cell");
    const change = buildCell(
      row.change === null ? "—" : `${formatSigned(row.change)} 点`,
      directionClass(row.change),
    );
    const statusCell = buildCell("", `direction-${status.className || "flat"}`);
    const dot = document.createElement("span");
    dot.className = "state-dot";
    statusCell.append(dot, status.label);
    tr.append(rank, city, index, change, statusCell);
    fragment.appendChild(tr);
  });

  elements.rankingBody.replaceChildren(fragment);
  elements.rankingEmpty.hidden = rows.length > 0;
}

function buildCell(text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

function selectRankingCity(event) {
  const row = event.target.closest(".city-row");
  if (!row) return;
  selectCity(row.dataset.adcode, { scrollToOverview: true });
}

function renderHistory() {
  const values = getSeries();
  const latestIndex = findLastValueIndex(values);
  const startIndex = Math.max(0, latestIndex - 11);
  const fragment = document.createDocumentFragment();

  for (let index = latestIndex; index >= startIndex; index -= 1) {
    if (!isNumber(values[index])) continue;
    const item = document.createElement("article");
    item.className = "history-item";

    const month = document.createElement("span");
    month.textContent = formatMonth(state.data.dates[index]);
    const value = document.createElement("strong");
    value.textContent = formatIndex(values[index]);
    const status = classifyIndex(values[index]);
    const direction = document.createElement("em");
    direction.className = `direction-${status.className || "flat"}`;
    direction.textContent = status.symbol;
    item.append(month, value, direction);
    fragment.appendChild(item);
  }

  elements.historyGrid.replaceChildren(fragment);
}

function renderChart() {
  if (!state.data || elements.dashboard.hidden) return;

  const canvas = elements.trendChart;
  const context = canvas.getContext("2d");
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);

  const fullSeries = getSeries();
  const fullDates = state.data.dates;
  const range = state.range === "all" ? fullSeries.length : state.range;
  const start = Math.max(0, fullSeries.length - range);
  const points = fullSeries
    .map((value, index) => ({ value, date: fullDates[index], sourceIndex: index }))
    .slice(start)
    .filter((point) => isNumber(point.value));

  if (points.length < 2) return;

  const padding = { top: 18, right: 18, bottom: 34, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const rawMin = Math.min(100, ...points.map((point) => point.value));
  const rawMax = Math.max(100, ...points.map((point) => point.value));
  const scale = niceScale(rawMin, rawMax);
  const { min: yMin, max: yMax } = scale;
  const xFor = (index) => padding.left + (index / (points.length - 1)) * plotWidth;
  const yFor = (value) => padding.top + ((yMax - value) / (yMax - yMin)) * plotHeight;

  drawChartGrid(context, width, padding, plotWidth, plotHeight, scale, yFor);

  const segments = groupIntoSegments(points);
  if (segments.length > 1) {
    drawSegmentBreaks(context, segments, points, xFor, padding, plotHeight);
  }

  context.strokeStyle = CHART_COLORS.line;
  context.fillStyle = CHART_COLORS.line;
  context.lineWidth = 2;
  context.lineJoin = "round";
  context.lineCap = "round";
  segments.forEach((segment) => {
    if (segment.indices.length === 1) {
      const only = segment.indices[0];
      context.beginPath();
      context.arc(xFor(only), yFor(points[only].value), 2.5, 0, Math.PI * 2);
      context.fill();
      return;
    }

    context.beginPath();
    segment.indices.forEach((pointIndex, order) => {
      const x = xFor(pointIndex);
      const y = yFor(points[pointIndex].value);
      if (order === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
  });

  const lastPoint = points.at(-1);
  context.beginPath();
  context.arc(xFor(points.length - 1), yFor(lastPoint.value), 3.5, 0, Math.PI * 2);
  context.fillStyle = CHART_COLORS.surface;
  context.fill();
  context.lineWidth = 2;
  context.strokeStyle = CHART_COLORS.line;
  context.stroke();

  drawXAxis(context, points, padding, plotWidth, height);

  chartModel = {
    points,
    xFor,
    yFor,
    bounds: {
      left: padding.left,
      right: width - padding.right,
      top: padding.top,
      bottom: height - padding.bottom,
    },
  };

  canvas.setAttribute(
    "aria-label",
    `${getSelectedCity().name}${getMetricLabel()}${BASES[state.basis].label}指数，` +
    `${formatMonth(points[0].date)}至${formatMonth(lastPoint.date)}，最新值${formatIndex(lastPoint.value)}` +
    (segments.length > 1
      ? `。因基期轮换分为 ${segments.length} 段绘制，段间不可比。`
      : ""),
  );
}

// 在基期切换处画竖向断点并标注各段基期，让"这里不可比"在图上直接可见。
function drawSegmentBreaks(context, segments, points, xFor, padding, plotHeight) {
  const top = padding.top;
  const bottom = padding.top + plotHeight;

  context.save();
  context.setLineDash([3, 4]);
  context.strokeStyle = CHART_COLORS.divider;
  context.lineWidth = 1;
  for (let index = 1; index < segments.length; index += 1) {
    const previousEnd = segments[index - 1].indices.at(-1);
    const currentStart = segments[index].indices[0];
    const x = (xFor(previousEnd) + xFor(currentStart)) / 2;
    context.beginPath();
    context.moveTo(x, top);
    context.lineTo(x, bottom);
    context.stroke();
  }
  context.restore();

  context.save();
  context.font = `10px ${CHART_FONT}`;
  context.fillStyle = CHART_COLORS.axisStrong;
  context.textAlign = "center";
  context.textBaseline = "top";
  segments.forEach((segment) => {
    if (!segment.short) return;
    const left = xFor(segment.indices[0]);
    const right = xFor(segment.indices.at(-1));
    const width = context.measureText(segment.short).width;
    if (right - left < width + 8) return;
    context.fillText(segment.short, (left + right) / 2, top + 2);
  });
  context.restore();
}

// 刻度取整：步长只从 NICE_STEPS 里选，避免出现 104.9 / 101.8 这类读不动的刻度值。
function niceScale(min, max) {
  const spread = Math.max(max - min, 1);
  const low = min - spread * 0.14;
  const high = max + spread * 0.14;

  for (const step of NICE_STEPS) {
    const scaleMin = Math.floor(low / step) * step;
    const scaleMax = Math.ceil(high / step) * step;
    if ((scaleMax - scaleMin) / step <= 6) {
      return { min: round2(scaleMin), max: round2(scaleMax), step };
    }
  }

  const step = NICE_STEPS.at(-1);
  return {
    min: round2(Math.floor(low / step) * step),
    max: round2(Math.ceil(high / step) * step),
    step,
  };
}

function round2(value) {
  return Math.round(value * 100) / 100;
}

function drawChartGrid(context, width, padding, plotWidth, plotHeight, scale, yFor) {
  context.font = `10px ${CHART_FONT}`;
  context.textAlign = "right";
  context.textBaseline = "middle";
  context.lineWidth = 1;

  for (let value = scale.min; value <= scale.max + scale.step / 2; value += scale.step) {
    const tickValue = round2(value);
    const y = Math.round(yFor(tickValue)) + 0.5;
    const isBenchmark = Math.abs(tickValue - 100) < 0.001;

    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.strokeStyle = isBenchmark ? CHART_COLORS.benchmark : CHART_COLORS.grid;
    context.setLineDash(isBenchmark ? [4, 4] : []);
    context.stroke();
    context.setLineDash([]);

    context.fillStyle = isBenchmark ? CHART_COLORS.axisStrong : CHART_COLORS.axis;
    context.fillText(formatIndex(tickValue), padding.left - 8, y);
  }
}

function drawXAxis(context, points, padding, plotWidth, height) {
  const labelCount = Math.min(5, points.length);
  context.fillStyle = CHART_COLORS.axis;
  context.font = `10px ${CHART_FONT}`;
  context.textBaseline = "bottom";

  for (let index = 0; index < labelCount; index += 1) {
    const pointIndex = Math.round((index / (labelCount - 1 || 1)) * (points.length - 1));
    const x = padding.left + (pointIndex / (points.length - 1)) * plotWidth;
    context.textAlign = index === 0 ? "left" : index === labelCount - 1 ? "right" : "center";
    context.fillText(formatShortMonth(points[pointIndex].date), x, height);
  }
}

function showChartTooltip(event) {
  if (!chartModel) return;
  const rect = elements.trendChart.getBoundingClientRect();
  const pointer = event.touches?.[0] || event;
  const x = pointer.clientX - rect.left;
  if (x < chartModel.bounds.left || x > chartModel.bounds.right) {
    hideChartTooltip();
    return;
  }

  const ratio = (x - chartModel.bounds.left) /
    (chartModel.bounds.right - chartModel.bounds.left);
  const index = Math.max(
    0,
    Math.min(chartModel.points.length - 1, Math.round(ratio * (chartModel.points.length - 1))),
  );
  const point = chartModel.points[index];
  const pointX = chartModel.xFor(index);
  const pointY = chartModel.yFor(point.value);

  elements.chartTooltip.innerHTML =
    `${formatMonth(point.date)}<strong>${formatIndex(point.value)}</strong>`;
  elements.chartTooltip.style.left = `${pointX}px`;
  elements.chartTooltip.style.top = `${pointY}px`;
  elements.chartTooltip.hidden = false;
}

function hideChartTooltip() {
  elements.chartTooltip.hidden = true;
}

function scheduleChartRender() {
  window.cancelAnimationFrame(resizeFrame);
  resizeFrame = window.requestAnimationFrame(renderChart);
}

function setActiveButton(container, value) {
  container.querySelectorAll("button[data-value]").forEach((button) => {
    const isActive = button.dataset.value === value;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function syncUrl() {
  const params = new URLSearchParams();
  params.set("city", state.city);
  params.set("market", state.market);
  params.set("area", state.area);
  params.set("basis", state.basis);
  params.set("range", String(state.range));
  window.history.replaceState(null, "", `${window.location.pathname}?${params}`);
}

function classifyIndex(value) {
  if (!isNumber(value)) {
    return { key: "flat", label: "暂无", className: "flat", symbol: "—" };
  }
  if (value > 100.05) {
    return { key: "rising", label: "上涨", className: "up", symbol: "↑" };
  }
  if (value < 99.95) {
    return { key: "falling", label: "下降", className: "down", symbol: "↓" };
  }
  return { key: "flat", label: "持平", className: "flat", symbol: "→" };
}

function directionClass(value) {
  if (!isNumber(value) || Math.abs(value) < 0.05) return "direction-flat";
  return value > 0 ? "direction-up" : "direction-down";
}

function findLastValueIndex(values) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (isNumber(values[index])) return index;
  }
  return -1;
}

function findPreviousValueIndex(values, fromIndex) {
  for (let index = fromIndex - 1; index >= 0; index -= 1) {
    if (isNumber(values[index])) return index;
  }
  return -1;
}

function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function formatIndex(value) {
  return isNumber(value) ? value.toFixed(1) : "—";
}

function formatSigned(value) {
  if (!isNumber(value)) return "—";
  const rounded = Math.abs(value) < 0.05 ? 0 : value;
  return `${rounded > 0 ? "+" : ""}${rounded.toFixed(1)}`;
}

function formatMonth(month) {
  const [year, value] = month.split("-");
  return `${year} 年 ${Number(value)} 月`;
}

function formatShortMonth(month) {
  const [year, value] = month.split("-");
  return `${year}.${String(value).padStart(2, "0")}`;
}
