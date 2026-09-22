import { useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, ArrowRight, Bot, Check, CheckCircle2, ChevronRight,
  CircleDollarSign, Clock3, Cpu, Gauge, Leaf, Menu, Minus, Plus, Search,
  ShieldCheck, Sparkles, Split, Star, Users, UtensilsCrossed, X,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import feastImage from "@/assets/flavorpilot-feast.jpg";
import { api, MenuItemResult, RestaurantResult } from "@/services/api";

type Mode = "group" | "solo";
type WorkflowStatus = "idle" | "running" | "done";

type CartItem = {
  id: string;
  name: string;
  detail: string;
  price: number;
  qty: number;
  tag: string;
};

const evaluationData = [
  { run: "08:10", grounded: 98.2, safety: 100 },
  { run: "08:30", grounded: 98.7, safety: 100 },
  { run: "09:05", grounded: 99.1, safety: 100 },
  { run: "09:40", grounded: 98.9, safety: 100 },
  { run: "10:15", grounded: 99.4, safety: 100 },
  { run: "Now", grounded: 99.2, safety: 100 },
];

const routingData = [
  { name: "Smart Intern", value: 85, fill: "var(--chart-2)" },
  { name: "PhD Reasoner", value: 15, fill: "var(--chart-1)" },
];

const workflowSteps = [
  { icon: ShieldCheck, worker: "Worker 1", title: "Dietary & allergens", detail: "Checks the live menu" },
  { icon: CircleDollarSign, worker: "Worker 2", title: "Price & promos", detail: "Coupon stays on Zomato checkout" },
  { icon: Clock3, worker: "Worker 3", title: "Delivery & ETA", detail: "Uses the restaurant ETA" },
];

const people = [
  { name: "Aarav", preference: "Keto" },
  { name: "Meera", preference: "Vegan • Peanut allergy" },
  { name: "Rohan", preference: "High protein" },
  { name: "Isha", preference: "Keto" },
  { name: "Kabir", preference: "High protein" },
  { name: "Naina", preference: "High protein" },
];

function menuToCart(items: MenuItemResult[]): CartItem[] {
  return items.slice(0, 6).map((item) => ({
    id: item.item_id || item.name,
    name: item.name,
    detail: item.detail || "From the Zomato menu",
    price: Math.round(item.price_inr),
    qty: 1,
    tag: item.tags[0] || "Zomato",
  }));
}

function Metric({ icon: Icon, label, value, tone = "default" }: { icon: typeof Activity; label: string; value: string; tone?: "default" | "success" }) {
  return (
    <div className="flex min-w-[138px] items-center gap-3 border-r border-border px-4 last:border-0">
      <div className={tone === "success" ? "text-success" : "text-primary"}><Icon className="size-4" /></div>
      <div>
        <p className="text-[10px] font-bold uppercase text-muted-foreground">{label}</p>
        <p className="font-display text-sm font-semibold text-foreground">{value}</p>
      </div>
    </div>
  );
}

function SectionTitle({ eyebrow, title, action }: { eyebrow: string; title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <p className="mb-1 text-[10px] font-bold uppercase text-primary">{eyebrow}</p>
        <h2 className="font-display text-lg font-semibold text-foreground">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function FlavorPilotApp() {
  const [mode, setMode] = useState<Mode>("group");
  const [mobileNav, setMobileNav] = useState(false);
  const [prompt, setPrompt] = useState("Group lunch for 6 under ₹2,000 — 3 keto, 1 vegan, 2 high-protein, 30-min ETA");
  const [workflow, setWorkflow] = useState<WorkflowStatus>("idle");
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [splitOpen, setSplitOpen] = useState(false);
  const [allergenConfirmed, setAllergenConfirmed] = useState(false);
  const [orderStaged, setOrderStaged] = useState(false);
  const [rerouting, setRerouting] = useState(false);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [restaurants, setRestaurants] = useState<RestaurantResult[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState(0);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [mcpStatus, setMcpStatus] = useState<"checking" | "offline" | "live">("checking");

  useEffect(() => {
    let cancelled = false;
    api.mcpStatus()
      .then((status) => {
        if (!cancelled) setMcpStatus(status.connected ? "live" : "offline");
      })
      .catch(() => {
        if (!cancelled) setMcpStatus("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!rerouting) return;
    const timer = window.setTimeout(() => setRerouting(false), 1800);
    return () => window.clearTimeout(timer);
  }, [rerouting]);

  const subtotal = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.qty, 0), [cart]);
  const activeRestaurant = restaurants[selectedRestaurant] ?? restaurants[0];
  const fees = activeRestaurant ? Math.round(activeRestaurant.delivery_fee_inr) : 0;
  const total = subtotal + fees;
  const dinerShare = people.length ? Math.round(total / people.length) : 0;

  const updateQty = (id: string, delta: number) => {
    setCart((items) => items.map((item) => item.id === id ? { ...item, qty: Math.max(1, item.qty + delta) } : item));
  };

  const startSearch = async () => {
    setWorkflow("running");
    setOrderStaged(false);
    setSearchError(null);
    try {
      const result = await api.searchRestaurants({
        query: prompt,
        location: "",
        group_size: mode === "group" ? people.length : 1,
        dietary_constraints: mode === "group" ? ["keto", "vegan", "high protein"] : undefined,
      });
      setRestaurants(result.restaurants);
      setSelectedRestaurant(0);
      setCart(menuToCart(result.menu_items ?? []));
      setMcpStatus("live");
      setWorkflow("done");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Zomato MCP search failed";
      setSearchError(message === "Failed to fetch" ? "FlavorPilot API is not running at http://localhost:8000." : message);
      setWorkflow("idle");
    }
  };

  const placeOrder = () => {
    setOrderStaged(true);
    setApprovalOpen(false);
    setAllergenConfirmed(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex h-16 items-center justify-between px-4 lg:px-7">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Menu /></Button>
            <div className="grid size-9 place-items-center rounded-md bg-primary font-display text-xl font-bold text-primary-foreground">Z</div>
            <div>
              <p className="font-display text-base font-bold">FlavorPilot</p>
              <p className="text-[9px] font-bold uppercase text-muted-foreground">Personal dining resident</p>
            </div>
          </div>
          <div className="hidden items-center rounded-md border border-border bg-panel p-1 md:flex">
            <Button size="sm" variant={mode === "solo" ? "secondary" : "ghost"} onClick={() => setMode("solo")}><UtensilsCrossed /> Solo</Button>
            <Button size="sm" variant={mode === "group" ? "default" : "ghost"} onClick={() => setMode("group")}><Users /> Group concierge</Button>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 text-xs sm:flex"><span className={`size-2 rounded-full ${mcpStatus === "live" ? "animate-pulse-soft bg-success" : mcpStatus === "checking" ? "animate-pulse-soft bg-warning" : "bg-muted-foreground"}`} /><span className="text-muted-foreground">Zomato MCP</span><strong>{mcpStatus === "live" ? "Live" : mcpStatus === "checking" ? "Connecting" : "Not connected"}</strong></div>
            <div className="grid size-9 place-items-center rounded-full border border-border bg-secondary text-xs font-bold">AK</div>
          </div>
        </div>
      </header>

      <div className="flex">
        <aside className={`${mobileNav ? "fixed inset-y-0 left-0 z-50 flex" : "hidden"} w-64 flex-col border-r border-border bg-panel px-4 py-5 lg:sticky lg:top-16 lg:flex lg:h-[calc(100vh-4rem)]`}>
          <div className="mb-7 flex items-center justify-between lg:hidden"><span className="font-display font-semibold">Navigation</span><Button variant="ghost" size="icon" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X /></Button></div>
          <p className="px-3 text-[10px] font-bold uppercase text-muted-foreground">Workspace</p>
          <nav className="mt-3 space-y-1">
            <Button variant="secondary" className="w-full justify-start"><Sparkles className="text-primary" /> Resident workspace</Button>
            <Button variant="ghost" className="w-full justify-start text-muted-foreground"><Activity /> AI PRD & Eval Studio</Button>
            <Button variant="ghost" className="w-full justify-start text-muted-foreground"><Cpu /> Model router</Button>
          </nav>
          <div className="mt-7 border-t border-border pt-6">
            <p className="px-3 text-[10px] font-bold uppercase text-muted-foreground">Active mode</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Button size="sm" variant={mode === "solo" ? "default" : "outline"} onClick={() => setMode("solo")}>Solo</Button>
              <Button size="sm" variant={mode === "group" ? "default" : "outline"} onClick={() => setMode("group")}>Group</Button>
            </div>
          </div>
          <div className="mt-auto rounded-md border border-border bg-background p-4">
            <div className="flex items-center justify-between"><span className="text-xs font-semibold">MCP health</span><span className={`rounded-sm px-2 py-1 text-[10px] font-bold ${mcpStatus === "live" ? "bg-success-soft text-success" : "bg-secondary text-muted-foreground"}`}>{mcpStatus === "live" ? "Live" : mcpStatus === "checking" ? "Checking" : "Offline"}</span></div>
            <div className="mt-4 space-y-2 text-[11px] text-muted-foreground">
              <p className="flex justify-between gap-3"><span>Server</span><span className="truncate text-foreground">mcp-server.zomato.com</span></p>
              <p className="flex justify-between"><span>Transport</span><span className="text-foreground">mcp-remote</span></p>
            </div>
          </div>
        </aside>
        {mobileNav && <button className="fixed inset-0 z-40 bg-background/70 lg:hidden" aria-label="Close navigation overlay" onClick={() => setMobileNav(false)} />}

        <main className="min-w-0 flex-1">
          <div className="overflow-x-auto border-b border-border bg-panel py-3">
            <div className="flex min-w-max px-3 lg:px-6">
              <Metric icon={ShieldCheck} label="Groundedness" value="99.2%" tone="success" />
              <Metric icon={CheckCircle2} label="Allergen safety" value="100%" tone="success" />
              <Metric icon={CircleDollarSign} label="Cost / query" value="$0.0042" />
              <Metric icon={Gauge} label="Latency P95" value="684 ms" />
            </div>
          </div>

          <div className="mx-auto max-w-[1600px] p-4 lg:p-6">
            <section className="relative overflow-hidden rounded-lg border border-border bg-panel-strong">
              <img src={feastImage} width={1200} height={800} alt="A high-protein Indian dining spread" className="absolute inset-0 h-full w-full object-cover opacity-25" />
              <div className="absolute inset-0 bg-background/65" />
              <div className="relative max-w-4xl p-5 md:p-8">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="rounded-sm bg-primary px-2 py-1 text-[10px] font-bold uppercase text-primary-foreground">Resident online</span>
                  <span className="text-xs text-muted-foreground">Saved Zomato address</span>
                </div>
                <h1 className="font-display text-2xl font-bold md:text-4xl">{mode === "group" ? "What should the team eat today?" : "What are you craving today?"}</h1>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">I’ll balance taste, nutrition, budget, delivery time, and verified dietary constraints.</p>
                <div className="mt-6 flex flex-col gap-2 rounded-md border border-border bg-background/90 p-2 sm:flex-row">
                  <div className="flex min-w-0 flex-1 items-center gap-3 px-2"><Search className="size-5 shrink-0 text-primary" /><input value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="Describe your order" className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground" /></div>
                  <Button size="lg" className="shrink-0" onClick={startSearch} disabled={workflow === "running"}>{workflow === "running" ? <><span className="size-2 animate-pulse-soft rounded-full bg-primary-foreground" />Reasoning…</> : <>Build my order <ArrowRight /></>}</Button>
                </div>
              </div>
            </section>

            {searchError && <div className="mt-4 flex items-start gap-3 rounded-md border border-warning bg-warning-soft p-4 text-sm"><AlertTriangle className="mt-0.5 size-5 shrink-0 text-warning" /><div><p className="font-semibold text-warning">Zomato MCP did not return results</p><p className="mt-1 text-muted-foreground">{searchError}</p>{/auth|sign-?in|401|token|oauth|browser/i.test(searchError) && <p className="mt-1 text-muted-foreground">The first search opens a Zomato sign-in in your browser. Approve it, then search again.</p>}</div></div>}
            {orderStaged && <div className="mt-4 flex items-start gap-3 rounded-md border border-success bg-success-soft p-4 text-sm"><CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" /><div><p className="font-semibold text-success">Cart reviewed</p><p className="mt-1 text-muted-foreground">Items came from the Zomato menu. FlavorPilot does not charge the card; checkout stays on Zomato.</p></div></div>}

            <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(350px,.65fr)]">
              <div className="space-y-6">
                <section className="rounded-lg border border-border bg-panel p-5">
                  <SectionTitle eyebrow="Live orchestration" title="Lead–Worker trajectory" action={<span className="flex items-center gap-2 text-xs text-muted-foreground"><span className={`size-2 rounded-full ${workflow === "running" ? "animate-pulse-soft bg-warning" : workflow === "done" ? "bg-success" : "bg-muted-foreground"}`} />{workflow === "running" ? "Running" : workflow === "done" ? "Search finished" : "Waiting for a search"}</span>} />
                  <div className="mt-6 overflow-x-auto pb-2">
                    <div className="min-w-[650px]">
                      <div className="mx-auto flex w-fit items-center gap-3 rounded-md border border-primary bg-primary/10 px-4 py-3"><Bot className="size-5 text-primary" /><div><p className="text-xs font-bold">Lead Resident</p><p className="text-[10px] text-muted-foreground">6-person constraint synthesis</p></div></div>
                      <div className="mx-auto h-6 w-px bg-border" />
                      <div className="grid grid-cols-3 gap-3 border-t border-border pt-5">
                        {workflowSteps.map((step) => {
                          const StepIcon = step.icon;
                          return (
                          <div key={step.worker} className="relative rounded-md border border-border bg-background p-4 before:absolute before:-top-5 before:left-1/2 before:h-5 before:w-px before:bg-border">
                            <div className="flex items-center gap-2"><div className="grid size-8 place-items-center rounded-sm bg-success-soft text-success"><StepIcon className="size-4" /></div><div><p className="text-[10px] font-bold uppercase text-muted-foreground">{step.worker}</p><p className="text-xs font-semibold">{step.title}</p></div></div>
                            <div className="mt-3 flex items-center gap-2 text-[11px] text-success"><CheckCircle2 className="size-3.5" />{workflow === "running" ? "Checking live data…" : step.detail}</div>
                          </div>
                        )})}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md bg-success-soft px-4 py-3 text-xs"><Sparkles className="size-4 text-success" /><strong className="text-success">Checkout:</strong><span className="text-muted-foreground">Coupons are applied on the Zomato cart, not guessed here.</span></div>
                </section>

                <section>
                  <SectionTitle eyebrow="Live Zomato proposals" title={restaurants.length ? `${restaurants.length} kitchens from Zomato` : "Search to load live kitchens"} action={<Button variant="outline" size="sm" onClick={() => setRerouting(true)} disabled={!restaurants.length}><Activity /> Simulate stock issue</Button>} />
                  {rerouting && <div className="mt-4 flex items-start gap-3 rounded-md border border-warning bg-warning-soft p-4"><AlertTriangle className="size-5 shrink-0 text-warning" /><div><p className="text-sm font-semibold text-warning">Item out of stock — AI re-routing</p><p className="text-xs text-muted-foreground">Checking two alternatives against dietary rules, price, and ETA.</p></div></div>}
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    {restaurants.length === 0 && <p className="text-sm text-muted-foreground md:col-span-2">{workflow === "done" ? "Zomato returned no kitchens for that search." : "Run a search to load restaurants from the Zomato MCP server."}</p>}
                    {restaurants.map((restaurant, index) => (
                      <article key={restaurant.restaurant_id} className={`overflow-hidden rounded-lg border bg-panel transition-colors ${selectedRestaurant === index ? "border-primary" : "border-border"}`}>
                        <div className="relative h-40 overflow-hidden bg-muted">
                          {rerouting ? <div className="h-full w-full animate-pulse bg-secondary" /> : <img src={restaurant.image_url || feastImage} width={928} height={720} loading="lazy" alt={`${restaurant.name}`} className="h-full w-full object-cover transition-transform duration-500 hover:scale-105" />}
                          <span className="absolute left-3 top-3 rounded-sm bg-success px-2 py-1 text-[10px] font-bold text-primary-foreground"><ShieldCheck className="mr-1 inline size-3" />{restaurant.tags[0] || "Zomato"}</span>
                        </div>
                        <div className="p-4">
                          <div className="flex items-start justify-between gap-3"><div><h3 className="font-display font-semibold">{restaurant.name}</h3><p className="mt-1 text-xs text-muted-foreground">{restaurant.cuisine}{restaurant.location ? ` • ${restaurant.location}` : ""}</p></div><span className="flex items-center gap-1 rounded-sm bg-success-soft px-2 py-1 text-xs font-bold text-success"><Star className="size-3 fill-current" />{restaurant.rating.toFixed(1)}</span></div>
                          <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground"><span><Clock3 className="mr-1 inline size-3.5" />{restaurant.eta_mins} min</span><span>{restaurant.delivery_fee_inr ? `₹${Math.round(restaurant.delivery_fee_inr)} delivery` : "Delivery fee from Zomato"}</span></div>
                          <div className="mt-3 flex items-center justify-between border-t border-border pt-3"><span className="text-[11px] text-success">{restaurant.restaurant_id}</span><Button size="sm" variant={selectedRestaurant === index ? "default" : "outline"} onClick={() => setSelectedRestaurant(index)}>{selectedRestaurant === index ? <><Check />Selected</> : <>Choose<ChevronRight /></>}</Button></div>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-panel p-5">
                  <SectionTitle eyebrow="AI PRD & Eval Studio" title="Quality is a release gate, not a vibe" />
                  <div className="mt-5 grid gap-5 lg:grid-cols-[1.4fr_.6fr]">
                    <div className="h-64 rounded-md bg-background p-3">
                      <ResponsiveContainer width="100%" height="100%"><AreaChart data={evaluationData} margin={{ top: 12, right: 10, left: -18, bottom: 0 }}><defs><linearGradient id="groundedFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.3}/><stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="run" tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} axisLine={false} tickLine={false}/><YAxis domain={[96, 101]} tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}/><Area type="monotone" dataKey="grounded" stroke="var(--chart-2)" fill="url(#groundedFill)" strokeWidth={2}/><Area type="monotone" dataKey="safety" stroke="var(--chart-1)" fill="transparent" strokeWidth={2}/></AreaChart></ResponsiveContainer>
                    </div>
                    <div className="rounded-md bg-background p-4">
                      <p className="text-xs font-semibold">Model routing mix</p>
                      <div className="h-36"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={routingData} innerRadius={38} outerRadius={58} paddingAngle={3} dataKey="value">{routingData.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}</Pie><Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}/></PieChart></ResponsiveContainer></div>
                      <div className="space-y-2 text-[11px]">{routingData.map((entry) => <div key={entry.name} className="flex justify-between"><span className="text-muted-foreground">{entry.name}</span><strong>{entry.value}%</strong></div>)}</div>
                      <div className="mt-4 border-t border-border pt-3"><p className="text-[10px] uppercase text-muted-foreground">Projected annual savings</p><p className="font-display text-xl font-bold text-success">$382.5K</p></div>
                    </div>
                  </div>
                </section>
              </div>

              <aside className="space-y-6">
                <section className="rounded-lg border border-border bg-panel p-5 xl:sticky xl:top-24">
                  <SectionTitle eyebrow="Staged Zomato cart" title={activeRestaurant?.name ?? "Selected kitchen"} action={<span className={`rounded-sm px-2 py-1 text-[10px] font-bold ${mcpStatus === "live" ? "bg-success-soft text-success" : "bg-secondary text-muted-foreground"}`}>{mcpStatus === "live" ? "From Zomato" : "No search yet"}</span>} />
                  <div className="mt-5 space-y-4">
                    {cart.length === 0 && <p className="text-sm text-muted-foreground">Menu items from the selected Zomato restaurant show up here after a search.</p>}
                    {cart.map((item) => <div key={item.id} className="border-b border-border pb-4 last:border-0"><div className="flex justify-between gap-3"><div className="min-w-0"><div className="mb-1 flex items-center gap-2"><span className="size-2 shrink-0 rounded-sm border border-success" /><p className="truncate text-sm font-semibold">{item.name}</p></div><p className="text-[11px] text-muted-foreground">{item.detail}</p><span className="mt-2 inline-block rounded-sm bg-success-soft px-2 py-0.5 text-[9px] font-bold text-success">{item.tag}</span></div><div className="text-right"><p className="text-sm font-bold">₹{item.price * item.qty}</p><div className="mt-2 flex items-center rounded-sm border border-border"><Button size="icon" variant="ghost" className="size-7" aria-label={`Remove one ${item.name}`} onClick={() => updateQty(item.id, -1)}><Minus /></Button><span className="w-6 text-center text-xs">{item.qty}</span><Button size="icon" variant="ghost" className="size-7" aria-label={`Add one ${item.name}`} onClick={() => updateQty(item.id, 1)}><Plus /></Button></div></div></div></div>)}
                  </div>
                  <div className="mt-4 rounded-md bg-background p-4">
                    <div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold">Group macro profile</span><span className="text-[10px] text-success">On target</span></div>
                    <div className="space-y-3">
                      {[ ["Protein", 76, "258g"], ["Carbs", 48, "164g"], ["Fat", 61, "92g"] ].map(([label, value, amount]) => <div key={label as string}><div className="mb-1 flex justify-between text-[10px]"><span className="text-muted-foreground">{label as string}</span><span>{amount as string}</span></div><Progress value={value as number} className="h-1.5" /></div>)}
                    </div>
                  </div>
                  <div className="mt-4 space-y-2 text-xs"><div className="flex justify-between text-muted-foreground"><span>Subtotal</span><span>₹{subtotal}</span></div><div className="flex justify-between text-muted-foreground"><span>Delivery fee</span><span>₹{fees}</span></div><div className="flex justify-between border-t border-border pt-3 font-display text-base font-bold"><span>Total</span><span>₹{total}</span></div></div>
                  <div className="mt-4 grid grid-cols-[auto_1fr] gap-2"><Button variant="outline" size="icon" aria-label="Split group bill" onClick={() => setSplitOpen(true)}><Split /></Button><Button size="lg" onClick={() => setApprovalOpen(true)}><ShieldCheck /> Approve & place Zomato order</Button></div>
                  <p className="mt-3 text-center text-[10px] text-muted-foreground">Human approval required • No automatic payment</p>
                </section>
              </aside>
            </div>
          </div>
        </main>
      </div>

      <Dialog open={approvalOpen} onOpenChange={setApprovalOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto border-border bg-panel sm:max-w-xl">
          <DialogHeader><div className="mb-2 grid size-11 place-items-center rounded-md bg-primary/10 text-primary"><ShieldCheck /></div><DialogTitle className="font-display text-xl">Human approval required</DialogTitle><DialogDescription>Verify every item, price, and allergen safeguard before staging this order.</DialogDescription></DialogHeader>
          <div className="space-y-3 rounded-md border border-border bg-background p-4">{cart.map((item) => <div key={item.id} className="flex justify-between text-sm"><span>{item.qty}× {item.name}</span><strong>₹{item.price * item.qty}</strong></div>)}<div className="flex justify-between border-t border-border pt-3 text-sm text-muted-foreground"><span>Delivery fee</span><span>₹{fees}</span></div><div className="flex justify-between border-t border-border pt-3 font-display text-lg font-bold"><span>Payable total</span><span>₹{total}</span></div></div>
          <div className="rounded-md border border-success bg-success-soft p-4"><div className="flex gap-3"><ShieldCheck className="size-5 shrink-0 text-success" /><div><p className="text-sm font-semibold text-success">Allergen verification passed</p><p className="mt-1 text-xs text-muted-foreground">Meera’s meal is assigned to a dedicated nut-free preparation zone. Restaurant evidence checked moments ago.</p></div></div></div>
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-4"><Checkbox checked={allergenConfirmed} onCheckedChange={(value) => setAllergenConfirmed(value === true)} /><span className="text-xs leading-5">I reviewed the itemized cart and confirm the severe peanut-allergy safeguard for this order.</span></label>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Button variant="outline" onClick={() => setApprovalOpen(false)}>Return to cart</Button><Button disabled={!allergenConfirmed} onClick={placeOrder}><CheckCircle2 /> Confirm & stage order</Button></div>
        </DialogContent>
      </Dialog>

      <Dialog open={splitOpen} onOpenChange={setSplitOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto border-border bg-panel sm:max-w-2xl">
          <DialogHeader><DialogTitle className="font-display text-xl">Group bill & dietary split</DialogTitle><DialogDescription>Each diner’s share is an even split of the live Zomato subtotal and delivery fee.</DialogDescription></DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">{people.map((person, index) => <div key={person.name} className="flex items-center justify-between rounded-md border border-border bg-background p-3"><div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-full bg-secondary text-xs font-bold">{person.name.slice(0, 2)}</div><div><p className="text-sm font-semibold">{person.name}</p><p className={`text-[10px] ${index === 1 ? "text-warning" : "text-muted-foreground"}`}>{person.preference}</p></div></div><strong className="text-sm">₹{dinerShare}</strong></div>)}</div>
          <div className="rounded-md bg-background p-4"><div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">Allocated to {people.length} diners</span><strong>₹{total}</strong></div><div className="mt-3 h-32"><ResponsiveContainer width="100%" height="100%"><BarChart data={people.map((person) => ({ ...person, amount: dinerShare }))}><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="name" tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} axisLine={false} tickLine={false}/><YAxis hide/><Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}/><Bar dataKey="amount" fill="var(--chart-1)" radius={[3, 3, 0, 0]}/></BarChart></ResponsiveContainer></div></div>
          <Button onClick={() => setSplitOpen(false)}>Apply split</Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
