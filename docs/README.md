# FlavorPilot Documentation

Comprehensive documentation for the FlavorPilot AI-powered autonomous dining resident system.

---

## 📚 Documentation Index

### Getting Started

- **[How to Use](HOW_TO_USE.md)** - Complete user guide for installation, configuration, and daily usage
  - Quick start instructions
  - Solo and group mode usage
  - Common use cases with examples
  - Troubleshooting guide

### Technical Documentation

- **[Architecture](architecture.md)** - System architecture and design principles
  - Component architecture
  - Technology stack
  - Data flow diagrams
  - Scalability and security considerations

- **[Workflow](workflow.md)** - End-to-end execution flow with detailed diagrams
  - Stage-by-stage breakdown
  - Lead-Worker orchestration
  - MCP tool interactions
  - Quality gates and evaluation pipeline

- **[Development Guide](development.md)** - Setup and contribution guidelines
  - Development environment setup
  - Project structure
  - Testing strategies
  - Code style and best practices

---

## 🚀 Quick Links

**For Users:**
- Start here: [How to Use](HOW_TO_USE.md)
- Need help? See [Troubleshooting](HOW_TO_USE.md#troubleshooting)

**For Developers:**
- Setup environment: [Development Guide](development.md#development-setup)
- Understand architecture: [Architecture](architecture.md)
- See execution flow: [Workflow](workflow.md)

**For Contributors:**
- Contributing guidelines: [Development Guide](development.md#contributing)
- Code style: [Development Guide](development.md#code-style)
- Pull request process: [Development Guide](development.md#pull-request-checklist)

---

## 📖 Document Overview

### HOW_TO_USE.md (13 KB)

**Audience**: End users, QA testers

**Contents**:
- Platform-specific startup commands (bash/PowerShell)
- Solo and group mode usage guides
- Step-by-step use cases with screenshots
- UI component explanations
- API access examples
- Comprehensive troubleshooting section

**Use when**: You want to know how to use FlavorPilot as an end user.

---

### architecture.md (22 KB)

**Audience**: Technical leads, architects, senior developers

**Contents**:
- High-level system architecture
- Architecture principles (MCP-first, Lead-Worker, Model Router)
- Component diagrams (Frontend, Backend, Database)
- Technology stack breakdown
- Production deployment recommendations
- Security and monitoring strategies

**Use when**: You need to understand how FlavorPilot is built at a system level.

---

### workflow.md (15 KB)

**Audience**: Developers, QA engineers, AI/ML engineers

**Contents**:
- End-to-end flow with Mermaid diagram
- 14-stage pipeline breakdown (from user query to order placement)
- MCP tool interaction details
- Worker agent specializations
- Quality gate evaluation metrics
- Performance benchmarks

**Use when**: You want to trace how a user query flows through the system.

---

### development.md (17 KB)

**Audience**: Developers, contributors

**Contents**:
- Prerequisites installation (Python, Node.js, PostgreSQL, Git)
- Repository setup and project structure
- Development workflow and common tasks
- Testing strategies (backend, frontend, integration, UI)
- Code style guides (Python PEP 8, TypeScript Airbnb)
- Common development tasks with examples
- Contributing guidelines

**Use when**: You're setting up a development environment or contributing code.

---

## 🔗 Related Documentation

**In Project Root:**
- `README.md` - Project overview and quick start
- `IMPLEMENTATION_SUMMARY.md` - Technical deep dive
- `SETUP_GUIDE.md` - Detailed installation guide
- `PASS_RATE_IMPROVEMENT.md` - Test quality improvements
- `MERGE_SUMMARY.md` - Git merge documentation

**API Documentation:**
- Interactive API docs: http://localhost:8000/docs (when running)
- OpenAPI spec: http://localhost:8000/openapi.json

---

## 📊 Documentation Statistics

| File | Size | Lines | Sections |
|------|------|-------|----------|
| HOW_TO_USE.md | 13 KB | ~500 | 9 |
| architecture.md | 22 KB | ~800 | 10 |
| workflow.md | 15 KB | ~600 | 8 |
| development.md | 17 KB | ~650 | 7 |
| **Total** | **67 KB** | **~2,550** | **34** |

---

## 🎯 Documentation Goals

This documentation aims to:

1. **Enable Self-Service**: Users and developers can find answers without asking
2. **Reduce Onboarding Time**: New team members can get productive quickly
3. **Maintain Consistency**: Architectural decisions are documented
4. **Support Quality**: Testing and evaluation processes are clear
5. **Facilitate Contributions**: Contributing guidelines are accessible

---

## 🔄 Documentation Updates

**Last Updated**: September 22, 2026  
**Version**: 1.0.0

**Update Frequency**:
- HOW_TO_USE.md: Updated with new features
- architecture.md: Updated on major architectural changes
- workflow.md: Updated when pipeline stages change
- development.md: Updated when tooling or setup changes

**Maintainer**: FlavorPilot Team

---

## 💡 Documentation Best Practices

When updating documentation:

1. **Keep examples current** - Test all code examples
2. **Update screenshots** - Regenerate UI screenshots when UI changes
3. **Link between docs** - Cross-reference related sections
4. **Version compatibility** - Note which versions features apply to
5. **Include troubleshooting** - Add common issues and solutions

---

## 📝 Feedback

Found an issue or have suggestions for improving documentation?

- **Open an issue**: https://github.com/mayukhg/zomato-flavor-pilot/issues
- **Submit a PR**: Corrections and improvements welcome
- **Start a discussion**: https://github.com/mayukhg/zomato-flavor-pilot/discussions

---

## 📚 External Resources

**Technologies Used:**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Model Context Protocol Spec](https://modelcontextprotocol.io/)

**Related Concepts:**
- [AI Agent Architecture Patterns](https://www.anthropic.com/research/building-effective-agents)
- [RAG Evaluation Best Practices](https://arxiv.org/abs/2404.18930)
- [Prompt Injection Prevention](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)

---

**Happy Building! 🚀**
