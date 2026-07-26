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

const state = {
  data: null,
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

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  try {
    cacheElements();
    bindEvents();
    const buildVersion = document.documentElement.dataset.buildVersion || "dev";
    const response = await fetch(
      `./data/dashboard.json?v=${encodeURIComponent(buildVersion)}`,
    );
    if (!response.ok) {
      throw new Error(`数据请求失败 (${response.status})`);
    }

    state.data = await response.json();
    validateData(state.data);
    applyUrlState();
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

function cacheElements() {
  const ids = [
    "area-control",
    "basis-control",
    "chart-city",
    "chart-tooltip",
    "city-coverage",
    "city-input",
    "city-options",
    "city-search",
    "city-toggle",
    "dashboard",
    "data-through",
    "falling-count",
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
    data.schemaVersion !== 2 ||
    !Array.isArray(data.dates) ||
    !Array.isArray(data.cities) ||
    typeof data.series !== "object"
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

  if (city && state.data.series[city]) state.city = city;
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

function selectCity(adcode, options = {}) {
  state.city = adcode;
  elements.cityInput.value = getSelectedCity().name;
  closeCityOptions();
  renderCityViews();
  syncUrl();
  if (options.scrollToOverview) {
    document.querySelector(".overview-grid").scrollIntoView({ behavior: "smooth" });
  }
}

function renderAll() {
  const { meta } = state.data;
  const startYear = meta.startMonth.slice(0, 4);
  const endLabel = formatMonth(meta.endMonth);

  elements.dataThrough.textContent = `数据截至 ${endLabel}`;
  elements.cityCoverage.textContent = `${meta.cityCount} 个城市`;
  elements.monthCoverage.textContent = `${startYear} 年至今 · ${meta.monthCount} 个月`;
  elements.heroMonth.textContent = meta.endMonth.replace("-", ".");
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
  renderChart();
  renderLatest();
  renderSnapshot();
  renderHistory();
}

function getSelectedCity() {
  return state.data.cities.find((city) => city.adcode === state.city);
}

function getSeries(adcode = state.city) {
  return state.data.series[adcode][state.market][state.area][state.basis];
}

function getMetricLabel() {
  const area = state.area === "all" ? "" : ` · ${AREAS[state.area]}`;
  return `${MARKETS[state.market]}${area}`;
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
  const latestMonth = state.data.meta.endMonth;

  elements.snapshotMonth.textContent = formatMonth(latestMonth);
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
  const values = state.data.series[state.city][market][area][state.basis];
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
  const latestMonth = state.data.meta.endMonth;
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
  elements.marketCaption.textContent =
    `${formatMonth(latestMonth)} · ${getMetricLabel()} · ${BASES[state.basis].label}指数`;
}

function buildRankingRows() {
  return state.data.cities
    .map((city) => {
      const series = getSeries(city.adcode);
      const latestIndex = findLastValueIndex(series);
      const previousIndex = findPreviousValueIndex(series, latestIndex);
      const value = series[latestIndex];
      const previous = previousIndex >= 0 ? series[previousIndex] : null;
      return {
        ...city,
        value,
        change: previous === null ? null : value - previous,
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
  const spread = Math.max(rawMax - rawMin, 2);
  const yMin = Math.floor((rawMin - spread * 0.14) * 2) / 2;
  const yMax = Math.ceil((rawMax + spread * 0.14) * 2) / 2;
  const xFor = (index) => padding.left + (index / (points.length - 1)) * plotWidth;
  const yFor = (value) => padding.top + ((yMax - value) / (yMax - yMin)) * plotHeight;

  drawChartGrid(context, width, padding, plotWidth, plotHeight, yMin, yMax, yFor);

  context.beginPath();
  points.forEach((point, index) => {
    const x = xFor(index);
    const y = yFor(point.value);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.strokeStyle = "#d94f31";
  context.lineWidth = 2.5;
  context.lineJoin = "round";
  context.lineCap = "round";
  context.stroke();

  const lastPoint = points.at(-1);
  context.beginPath();
  context.arc(xFor(points.length - 1), yFor(lastPoint.value), 4, 0, Math.PI * 2);
  context.fillStyle = "#fffef9";
  context.fill();
  context.lineWidth = 2.5;
  context.strokeStyle = "#d94f31";
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
    `${formatMonth(points[0].date)}至${formatMonth(lastPoint.date)}，最新值${formatIndex(lastPoint.value)}`,
  );
}

function drawChartGrid(context, width, padding, plotWidth, plotHeight, yMin, yMax, yFor) {
  const tickCount = 5;
  context.font = '11px "PingFang SC", sans-serif';
  context.textAlign = "right";
  context.textBaseline = "middle";

  for (let tick = 0; tick <= tickCount; tick += 1) {
    const value = yMin + ((yMax - yMin) * tick) / tickCount;
    const y = yFor(value);
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(padding.left + plotWidth, y);
    context.strokeStyle = Math.abs(value - 100) < (yMax - yMin) / tickCount / 2
      ? "#9e9b91"
      : "#e5e2d9";
    context.lineWidth = 1;
    context.setLineDash(value === 100 ? [5, 5] : []);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = "#7b817d";
    context.fillText(formatIndex(value), padding.left - 8, y);
  }

  if (yMin < 100 && yMax > 100) {
    const benchmarkY = yFor(100);
    context.beginPath();
    context.moveTo(padding.left, benchmarkY);
    context.lineTo(width - padding.right, benchmarkY);
    context.strokeStyle = "#85877f";
    context.setLineDash([5, 5]);
    context.stroke();
    context.setLineDash([]);
  }
}

function drawXAxis(context, points, padding, plotWidth, height) {
  const labelCount = Math.min(5, points.length);
  context.fillStyle = "#7b817d";
  context.font = '11px "PingFang SC", sans-serif';
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
