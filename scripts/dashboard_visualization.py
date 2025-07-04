#!/usr/bin/env python3
"""
Create visual representations of the AutoTaskTracker dashboards
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def show_task_board():
    """Show Task Board layout"""
    print("\n" + "="*70)
    print("🖥️  TASK BOARD DASHBOARD (http://localhost:8502)")
    print("="*70)
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    📋 AutoTaskTracker - Task Board                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  📅 Date Range: [2025-07-03 ▼] to [2025-07-04 ▼]   🔄 Refresh      ║
║  🏷️  Category: [All Categories ▼]                                   ║
║                                                                      ║
╠═══════════════════════════╤══════════════════════════════════════════╣
║  📊 METRICS               │  📈 ACTIVITY TIMELINE                    ║
║ ┌────────────────────┐    │  ┌────────────────────────────────────┐ ║
║ │ Total Activities   │    │  │     Activity Over Time             │ ║
║ │      1,000         │    │  │  40 ┤ ╭─╮                         │ ║
║ └────────────────────┘    │  │  30 ┤ │ ╰─╮  ╭─╮                 │ ║
║ ┌────────────────────┐    │  │  20 ┤ │   ╰──╯ ╰─╮               │ ║
║ │ Unique Tasks       │    │  │  10 ┤ │         ╰─────          │ ║
║ │       23           │    │  │   0 └─┴─┴─┴─┴─┴─┴─┴─┴─┴─        │ ║
║ └────────────────────┘    │  │     21:00  22:00  23:00  00:00    │ ║
║ ┌────────────────────┐    │  └────────────────────────────────────┘ ║
║ │ Active Hours       │    │                                          ║
║ │      2.8           │    │  📊 CATEGORY DISTRIBUTION               ║
║ └────────────────────┘    │  ┌────────────────────────────────────┐ ║
║ ┌────────────────────┐    │  │ 🤖 AI Tools        ████████ 78.9% │ ║
║ │ Top Category       │    │  │ 🧑‍💻 Coding         ██ 20.3%       │ ║
║ │   🤖 AI Tools      │    │  │ 📋 Other           ▌ 0.8%         │ ║
║ └────────────────────┘    │  └────────────────────────────────────┘ ║
╠═══════════════════════════╧══════════════════════════════════════════╣
║  🗂️  RECENT ACTIVITIES                                              ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ Time   │ Category      │ Window Title                          │ ║
║ ├────────┼───────────────┼───────────────────────────────────────┤ ║
║ │ 00:09  │ 🤖 AI Tools   │ AutoTaskTracker — Software Testing    │ ║
║ │ 00:08  │ 🧑‍💻 Coding    │ AutoTaskTracker — Testing Concerns    │ ║
║ │ 00:08  │ 🤖 AI Tools   │ AutoTaskTracker — Technical Support   │ ║
║ │ 00:08  │ 📋 Other      │ paulrohde - Daily Notes               │ ║
║ │ 00:05  │ 🤖 AI Tools   │ AutoTaskTracker — Test System Health  │ ║
║ └────────┴───────────────┴───────────────────────────────────────┘ ║
║  [Export CSV]  [Export JSON]  Page 1 of 50  [< Prev] [Next >]      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

def show_analytics_dashboard():
    """Show Analytics dashboard layout"""
    print("\n" + "="*70)
    print("📊 ANALYTICS DASHBOARD (http://localhost:8503)")
    print("="*70)
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    📊 AutoTaskTracker - Analytics                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  📅 Period: [Last 7 Days ▼]    Compare to: [Previous Period ▼]      ║
║                                                                      ║
╠═════════════════════════════════╤════════════════════════════════════╣
║  📈 PRODUCTIVITY TRENDS         │  🎯 FOCUS ANALYSIS                  ║
║ ┌─────────────────────────────┐ │ ┌──────────────────────────────┐  ║
║ │   Daily Active Hours        │ │ │    Focus Score by Day        │  ║
║ │ 8 ┤      ╭─╮               │ │ │ 100┤        ╭─╮            │  ║
║ │ 6 ┤  ╭─╮ │ │ ╭─╮           │ │ │  75┤    ╭─╮ │ │            │  ║
║ │ 4 ┤  │ ╰─╯ ╰─╯ │           │ │ │  50┤ ╭──╯ ╰─╯ │            │  ║
║ │ 2 ┤  │         │           │ │ │  25┤ │        ╰─           │  ║
║ │ 0 └──┴─┴─┴─┴─┴─┴─          │ │ │   0└─┴─┴─┴─┴─┴─┴─          │  ║
║ │    Mon Tue Wed Thu Fri     │ │ │    Mon Tue Wed Thu Fri     │  ║
║ └─────────────────────────────┘ │ └──────────────────────────────┘  ║
╠═════════════════════════════════╧════════════════════════════════════╣
║  📊 CATEGORY BREAKDOWN                                               ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ Category        │ This Period │ Last Period │ Change           │ ║
║ ├─────────────────┼─────────────┼─────────────┼──────────────────┤ ║
║ │ 🧑‍💻 Coding       │ 45.2 hrs    │ 38.5 hrs    │ ↑ +17.4%        │ ║
║ │ 🤖 AI Tools     │ 28.3 hrs    │ 31.2 hrs    │ ↓ -9.3%         │ ║
║ │ 🔍 Research     │ 12.7 hrs    │ 10.1 hrs    │ ↑ +25.7%        │ ║
║ │ 💬 Communication│  8.4 hrs    │  9.8 hrs    │ ↓ -14.3%        │ ║
║ └─────────────────┴─────────────┴─────────────┴──────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════╣
║  🏆 TOP TASKS BY TIME                                                ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 1. VS Code - main.py                              12.3 hrs     │ ║
║ │ 2. Chrome - Documentation                          8.7 hrs     │ ║
║ │ 3. Slack - Team Chat                              6.2 hrs     │ ║
║ │ 4. Terminal - git operations                      4.5 hrs     │ ║
║ │ 5. Figma - UI Design                              3.8 hrs     │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
""")

def show_time_tracker():
    """Show Time Tracker dashboard layout"""
    print("\n" + "="*70)
    print("⏱️  TIME TRACKER DASHBOARD (http://localhost:8505)")
    print("="*70)
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    ⏱️  AutoTaskTracker - Time Tracker                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  📅 Date: [Today ▼]           Min Session: [30 seconds ▼]           ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  📊 TODAY'S SUMMARY                                                  ║
║ ┌─────────────────┬─────────────────┬─────────────────┬───────────┐ ║
║ │ Total Time      │ Active Time     │ Idle Time       │ Sessions  │ ║
║ │   8h 24m        │   7h 12m        │   1h 12m        │    23     │ ║
║ └─────────────────┴─────────────────┴─────────────────┴───────────┘ ║
╠══════════════════════════════════════════════════════════════════════╣
║  ⏰ TIME SESSIONS                                                    ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ Start  │ End    │ Duration │ Task                  │ Confidence│ ║
║ ├────────┼────────┼──────────┼───────────────────────┼───────────┤ ║
║ │ 09:15  │ 10:45  │ 1h 30m   │ VS Code - feature.py  │ 🟢 0.95   │ ║
║ │ 10:50  │ 11:20  │ 30m      │ Slack - Team Updates  │ 🟢 0.88   │ ║
║ │ 11:25  │ 12:00  │ 35m      │ Chrome - API Docs     │ 🟡 0.72   │ ║
║ │ 13:00  │ 14:15  │ 1h 15m   │ VS Code - tests.py    │ 🟢 0.91   │ ║
║ │ 14:20  │ 14:35  │ 15m      │ Terminal - git push   │ 🔴 0.45   │ ║
║ └────────┴────────┴──────────┴───────────────────────┴───────────┘ ║
║                                                                      ║
║  💡 Confidence Indicators:                                           ║
║  🟢 High (>0.8): Regular screenshots, continuous work                ║
║  🟡 Medium (0.6-0.8): Some gaps but consistent activity              ║
║  🔴 Low (<0.6): Large gaps, may be overestimated                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  📈 FOCUS METRICS                                                    ║
║ ┌─────────────────────┬─────────────────────┬─────────────────────┐ ║
║ │ Longest Session     │ Focus Score         │ Context Switches    │ ║
║ │     1h 30m          │    75/100           │        12           │ ║
║ └─────────────────────┴─────────────────────┴─────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
""")

def main():
    """Show all dashboard visualizations"""
    print("\n🚀 AutoTaskTracker Live Dashboard Visualizations")
    print("=" * 70)
    print("\nAutoTaskTracker provides multiple dashboards for different views:")
    print("1. Task Board - Real-time activity monitoring")
    print("2. Analytics - Productivity trends and insights")  
    print("3. Time Tracker - Session-based time tracking")
    
    show_task_board()
    show_analytics_dashboard()
    show_time_tracker()
    
    print("\n📝 HOW TO ACCESS THE LIVE DASHBOARDS:")
    print("=" * 70)
    print("1. Start all dashboards:    python autotasktracker.py start")
    print("2. Task Board only:         python autotasktracker.py dashboard")
    print("3. Analytics only:          python autotasktracker.py analytics")
    print("4. Time Tracker only:       python autotasktracker.py timetracker")
    print("\nThe dashboards update in real-time as Pensieve captures screenshots!")

if __name__ == "__main__":
    main()