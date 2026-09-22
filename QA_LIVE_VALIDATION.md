# FlavorPilot live integration validation

Date: 22 September 2026  
Environment: UI `http://localhost:8080`, API `http://localhost:8000`, official Zomato MCP `https://mcp-server.zomato.com/mcp` via `mcp-remote`  
Pinned address: `217570301` (Wanwadi)  
Runner: Playwright Chromium headless, plus direct API calls  
Order safety: `create_cart` and `checkout_cart` were not called

## Result

**22 passed, 3 blocked, 0 failed.**

Search, menus, and the main UI path are working against the live Zomato account. Trajectory history, the eval summary API, and server-side cart staging are blocked because Postgres is not running on `localhost:5432`.

| ID | Area | Case | Result |
| --- | --- | --- | --- |
| API-01 | API | Root reports operational, transport `stdio` | Pass |
| API-02 | API | `/health` returns HTTP 200 | Pass, with a defect |
| API-03 | MCP | Status connected, all 10 official tools listed | Pass |
| API-04 | Search | `pizza` returns 8 priced kitchens near the pinned address | Pass |
| API-05 | Search | Default group-lunch prompt returns 14 Pune-area kitchens | Pass |
| API-06 | Trajectory | Read trajectory for the pizza session | Blocked |
| API-07 | Evals | `GET /api/v1/evals/summary` | Blocked |
| API-08 | Cart API | `POST /api/v1/cart/build` (local DB only) | Blocked |
| API-09 | Safety | No live Zomato order | Pass |
| UI-01 | UI | Dashboard loads in group mode | Pass |
| UI-02 | UI | Hero shows saved-address copy and Build my order | Pass |
| UI-03 | UI | Metrics bar visible | Pass |
| UI-04 | UI | Header and sidebar show Zomato MCP Live | Pass |
| UI-05 | UI | Pizza search renders 8 live kitchen cards | Pass |
| UI-06 | UI | Cart fills with Domino's menu prices | Pass |
| UI-07 | UI | Trajectory shows Search finished | Pass |
| UI-08 | UI | Second kitchen can be selected | Pass |
| UI-09 | UI | Plus button updates the total ₹3844 → ₹4843 | Pass |
| UI-10 | UI | Stock-issue banner appears | Pass |
| UI-11 | UI | Split dialog lists all 6 diners at ₹807 | Pass |
| UI-12 | UI | Confirm stays disabled until the allergen checkbox | Pass |
| UI-13 | UI | Eval studio chart renders | Pass |
| UI-14 | UI | Solo mode changes the heading | Pass |
| UI-15 | UI | No console errors or failed requests on load | Pass |
| UI-16 | UI | 390px layout and navigation drawer | Pass |

Machine-readable detail is in `qa_live_validation_results.json`. Screenshots are in `screenshots/qa_*.png`.

## What the live search returned

Pizza (`API-04`, about 5.0 s) used address `217570301` and returned Domino's Pizza, Pizza Hut, MOJO Pizza, LeanCrust, Circle Of Crust, La Pino'z, Olio, and Largo Pizzeria. Distances were 1.0–2.8 km. Six menu items had prices above ₹0. No Goa, Ponda, Chicalim, or Madkai markers.

The default group prompt (`API-05`, about 10.7 s) — “Group lunch for 6 under ₹2,000 — 3 keto, 1 vegan, 2 high-protein, 30-min ETA” — returned 14 kitchens, including NFP Organic Veggies (Kondhwa), Sattvik High Protein (Bavdhan), WeFit, The Protein Palate (Hadapsar), and Mountain High (Wanowrie). Only 4 menu items came back, because the menu is loaded for the first restaurant only.

The UI pizza search (`UI-05`) showed the same Domino's-led list, with cart lines such as Big Big 6in1 Pizza - Non Veg ₹999, Big Big 6in1 Pizza - Veg ₹799, and Chicken Dominator Pizza ₹389. Mock kitchens (Green Theory, Fuel & Fire) were absent.

## Approval and checkout

The Approve button opens “Human approval required”. Confirm & stage order stays disabled until the peanut-allergy checkbox is checked. After confirm, the page shows “Cart reviewed” and states that FlavorPilot does not charge the card. That action is local UI state. It does not call Zomato `create_cart` or `checkout_cart`.

## Blocked by Postgres

The API log for API-06, API-07, and API-08 is `ConnectionRefusedError: [Errno 61] Connection refused` while SQLAlchemy connects to Postgres. The HTTP body is a generic 500 and does not say the database is down.

`/health` still returns `"database": "connected"` without opening a connection. That is a defect: the health check reports a database that is not running.

## Other product notes

These did not fail the cases above. They are gaps a follow-up should treat separately.

- Choosing another kitchen highlights that card and leaves the cart on the first restaurant’s menu.
- Delivery fee on these results is ₹0. Cards fall back to the text “Delivery fee from Zomato” when the fee is missing or zero.
- The even split rounds to ₹807. Six shares are ₹4842 against a ₹4843 total.
- Groundedness, allergen safety, cost per query, latency, macro bars, the eval chart, and the “Allergen verification passed” copy are static UI. They are not computed from this Zomato response or from `/api/v1/evals/summary`.
- “Simulate stock issue” is a local banner. It does not ask Zomato for a substitute.

## Screenshots

| File | What it shows |
| --- | --- |
| `screenshots/qa_01_dashboard_initial.png` | Initial group dashboard |
| `screenshots/qa_02_hero.png` | Hero and search |
| `screenshots/qa_03_header_metrics.png` | Header and metrics |
| `screenshots/qa_04_mcp_health.png` | MCP Live in the sidebar |
| `screenshots/qa_05_search_running.png` | Search in progress |
| `screenshots/qa_06_restaurant_cards.png` | 8 Zomato kitchens |
| `screenshots/qa_07_staged_cart.png` | Domino's cart |
| `screenshots/qa_08_trajectory.png` | Lead–worker trajectory |
| `screenshots/qa_09_second_kitchen.png` | Another kitchen selected |
| `screenshots/qa_10_quantity.png` | Quantity increased |
| `screenshots/qa_11_stock_reroute.png` | Stock-issue banner |
| `screenshots/qa_12_split_bill.png` | Group split dialog |
| `screenshots/qa_13_approval_locked.png` | Approval before the checkbox |
| `screenshots/qa_14_approval_confirmed.png` | Approval after the checkbox |
| `screenshots/qa_15_cart_reviewed.png` | Staged review |
| `screenshots/qa_16_eval_studio.png` | Eval chart |
| `screenshots/qa_17_solo_mode.png` | Solo heading |
| `screenshots/qa_18_mobile.png` | 390px layout |
| `screenshots/qa_19_mobile_nav.png` | Mobile drawer with MCP Live |
