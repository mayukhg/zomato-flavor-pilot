# Zomato FlavorPilot implementation plan

## Goal
Build the uploaded concept as a polished, interactive single-page dining operations workspace, and replace the repository README with the uploaded FlavorPilot README verbatim.

## Experience to build
- Create a dark, high-density “Crimson & Emerald Trust” interface using the specified slate, Zomato red, emerald, and supporting amber/cyan data accents.
- Add responsive navigation with FlavorPilot branding, Solo/Group mode switching, MCP status, workspace navigation, and a compact mobile layout.
- Make the main view immediately usable: natural-language order prompt, realistic execution status, restaurant recommendations, staged cart, dietary assignments, nutrition totals, and approval action.
- Use generated food photography for realistic restaurant and menu cards rather than remote placeholders.

## Interactive flows
- Prompt execution will animate a deterministic Lead–Worker workflow across dietary/allergen checks, promo optimization, ETA checks, and cart synthesis.
- Solo and Group modes will update visible copy, controls, and staged-order context without layout jumps.
- Restaurant/menu cards will support selecting alternatives and updating the staged cart presentation.
- The group split dialog will let users adjust diner preferences and allocations, then recalculate per-person totals.
- “Approve & Place Zomato Order” will always open a Human-in-the-Loop confirmation dialog with itemized costs, fees, discount, allergy verification, and a required confirmation checkbox before the final action is enabled.
- A controllable out-of-stock/re-routing state will show skeleton loading, a warning banner, and two compliant alternatives.

## Data and evaluation views
- Add persistent metric badges for Groundedness, Allergen Safety, cost per query, and P95 latency.
- Build Recharts visualizations for RAG quality, routing mix/cost savings, macro composition, and recent evaluation performance.
- Visualize the Lead–Worker trajectory as an accessible execution tree with stable dimensions and status transitions.
- Include the documented ₹240 promo result across `ZOMATO50`, `HEALTH20`, and `CBUSER`, plus the ₹382.5K/year routing-savings baseline.

## Content and safety
- Use realistic Indian restaurant names, dishes, prices, ratings, delivery times, macro values, dietary labels, and allergen evidence.
- Include the severe peanut-allergy example with a verified nut-free kitchen state and mandatory approval confirmation.
- Clearly present the UI as a staged prototype: no real payment or live Zomato order will be executed without an actual MCP service connection.

## Technical implementation
- Keep the experience at `/` as the requested SPA using the existing TanStack Start structure.
- Build focused React components for navigation, prompt/workflow, restaurant results, cart/macros, telemetry, and dialogs.
- Use existing Lucide, Radix/Shadcn-compatible primitives, Recharts, and Tailwind v4 semantic tokens; add only the minimum reusable UI primitives needed.
- Add route-specific title, description, Open Graph, and Twitter metadata.
- Replace `README.md` with the exact contents of the uploaded `README-FlavorPilot.md`.
- Verify compilation plus the primary desktop and mobile flows, including the approval gate and failure-state recovery.

## GitHub delivery
- After verification, prepare the completed project for a **public** repository named `zomato-flavor-pilot`.
- Use Lovable’s GitHub project sync flow to create and push the repository; if GitHub is not yet connected, the final handoff will identify the single authorization step required in the editor.
