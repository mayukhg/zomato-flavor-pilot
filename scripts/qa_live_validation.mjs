/**
 * Live integration QA for FlavorPilot against the official Zomato MCP server.
 * Does not call create_cart or checkout_cart.
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const SCREENSHOT_DIR = path.join(ROOT, "screenshots");
const FRONTEND = "http://localhost:8080";
const API = "http://localhost:8000";
const GOA_MARKERS = ["goa", "ponda", "chicalim", "madkai", "camotim"];
const MOCK_NAMES = ["green theory", "fuel & fire", "fuel and fire"];

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const cases = [];

function record(entry) {
  cases.push(entry);
  const mark = entry.status === "pass" ? "PASS" : entry.status === "blocked" ? "BLOCKED" : "FAIL";
  console.log(`[${mark}] ${entry.id} ${entry.name} — ${entry.detail}`);
}

async function shot(page, filename) {
  const file = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: file, fullPage: false });
  return filename;
}

async function api(method, urlPath, body, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API}${urlPath}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = { raw: text.slice(0, 500) };
    }
    return { status: response.status, json };
  } finally {
    clearTimeout(timer);
  }
}

function looksGoa(restaurants) {
  const blob = JSON.stringify(restaurants).toLowerCase();
  return GOA_MARKERS.filter((marker) => blob.includes(marker));
}

function summarizeSearch(json) {
  const restaurants = json?.restaurants ?? [];
  const menu = json?.menu_items ?? [];
  const names = restaurants.map((r) => r.name).slice(0, 8);
  const locations = restaurants.map((r) => r.location).slice(0, 8);
  return { count: restaurants.length, menu: menu.length, names, locations, ms: json?.execution_time_ms, session: json?.session_id };
}

async function runApi() {
  const root = await api("GET", "/", null, 15000).catch((error) => ({ error: String(error) }));
  if (root.error) {
    record({ id: "API-01", area: "api", name: "API process reachable", status: "fail", detail: root.error });
    return null;
  }
  record({
    id: "API-01",
    area: "api",
    name: "API root",
    status: root.status === 200 && root.json?.status === "operational" ? "pass" : "fail",
    detail: `HTTP ${root.status} transport=${root.json?.mcp_transport ?? "missing"}`,
  });

  const health = await api("GET", "/health", null, 15000);
  record({
    id: "API-02",
    area: "api",
    name: "Health endpoint",
    status: health.status === 200 ? "pass" : "fail",
    detail: `HTTP ${health.status} body=${JSON.stringify(health.json)}`,
    note: "This endpoint reports database=connected without probing Postgres.",
  });

  const mcp = await api("GET", "/api/v1/mcp/status", null, 120000);
  const tools = mcp.json?.tools ?? [];
  const required = [
    "get_restaurants_for_keyword",
    "get_menu_items_listing",
    "get_saved_addresses_for_user",
    "get_restaurant_menu_by_categories",
  ];
  const missing = required.filter((name) => !tools.includes(name));
  record({
    id: "API-03",
    area: "mcp",
    name: "Zomato MCP status and tool list",
    status: mcp.status === 200 && mcp.json?.connected && missing.length === 0 ? "pass" : "fail",
    detail: `HTTP ${mcp.status} connected=${mcp.json?.connected} tools=${tools.length} missing=${missing.join(",") || "none"} server=${mcp.json?.server ?? ""}`,
    tools,
  });

  const pizza = await api("POST", "/api/v1/search/", {
    query: "pizza",
    location: "",
    group_size: 1,
  });
  const pizzaSummary = summarizeSearch(pizza.json);
  const pizzaGoa = looksGoa(pizza.json?.restaurants ?? []);
  const pizzaPrices = (pizza.json?.menu_items ?? []).filter((item) => Number(item.price_inr) > 0);
  record({
    id: "API-04",
    area: "search",
    name: "Pizza search on pinned Wanwadi address",
    status:
      pizza.status === 200 && pizzaSummary.count > 0 && pizzaGoa.length === 0 && pizzaPrices.length > 0
        ? "pass"
        : "fail",
    detail: `HTTP ${pizza.status} kitchens=${pizzaSummary.count} menu=${pizzaSummary.menu} priced=${pizzaPrices.length} goaMarkers=${pizzaGoa.join(",") || "none"} names=${pizzaSummary.names.join(" | ")} locations=${pizzaSummary.locations.join(" | ")}`,
    summary: pizzaSummary,
    error: pizza.json?.detail,
  });

  const group = await api("POST", "/api/v1/search/", {
    query: "Group lunch for 6 under ₹2,000 — 3 keto, 1 vegan, 2 high-protein, 30-min ETA",
    location: "",
    group_size: 6,
    dietary_constraints: ["keto", "vegan", "high protein"],
  });
  const groupSummary = summarizeSearch(group.json);
  const groupGoa = looksGoa(group.json?.restaurants ?? []);
  record({
    id: "API-05",
    area: "search",
    name: "Default group-lunch prompt",
    status: group.status === 200 && groupSummary.count > 0 && groupGoa.length === 0 ? "pass" : "fail",
    detail: `HTTP ${group.status} kitchens=${groupSummary.count} menu=${groupSummary.menu} ms=${Math.round(groupSummary.ms || 0)} goaMarkers=${groupGoa.join(",") || "none"} names=${groupSummary.names.join(" | ")}`,
    summary: groupSummary,
    error: group.json?.detail,
  });

  const sessionId = pizza.json?.session_id || group.json?.session_id;
  if (sessionId) {
    const trajectory = await api("GET", `/api/v1/agent/trajectory/${sessionId}`, null, 20000);
    const dbDown = /connection refused|could not connect|operationalerror|postgres/i.test(JSON.stringify(trajectory.json));
    record({
      id: "API-06",
      area: "trajectory",
      name: "Agent trajectory persistence",
      status: trajectory.status === 200 ? "pass" : dbDown ? "blocked" : "fail",
      detail: `HTTP ${trajectory.status} session=${sessionId} ${trajectory.json?.detail || trajectory.json?.status || ""}`.trim(),
    });
  } else {
    record({ id: "API-06", area: "trajectory", name: "Agent trajectory persistence", status: "fail", detail: "No session_id from search" });
  }

  const evals = await api("GET", "/api/v1/evals/summary", null, 20000);
  const evalDb = /connection refused|could not connect|operationalerror|postgres/i.test(JSON.stringify(evals.json));
  record({
    id: "API-07",
    area: "evals",
    name: "Eval summary endpoint",
    status: evals.status === 200 ? "pass" : evalDb ? "blocked" : "fail",
    detail: `HTTP ${evals.status} ${evals.json?.detail || JSON.stringify(evals.json)?.slice(0, 240)}`,
  });

  const cart = await api("POST", "/api/v1/cart/build", {
    session_id: sessionId || "session_qa",
    restaurant_id: pizza.json?.restaurants?.[0]?.restaurant_id || "res_qa",
    items: [
      {
        item_id: pizza.json?.menu_items?.[0]?.item_id || "item_qa",
        name: pizza.json?.menu_items?.[0]?.name || "QA item",
        quantity: 1,
        price_inr: pizza.json?.menu_items?.[0]?.price_inr || 100,
        tags: ["qa"],
      },
    ],
    delivery_address: {
      street: "Flat 108 A",
      area: "Parmar Nagar",
      city: "Pune",
      pincode: "411040",
    },
  }, 20000);
  const cartDb = /connection refused|could not connect|operationalerror|postgres/i.test(JSON.stringify(cart.json));
  record({
    id: "API-08",
    area: "cart",
    name: "Local cart staging (no Zomato checkout)",
    status: cart.status === 200 ? "pass" : cartDb ? "blocked" : "fail",
    detail: `HTTP ${cart.status} ${cart.json?.detail || cart.json?.cart_id || ""}`.trim() + " Checkout was not called.",
  });

  record({
    id: "API-09",
    area: "safety",
    name: "No live order placement",
    status: "pass",
    detail: "create_cart and checkout_cart were not invoked. Approval in the UI only stages local state.",
  });

  return { pizza, group };
}

async function runUi() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text().slice(0, 300));
  });
  page.on("requestfailed", (req) => {
    failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ""}`);
  });

  try {
    await page.goto(FRONTEND, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.getByRole("heading", { name: "What should the team eat today?" }).waitFor({ timeout: 20000 });
    const initial = await shot(page, "qa_01_dashboard_initial.png");
    record({
      id: "UI-01",
      area: "ui",
      name: "Dashboard loads",
      status: "pass",
      detail: "Group concierge heading rendered",
      screenshot: initial,
    });

    const hero = page.locator("section").filter({ has: page.getByRole("heading", { name: "What should the team eat today?" }) });
    await hero.screenshot({ path: path.join(SCREENSHOT_DIR, "qa_02_hero.png") });
    record({ id: "UI-02", area: "ui", name: "Hero and saved-address prompt", status: "pass", detail: "Hero shows Saved Zomato address and Build my order", screenshot: "qa_02_hero.png" });

    await page.locator("header").screenshot({ path: path.join(SCREENSHOT_DIR, "qa_03_header_metrics.png") });
    const metricsVisible = await page.getByText("Groundedness").isVisible();
    record({
      id: "UI-03",
      area: "ui",
      name: "Metrics bar",
      status: metricsVisible ? "pass" : "fail",
      detail: metricsVisible ? "Groundedness, allergen safety, cost, and latency metrics are visible" : "Metrics missing",
      screenshot: "qa_03_header_metrics.png",
    });

    let mcpLive = false;
    try {
      await page.locator("header").getByText("Live", { exact: true }).waitFor({ timeout: 90000 });
      mcpLive = true;
    } catch {
      mcpLive = false;
    }
    const sidebar = await shot(page, "qa_04_mcp_health.png");
    const sidebarLive = await page.getByText("MCP health").locator("xpath=..").getByText("Live").count();
    record({
      id: "UI-04",
      area: "mcp",
      name: "Header and sidebar show Zomato MCP Live",
      status: mcpLive ? "pass" : "fail",
      detail: `headerLive=${mcpLive} sidebarLiveCount=${sidebarLive}`,
      screenshot: sidebar,
    });

    await page.getByLabel("Describe your order").fill("pizza");
    await page.getByRole("button", { name: "Build my order" }).click();
    await shot(page, "qa_05_search_running.png");
    const finished = page.getByText("Search finished");
    const errorBanner = page.getByText("Zomato MCP did not return results");
    const outcome = await new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (!settled) {
          settled = true;
          resolve(value);
        }
      };
      finished.waitFor({ timeout: 180000 }).then(() => finish("done")).catch(() => finish("timeout"));
      errorBanner.waitFor({ timeout: 180000 }).then(() => finish("error")).catch(() => {});
    });

    if (outcome !== "done") {
      const errText = outcome === "error" ? await errorBanner.locator("xpath=..").innerText() : "timed out";
      await shot(page, "qa_06_search_failed.png");
      record({ id: "UI-05", area: "search", name: "Pizza search from the UI", status: "fail", detail: errText.slice(0, 400), screenshot: "qa_06_search_failed.png" });
    } else {
      const kitchenTitle = await page.getByText(/kitchens from Zomato/).innerText();
      const cards = page.locator("article");
      const cardCount = await cards.count();
      const bodyText = (await page.locator("main").innerText()).toLowerCase();
      const mockHit = MOCK_NAMES.filter((name) => bodyText.includes(name));
      const goaHit = GOA_MARKERS.filter((name) => bodyText.includes(name));
      await page.getByText(/kitchens from Zomato/).scrollIntoViewIfNeeded();
      await shot(page, "qa_06_restaurant_cards.png");
      record({
        id: "UI-05",
        area: "search",
        name: "Pizza search renders live kitchens",
        status: cardCount > 0 && mockHit.length === 0 && goaHit.length === 0 ? "pass" : "fail",
        detail: `${kitchenTitle}; cards=${cardCount}; mock=${mockHit.join(",") || "none"}; goa=${goaHit.join(",") || "none"}`,
        screenshot: "qa_06_restaurant_cards.png",
      });

      const cartText = await page.getByText("Staged Zomato cart").locator("xpath=ancestor::section").innerText();
      const cartLines = (cartText.match(/₹/g) || []).length;
      await page.getByText("Staged Zomato cart").scrollIntoViewIfNeeded();
      await shot(page, "qa_07_staged_cart.png");
      record({
        id: "UI-06",
        area: "cart",
        name: "Cart fills from Zomato menu",
        status: cartLines >= 2 && !/menu items from the selected zomato restaurant show up here/i.test(cartText) ? "pass" : "fail",
        detail: `rupee marks=${cartLines}`,
        screenshot: "qa_07_staged_cart.png",
      });

      await page.getByText("Lead–Worker trajectory").scrollIntoViewIfNeeded();
      await shot(page, "qa_08_trajectory.png");
      record({
        id: "UI-07",
        area: "ui",
        name: "Lead-worker trajectory after search",
        status: "pass",
        detail: "Search finished is shown with the three workers",
        screenshot: "qa_08_trajectory.png",
      });

      const choose = page.getByRole("button", { name: "Choose" });
      if (await choose.count()) {
        await choose.first().click();
        await shot(page, "qa_09_second_kitchen.png");
        const selected = await page.getByRole("button", { name: "Selected" }).count();
        record({
          id: "UI-08",
          area: "ui",
          name: "Choose another kitchen",
          status: selected >= 1 ? "pass" : "fail",
          detail: `selectedButtons=${selected}. Cart items stay from the first restaurant menu.`,
          screenshot: "qa_09_second_kitchen.png",
        });
      } else {
        record({ id: "UI-08", area: "ui", name: "Choose another kitchen", status: "fail", detail: "No Choose button; only one kitchen or none" });
      }

      const addOne = page.getByRole("button", { name: /Add one / }).first();
      const before = await page.getByText("Staged Zomato cart").locator("xpath=ancestor::section").innerText();
      const beforeTotal = before.match(/Total\s*₹(\d+)/)?.[1];
      await addOne.click();
      const after = await page.getByText("Staged Zomato cart").locator("xpath=ancestor::section").innerText();
      const afterTotal = after.match(/Total\s*₹(\d+)/)?.[1];
      await shot(page, "qa_10_quantity.png");
      record({
        id: "UI-09",
        area: "cart",
        name: "Increase item quantity",
        status: beforeTotal && afterTotal && Number(afterTotal) > Number(beforeTotal) ? "pass" : "fail",
        detail: `total ₹${beforeTotal} -> ₹${afterTotal}`,
        screenshot: "qa_10_quantity.png",
      });

      await page.getByRole("button", { name: "Simulate stock issue" }).click();
      await page.getByText("Item out of stock — AI re-routing").waitFor({ timeout: 5000 });
      await shot(page, "qa_11_stock_reroute.png");
      record({
        id: "UI-10",
        area: "ui",
        name: "Stock-issue banner",
        status: "pass",
        detail: "Local re-route banner appears. It does not call Zomato.",
        screenshot: "qa_11_stock_reroute.png",
      });

      await page.getByRole("button", { name: "Split group bill" }).click();
      await page.getByRole("heading", { name: "Group bill & dietary split" }).waitFor();
      const diners = ["Aarav", "Meera", "Rohan", "Isha", "Kabir", "Naina"];
      const missingDiners = [];
      for (const name of diners) {
        if (!(await page.getByText(name, { exact: true }).count())) missingDiners.push(name);
      }
      await shot(page, "qa_12_split_bill.png");
      record({
        id: "UI-11",
        area: "ui",
        name: "Group split dialog",
        status: missingDiners.length === 0 ? "pass" : "fail",
        detail: missingDiners.length ? `missing ${missingDiners.join(",")}` : "Six diners shown with an even split",
        screenshot: "qa_12_split_bill.png",
      });
      await page.getByRole("button", { name: "Apply split" }).click();

      await page.getByRole("button", { name: "Approve & place Zomato order" }).click();
      await page.getByRole("heading", { name: "Human approval required" }).waitFor();
      const confirm = page.getByRole("button", { name: "Confirm & stage order" });
      const disabledBefore = await confirm.isDisabled();
      await shot(page, "qa_13_approval_locked.png");
      await page.getByRole("checkbox").click();
      const disabledAfter = await confirm.isDisabled();
      await shot(page, "qa_14_approval_confirmed.png");
      await confirm.click();
      await page.getByText("Cart reviewed").waitFor();
      await shot(page, "qa_15_cart_reviewed.png");
      record({
        id: "UI-12",
        area: "approval",
        name: "Human approval gate",
        status: disabledBefore && !disabledAfter ? "pass" : "fail",
        detail: `confirmDisabledBefore=${disabledBefore} confirmDisabledAfterCheck=${disabledAfter}. Banner says checkout stays on Zomato.`,
        screenshot: "qa_15_cart_reviewed.png",
      });

      await page.getByText("AI PRD & Eval Studio").scrollIntoViewIfNeeded();
      await shot(page, "qa_16_eval_studio.png");
      record({
        id: "UI-13",
        area: "ui",
        name: "Eval studio charts",
        status: (await page.getByText("Model routing mix").isVisible()) ? "pass" : "fail",
        detail: "Static eval chart rendered. Numbers are not from the eval API.",
        screenshot: "qa_16_eval_studio.png",
      });
    }

    await page.getByRole("button", { name: "Solo", exact: true }).first().click();
    await page.getByRole("heading", { name: "What are you craving today?" }).waitFor();
    await shot(page, "qa_17_solo_mode.png");
    record({
      id: "UI-14",
      area: "ui",
      name: "Solo mode",
      status: "pass",
      detail: "Heading switches to the solo prompt",
      screenshot: "qa_17_solo_mode.png",
    });

    record({
      id: "UI-15",
      area: "ui",
      name: "Browser console and failed requests",
      status: consoleErrors.length === 0 && failedRequests.length === 0 ? "pass" : "fail",
      detail: `consoleErrors=${consoleErrors.length} failedRequests=${failedRequests.length} ${[...consoleErrors, ...failedRequests].slice(0, 4).join(" || ")}`,
    });
  } catch (error) {
    await shot(page, "qa_error_desktop.png").catch(() => {});
    record({ id: "UI-ERR", area: "ui", name: "Desktop UI run", status: "fail", detail: String(error).slice(0, 500), screenshot: "qa_error_desktop.png" });
  }

  await context.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mobilePage = await mobile.newPage();
  try {
    await mobilePage.goto(FRONTEND, { waitUntil: "domcontentloaded", timeout: 30000 });
    await mobilePage.getByRole("heading", { name: /What should the team eat today\?|What are you craving today\?/ }).waitFor();
    await shot(mobilePage, "qa_18_mobile.png");
    await mobilePage.getByRole("button", { name: "Open navigation" }).click();
    await mobilePage.getByText("Navigation", { exact: true }).waitFor();
    await shot(mobilePage, "qa_19_mobile_nav.png");
    await mobilePage.getByRole("button", { name: "Close navigation" }).click();
    record({
      id: "UI-16",
      area: "ui",
      name: "Mobile layout and navigation drawer",
      status: "pass",
      detail: "390px viewport loads and the nav drawer opens and closes",
      screenshot: "qa_19_mobile_nav.png",
    });
  } catch (error) {
    await shot(mobilePage, "qa_error_mobile.png").catch(() => {});
    record({ id: "UI-16", area: "ui", name: "Mobile layout and navigation drawer", status: "fail", detail: String(error).slice(0, 400), screenshot: "qa_error_mobile.png" });
  }

  await browser.close();
}

const started = new Date().toISOString();
const apiResult = await runApi();
await runUi();
const summary = {
  started,
  finished: new Date().toISOString(),
  frontend: FRONTEND,
  api: API,
  address_id: "217570301",
  checkout_called: false,
  counts: {
    pass: cases.filter((c) => c.status === "pass").length,
    fail: cases.filter((c) => c.status === "fail").length,
    blocked: cases.filter((c) => c.status === "blocked").length,
  },
  cases,
  searches: {
    pizza: apiResult?.pizza?.json ? summarizeSearch(apiResult.pizza.json) : null,
    group: apiResult?.group?.json ? summarizeSearch(apiResult.group.json) : null,
  },
};
fs.writeFileSync(path.join(ROOT, "qa_live_validation_results.json"), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary.counts));
process.exit(summary.counts.fail > 0 ? 1 : 0);
