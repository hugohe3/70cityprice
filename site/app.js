"use strict";

const METRICS = {
  new: "新建商品住宅",
  resale: "二手住宅",
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
};

const state = {
  data: null,
  city: "110100",
  metric: "new",
  basis: "yoy",
  range: 60,
  search: "",
};

const elements = {};
let chartModel = null;
let resizeFrame = null;

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  cacheElements();
  bindEvents();

  try {
    const response = await fetch("./data/dashboard.json");
    if (!response.ok) {
      throw new Error(`数据请求失败 (${response.status})`);
    }

    state.data = await response.json();
    validateData(state.data);
    applyUrlState();
    populateCitySelect();
    elements.dashboard.hidden = false;
    renderAll();
    elements.status.hidden = true;
  } catch (error) {
    elements.status.textContent = `暂时无法加载数据：${error.message}`;
    elements.status.classList.add("error");
  }
}

function cacheElements() {
  const ids = [
    "basis-control",
    "chart-city",
    "chart-tooltip",
    "city-coverage",
    "city-search",
    "city-select",
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
    "metric-control",
    "month-coverage",
    "page-status",
    "point-change",
    "range-select",
    "ranking-body",
    "ranking-empty",
    "rising-count",
    "trend-chart",
    "year-range",
  ];

  ids.forEach((id) => {
    const key = id.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    elements[key] = document.getElementById(id);
  });
  elements.status = elements.pageStatus;
  elements.dashboard = document.getElementById("dashboard");
}

function bindEvents() {
  elements.citySelect.addEventListener("change", (event) => {
    state.city = event.target.value;
    renderCityViews();
    syncUrl();
  });

  elements.metricControl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    state.metric = button.dataset.value;
    setActiveButton(elements.metricControl, state.metric);
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
    data.schemaVersion !== 1 ||
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
  const metric = params.get("metric");
  const basis = params.get("basis");
  const range = params.get("range");

  if (city && state.data.series[city]) state.city = city;
  if (metric && METRICS[metric]) state.metric = metric;
  if (basis && BASES[basis]) state.basis = basis;
  if (range === "all") state.range = "all";
  if (["36", "60", "120"].includes(range)) state.range = Number(range);

  setActiveButton(elements.metricControl, state.metric);
  setActiveButton(elements.basisControl, state.basis);
  elements.rangeSelect.value = String(state.range);
}

function populateCitySelect() {
  const fragment = document.createDocumentFragment();
  state.data.cities.forEach((city) => {
    const option = document.createElement("option");
    option.value = city.adcode;
    option.textContent = city.name;
    fragment.appendChild(option);
  });
  elements.citySelect.appendChild(fragment);
  elements.citySelect.value = state.city;
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
  elements.citySelect.value = state.city;
  elements.chartCity.textContent = city.name;
  elements.historyCity.textContent = city.name;
  elements.legendLabel.textContent = `${METRICS[state.metric]} · ${BASES[state.basis].label}`;
  renderChart();
  renderLatest();
  renderHistory();
}

function getSelectedCity() {
  return state.data.cities.find((city) => city.adcode === state.city);
}

function getSeries(adcode = state.city) {
  return state.data.series[adcode][state.metric][state.basis];
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
  const subject = METRICS[state.metric];
  const comparison = BASES[state.basis].comparison;
  if (Math.abs(movement) < 0.05) {
    return `${subject}价格与${comparison}基本持平。`;
  }

  const direction = movement > 0 ? "上涨" : "下降";
  return `${subject}价格较${comparison}${direction}约 ${Math.abs(movement).toFixed(1)}%。`;
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
    `${formatMonth(latestMonth)} · ${METRICS[state.metric]}${BASES[state.basis].label}指数`;
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
  state.city = row.dataset.adcode;
  renderCityViews();
  syncUrl();
  document.querySelector(".overview-grid").scrollIntoView({ behavior: "smooth" });
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
    `${getSelectedCity().name}${METRICS[state.metric]}${BASES[state.basis].label}指数，` +
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
  params.set("metric", state.metric);
  params.set("basis", state.basis);
  params.set("range", String(state.range));
  window.history.replaceState(null, "", `${window.location.pathname}?${params}`);
}

function classifyIndex(value) {
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
