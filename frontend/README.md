# DevMind AI Multi-Agent Platform - Next.js Frontend Client

The frontend of DevMind is a premium, high-fidelity developer dashboard built using **Next.js 16**, **TypeScript**, and **Vanilla CSS Modules**. It communicates with the FastAPI backend via REST endpoints and real-time WebSockets to stream AI multi-agent analytics.

---

## 🎨 Design System & Aesthetics
- **Dark Mode Palette:** Tailored HSL color tokens for smooth transitions, rich backgrounds, and badged statuses.
- **Glassmorphism:** Elegant border-radius layers using backdrop-filters to give a modern, premium IDE-like feel.
- **Typography:** Using Google Fonts:
  - `Outfit` (Headings and titles)
  - `Inter` (UI elements, buttons, and readable body text)
  - `JetBrains Mono` (Code blocks and terminal logs)
- **Micro-Animations:** Hover state scaling, loading spinners, and fading cards.

---

## 🏗️ Folder Structure

```
frontend/
├── public/                 # Static assets (favicons, icons)
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Global font loaders and context
│   │   ├── globals.css     # CSS variable tokens and base styles
│   │   ├── page.tsx        # Submit repository landing page
│   │   ├── page.module.css # Homepage-specific styles
│   │   ├── dashboard/[id]/
│   │   │   ├── page.tsx    # Live streaming analysis view
│   │   │   └── page.module.css
│   │   └── components/     # High-end reusable React UI
│   │       ├── AgentPanel.tsx          # Agent results renderer
│   │       ├── AgentPanel.module.css
│   │       ├── MetricsChart.tsx        # Recharts visual panels
│   │       └── MetricsChart.module.css
├── package.json
└── tsconfig.json
```

---

## 🖥️ Key UI Components

### 1. `AgentPanel.tsx`
Renders a dashboard panel containing output from the 4 parallel LangGraph agents:
- **Doc Agent:** Formatted Markdown file list and inline structure view.
- **Review Agent:** Issue cards categorized by severity (Info, Low, Medium, High, Critical) with expand/collapse filters.
- **Q&A Agent:** Interactive, scrollable chat panel targeting codebase files via RAG.
- **Analytics Agent:** Detailed grid of lines-of-code, file counts, and AST complexity indices.

### 2. `MetricsChart.tsx`
Dynamic visual graphs built on **Recharts**:
- **Scatter Plot:** AST complexity score vs. Lines of Code (LOC) per file to isolate high-risk functions.
- **Bar Chart:** Top files sorted by Lines of Code.
- **Pie Chart:** Distribution of codebase file tiers (Small, Medium, Large, Giant).

---

## 🔌 Connection & Streaming Lifecycle
- **WebSocket Gateway:** Subscribes to `/ws/{job_id}` at startup. Streams incoming JSON packages containing current task status and logs.
- **Robust Polling Fallback:** Automatically switches to continuous GET `/api/results/{job_id}` REST polling in the event of local network WebSocket connection dropouts.

---

## 🚀 Running the Frontend locally

```bash
# 1. Install packages
npm install

# 2. Run the development server
npm run dev

# 3. Build production bundle
npm run build
```
