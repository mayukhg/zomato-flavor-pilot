# Action Required: Connect to Real Zomato MCP Server

**Status**: FlavorPilot is currently using MOCK data. You need to take action to connect to real Zomato.

---

## Your Action Items

### Step 1: Get Zomato API Access 🔑

**What you need to do:**

1. **Go to Zomato Developers Portal**:
   - Visit: https://developers.zomato.com/
   - Create an account or log in

2. **Create an Application**:
   - Click "Generate API Key" or "Create Application"
   - Fill in application details:
     - Name: "FlavorPilot"
     - Description: "AI-powered dining assistant"
     - Purpose: "Restaurant search and menu data"

3. **Copy Your API Key**:
   - You'll get a key like: `zm_live_abc123xyz789def456...`
   - Save this securely (you'll need it in Step 3)

**⏱️ Time**: 10-15 minutes  
**Status**: ⏸️ **WAITING ON YOU**

---

### Step 2: Choose MCP Server Option

You have 2 options:

#### Option A: Ask Zomato for MCP Server (Preferred) ⭐

**What you need to do:**

1. **Contact Zomato**:
   - Email: api-support@zomato.com
   - Ask: "Do you provide a Model Context Protocol (MCP) server for API access?"
   - If yes, ask for:
     - Installation instructions
     - Package name (e.g., `@zomato/mcp-server`)
     - Or hosted endpoint URL

2. **If they say NO**, go to Option B below.

**⏱️ Time**: Wait for Zomato response (1-3 days)  
**Status**: ⏸️ **WAITING ON YOU**

---

#### Option B: Build Your Own MCP Server (DIY)

**What you need to do:**

1. **Create the MCP server project**:
   ```bash
   mkdir ~/zomato-mcp-server
   cd ~/zomato-mcp-server
   ```

2. **Copy the example code**:
   - Open: `/workspace/docs/EXAMPLE_MCP_SERVER.md`
   - Copy all the code from the `index.js` section
   - Save as `index.js` in your `zomato-mcp-server` folder

3. **Copy the package.json**:
   - From the same doc, copy `package.json`
   - Save in the same folder

4. **Install dependencies**:
   ```bash
   npm install
   ```

5. **Create .env file**:
   ```bash
   echo "ZOMATO_API_KEY=your_api_key_from_step1" > .env
   ```

6. **Test it works**:
   ```bash
   chmod +x index.js
   node index.js
   ```
   
   Should see: `Zomato MCP server running on stdio`

**⏱️ Time**: 30 minutes  
**Status**: ⏸️ **WAITING ON YOU**

---

### Step 3: Configure FlavorPilot

**What you need to do:**

1. **Create/edit `.env` file** in `/workspace`:
   ```bash
   cd /workspace
   cp .env.example .env  # if .env doesn't exist
   nano .env  # or use any text editor
   ```

2. **Update these lines**:
   ```env
   # IMPORTANT: Change this to false!
   USE_MOCK_MCP=false
   
   # Choose your transport
   ZOMATO_MCP_TRANSPORT=stdio
   
   # For Option A (official server):
   ZOMATO_MCP_STDIO_CMD=npx -y @zomato/mcp-server
   
   # For Option B (your own server):
   ZOMATO_MCP_STDIO_CMD=/full/path/to/zomato-mcp-server/index.js
   # Example: /Users/yourname/zomato-mcp-server/index.js
   
   # Your API key from Step 1
   ZOMATO_API_KEY=zm_live_abc123xyz789def456
   ```

3. **Save and close** the file

**⏱️ Time**: 2 minutes  
**Status**: ⏸️ **WAITING ON YOU**

---

### Step 4: Restart FlavorPilot

**What you need to do:**

```bash
cd /workspace
./stop.sh
./start.sh
```

**⏱️ Time**: 1 minute  
**Status**: ⏸️ **WAITING ON YOU**

---

### Step 5: Verify It's Working ✅

**What you need to do:**

1. **Check startup logs**:
   Look for:
   ```
   ✓ Connected to Zomato MCP server (stdio)
   ✓ 5/5 tools available
   ```
   
   ❌ If you see: `Using MOCK Zomato MCP client` → You missed something

2. **Test in browser**:
   - Open: http://localhost:5173
   - Search: "pizza in Bangalore"
   - **Expected**: Real restaurant names (not "Green Theory Kitchen")

3. **Test via API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/search \
     -H "Content-Type: application/json" \
     -d '{"query": "pizza", "location": "Bangalore"}'
   ```
   
   **Expected**: JSON with real Zomato restaurants

**⏱️ Time**: 5 minutes  
**Status**: ⏸️ **WAITING ON YOU**

---

## Summary Checklist

- [ ] **Step 1**: Get Zomato API key from developers.zomato.com
- [ ] **Step 2A**: Ask Zomato for MCP server, OR
- [ ] **Step 2B**: Build MCP server using example code
- [ ] **Step 3**: Update `/workspace/.env` with credentials
- [ ] **Step 4**: Restart FlavorPilot (`./stop.sh && ./start.sh`)
- [ ] **Step 5**: Verify real data is showing

---

## What I've Already Done ✅

You don't need to change any code! I've already:

- ✅ Added `USE_MOCK_MCP` configuration flag
- ✅ Updated orchestrator to conditionally use real/mock client
- ✅ Created comprehensive connection documentation
- ✅ Provided example MCP server implementation
- ✅ Updated `.env.example` with all required fields

**You only need to provide credentials and choose an MCP server.**

---

## If You Get Stuck

### Issue: "Can't get Zomato API key"

**Solution**: Zomato's public API might require approval. Alternatives:
1. Contact Zomato support directly
2. Check if you need a business account
3. For now, continue using mock data (it's fine for development)

### Issue: "Don't know how to build MCP server"

**Solution**: 
1. Read `/workspace/docs/EXAMPLE_MCP_SERVER.md` (complete code provided)
2. Or wait for Zomato to provide official MCP server
3. Or use mock data until you're ready

### Issue: "MCP server crashes when I run it"

**Solution**:
```bash
# Check logs
node /path/to/zomato-mcp-server/index.js

# Common issue: Missing .env file
echo "ZOMATO_API_KEY=your_key" > .env

# Common issue: Missing dependencies
npm install
```

---

## Timeline Estimate

**If everything goes smoothly:**
- Zomato API key: 15 minutes
- Build MCP server: 30 minutes  
- Configure FlavorPilot: 5 minutes
- **Total**: ~1 hour

**Realistic timeline:**
- Waiting for Zomato approval: 1-3 days
- Building and testing MCP server: 2-4 hours
- **Total**: 1-3 days

---

## Current Status

```
┌─────────────────────────────────────────┐
│         FlavorPilot Status              │
├─────────────────────────────────────────┤
│ Code: ✅ Ready for real MCP             │
│ Docs: ✅ Complete                        │
│ MCP Client: ✅ Implemented               │
│ Configuration: ⏸️  Needs credentials    │
│ Zomato API Key: ⏸️  Needs your action  │
│ MCP Server: ⏸️  Needs your choice      │
├─────────────────────────────────────────┤
│ Next Action: YOU                        │
│ Step 1: Get Zomato API key              │
└─────────────────────────────────────────┘
```

---

## Questions?

**Contact:**
- For Zomato API: api-support@zomato.com
- For MCP Protocol: https://modelcontextprotocol.io/
- For FlavorPilot code: GitHub issues

**Documentation:**
- Full guide: `/workspace/docs/ZOMATO_MCP_CONNECTION.md`
- Example server: `/workspace/docs/EXAMPLE_MCP_SERVER.md`
- Architecture: `/workspace/docs/architecture.md`

---

**Ready to start? Begin with Step 1! 🚀**
