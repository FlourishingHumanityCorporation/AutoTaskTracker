# 📊 Pipeline Comparison Dashboard Layout

## 🌐 URL: http://localhost:8512

## 📱 Dashboard Structure

```
┌─ SIDEBAR ─────────────────┐  ┌─ MAIN CONTENT ──────────────────────────────────────┐
│  🎛️ Controls              │  │  ⚖️ AI Pipeline Comparison                          │
│                           │  │  Compare different AI processing pipelines side-by-side │
│  Screenshots to load: 30  │  │                                                      │
│  [████████████] (slider)  │  │  ✅ Loaded 3 screenshots for comparison             │
│                           │  │                                                      │
│  ─────────────────────    │  │  ┌─ TAB BAR ──────────────────────────────────────┐  │
│  Pipeline Information     │  │  │ 🔤 Basic Pipeline │ 📝 OCR Pipeline │ 🤖 AI Full │  │
│  🔤 Basic: Pattern only   │  │  └────────────────────────────────────────────────┘  │
│  📝 OCR: Enhanced text    │  │                                                      │
│  🤖 AI Full: Complete AI  │  │  [ACTIVE TAB CONTENT]                               │
│                           │  │                                                      │
│  ─────────────────────    │  │  🔧 Basic Pattern Matching                          │
│  Quick Tips               │  │  Original method using window title patterns        │
│                           │  │                                                      │
│  • Select same screenshot │  │  Select screenshot to analyze                       │
│  • Compare confidence     │  │  [screenshot-20250703-192109... ▼] (dropdown)       │
│  • Note feature diffs     │  │                                                      │
│  • Check processing       │  │  ┌─ SCREENSHOT INFO ──────────┐ ┌─ THUMBNAIL ──────┐ │
│                           │  │  │ File: screenshot-20250703-... │ │ [📸 Screenshot] │ │
│                           │  │  │ Time: 2025-07-03 19:21:13   │ │ 300x200px image │ │
│                           │  │  │ Window: AutoTaskTracker...   │ │                 │ │
│                           │  │  │ Available Data: 📝 OCR       │ │                 │ │
│                           │  │  └─────────────────────────────┘ └─────────────────┘ │
│                           │  │                                                      │
│                           │  │  ═══════════════════════════════════════════════════ │
│                           │  │                                                      │
│                           │  │  📊 Analysis Results                                │
│                           │  │  ┌─ METRICS ─────────────────────────────────────┐  │
│                           │  │  │ Confidence Score │ Detected Task  │ Category   │  │
│                           │  │  │      50%         │ AI Coding:     │ 🧑‍💻 Coding │  │
│                           │  │  │   🟡 Medium      │ AutoTaskTracker│            │  │
│                           │  │  └───────────────────────────────────────────────┘  │
│                           │  │                                                      │
│                           │  │  🔍 Processing Details                              │
│                           │  │  ┌─ FEATURES ─────┐ ┌─ PROCESSING ──────────────┐  │
│                           │  │  │ Features Used:  │ │ Processing Details:       │  │
│                           │  │  │ • Window Title  │ │ • Method: Pattern match   │  │
│                           │  │  │                 │ │ • Data Sources: Window    │  │
│                           │  │  │                 │ │ • Processing Time: Instant│  │
│                           │  │  └─────────────────┘ └───────────────────────────┘  │
└───────────────────────────┘  └──────────────────────────────────────────────────────┘
```

## 🎨 Visual Elements

### **Header**
- **Title:** ⚖️ AI Pipeline Comparison (large, prominent)
- **Subtitle:** Compare different AI processing pipelines side-by-side (italics)
- **Status:** ✅ Loaded X screenshots for comparison (green checkmark)

### **Tab Navigation**
Three identical-looking tabs that switch the processing pipeline:
- **🔤 Basic Pipeline** - Yellow/orange theme
- **📝 OCR Pipeline** - Blue theme  
- **🤖 AI Full Pipeline** - Purple/AI theme

### **Each Tab Contains:**

#### **Pipeline Info Section**
- Pipeline name and description
- Icon representing the pipeline type

#### **Screenshot Selector**
- Dropdown to select which screenshot to analyze
- Shows filename and timestamp for each option

#### **Screenshot Display**
- **Left side:** File details, timestamp, window title, available data indicators
- **Right side:** Thumbnail image (300x200px) of the actual screenshot

#### **Results Section**
Three metric cards showing:
1. **Confidence Score** with colored indicator:
   - 🟢 Green (>80%)
   - 🟡 Yellow (60-80%) 
   - 🔴 Red (<60%)
2. **Detected Task** (truncated if long)
3. **Category** with emoji

#### **Details Breakdown**
Two columns:
- **Features Used:** Bullet list of data sources
- **Processing Details:** Method info, timing, etc.

### **Sidebar Controls**
- **Screenshot limit slider** (10-100)
- **Pipeline information** summary
- **Usage tips** for comparison

## 🎯 Key Features

### **Interactive Elements**
- Screenshot dropdown synced across tabs
- Hover tooltips on metrics
- Expandable detail sections
- Color-coded confidence levels

### **Visual Indicators**
- 📝 OCR available
- 👁️ VLM available  
- 🧠 Embedding available
- 🟢🟡🔴 Confidence colors

### **Responsive Design**
- Wide layout optimized for comparison
- Sidebar collapsible
- Mobile-friendly metrics cards

## 📊 Sample Data Display

**Recent Screenshot:**
- `screenshot-20250703-192109-of-arzopa.webp`
- Time: `2025-07-03 19:21:13`
- Window: `AutoTaskTracker — ✳ Core Methods — claude...`

**Pipeline Results:**
- **Basic:** AI Coding: AutoTaskTracker (🟡 50%)
- **OCR:** AI Coding: AutoTaskTracker (🔴 0%) 
- **AI Full:** AI Coding: AutoTaskTracker (🟡 50%)

The dashboard provides a clean, professional interface for comparing how different AI processing pipelines handle the same screenshots, making it easy to evaluate which approach works best for different types of content.