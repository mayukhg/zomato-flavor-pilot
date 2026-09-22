import { createFileRoute } from "@tanstack/react-router";
import { FlavorPilotApp } from "@/components/flavorpilot/flavor-pilot-app";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Zomato FlavorPilot — Personal & Group Dining Resident" },
      { name: "description", content: "Plan constraint-aware personal and group meals with nutrition, allergen, promo, and delivery intelligence." },
      { property: "og:title", content: "Zomato FlavorPilot — Personal & Group Dining Resident" },
      { property: "og:description", content: "An AI dining workspace for safer, faster, nutrition-aware Zomato group orders." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return <FlavorPilotApp />;
}
