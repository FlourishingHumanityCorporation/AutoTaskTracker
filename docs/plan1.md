Of course. Here is a full, step-by-step guide to get your personalized AI task discovery application running as quickly and easily as possible.

This plan is designed for maximum efficiency. It leverages the powerful open-source `Pensieve` project as a foundation for the complex backend tasks (passive screen capture and AI analysis) and focuses your effort on building the custom, engaging task board you envision.

-----

## Pre-Mortem: Potential Failure Scenarios & Mitigations

| # | Failure Scenario | Likelihood | Impact | Early Warning / Indicators | Mitigation / Contingency |
| --- | --- | --- | --- | --- | --- |
| 1 | Python / `pip` version mismatch prevents installing `memos` | Medium | High – blocks setup | `pip install memos` raises version errors | Confirm Python ≥ 3.9; run `python -m pip install --upgrade pip` first |
| 2 | `memos start` fails to launch background services | Low | High – no data captured | `memos status` shows services crashed; no new screenshots in `~/.memos/screens/` | Inspect logs in `~/.memos/logs`; run `memos doctor`; temporarily run `memos record --once` to verify capture |
| 3 | Rapid disk growth from accumulated screenshots | Medium | Medium | `du -h ~/.memos/` exceeds threshold | Set `screenshots_retention_days` in `config.yaml`; schedule cron job to prune images |
| 4 | Streamlit dashboard sluggish or crashes with many images | Medium | Medium | Page load > 5 s or browser tab freezes | Paginate `tasks_df`; down-sample thumbnails; archive > 30-day images |
| 5 | Privacy leak—screenshots synced to cloud backup services | Low | Critical | Files visible in iCloud/Dropbox web UI | Add `~/.memos/` to backup ignore list; encrypt drive; set directory permissions `700` |
| 6 | Ollama model download fails or exceeds GPU/CPU resources | Medium | Medium | `ollama pull` errors; high memory usage alerts | Test with smaller `minicpm-v` first; enable CPU-only mode; fall back to text-only summarization |
| 7 | API port conflicts (8839 or 8501) already in use | Low | Low | Browser shows connection refused; `lsof -i :8839` reveals another process | Change ports in `config.yaml`/Streamlit `--server.port`; or stop conflicting process |

# Project Blueprint: Building Your Personal AI Task-Sensing App

This document provides a phased, step-by-step plan to create a privacy-first, AI-powered application that passively discovers and organizes your daily tasks from screenshots.

### **Phase 1: Core System Setup & Verification**

This phase gets the foundational `Pensieve` engine installed and running. It will begin capturing and analyzing your screen activity in the background, providing the data needed for your task board.

#### **Step 1: Set Up Your Python Environment**

`Pensieve` is a Python application. To ensure a clean installation, it's best to use a dedicated virtual environment.

1.  **Ensure Python is installed:** Open your terminal or command prompt and verify you have Python 3.9 or newer.
2.  **Create a project directory:**
    ```bash
    mkdir my-task-sensor
    cd my-task-sensor
    ```
3.  **Create and activate a virtual environment:**
      * On macOS / Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
      * On Windows:
        ```bash
        python -m venv venv
        ```
    .\\venv\\Scripts\\activate
    \`\`\`

#### **Step 2: Install and Initialize `Pensieve`**

Now, you will install the `Pensieve` package and set up its initial configuration.

1.  **Install with `pip`:**
    ```bash
    pip install memos
    ```
2.  **Initialize the configuration:**
    ```bash
    memos init
    ```
    This command creates a hidden directory in your user home folder (`~/.memos`). This folder is critical as it will store all your data locally, including the configuration file (`config.yaml`), the SQLite database (`memos.db`), and all captured screenshots. This local-first design ensures your privacy is maintained.[3]

#### **Step 3: Start the `Pensieve` Background Services**

With the configuration in place, you can start the services that will capture and process your activity.

1.  **Enable and start the services:**
    ```bash
    memos enable
    memos start
    ```
    These commands start three distinct background processes [3]:
      * `memos record`: Begins capturing screenshots of your display(s) at regular intervals.
      * `memos watch`: Monitors for new screenshots and queues them for AI processing.
      * `memos serve`: Runs a local web server and API, which you will use later.

The application is now passively recording your activity.

#### **Step 4: Verify the System is Working**

Before building the custom interface, confirm that the backend is capturing and processing data correctly.

1.  **Open your web browser** and navigate to: `http://localhost:8839`.[3]
2.  You should see the default `Pensieve` web interface. After giving it some time to capture and index a few screenshots, you can use the search bar to find activities. For example, if you were just viewing this document, you could search for "Pensieve" or "task board," and the relevant screenshots should appear.

-----

### **Phase 2: Building Your Custom Task Board**

With the backend running, you can now focus on creating the engaging, customized task board interface you wanted. This phase uses a rapid development approach with a Python dashboarding library.

#### **Step 5: Choose Your Dashboarding Tool**

For the fastest path to an interactive UI, use a Python-based library. This avoids the need for complex web development with separate frontend frameworks.

  * **Recommendation:** **Streamlit**. It is exceptionally easy to use and allows you to create beautiful, interactive web apps with just a few lines of Python code.[4, 5]

<!-- end list -->

1.  **Install Streamlit:**
    ```bash
    pip install streamlit pandas
    ```

#### **Step 6: Create Your Dashboard Script**

Create a new Python file in your project directory, for example, `task_board.py`. This script will read data from the `Pensieve` database and display it.

The core idea is to query the local SQLite database where `Pensieve` stores all its processed information.

Here is a starter script for `task_board.py`:

```python
import streamlit as st
import sqlite3
import pandas as pd
import os
from PIL import Image

# --- Configuration ---
# Path to the Pensieve database. Adjust if your home directory is different.
HOME_DIR = os.path.expanduser("~")
PENSIEVE_DB_PATH = os.path.join(HOME_DIR, '.memos', 'memos.db')
SCREENSHOTS_DIR = os.path.join(HOME_DIR, '.memos', 'screenshots')

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="My AI Task Board")

st.title("✅ My AI-Powered Daily Task Board")
st.write("A passive and engaging look at what you've accomplished today.")

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(f'file:{PENSIEVE_DB_PATH}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        st.error(f"Error connecting to the database: {e}")
        st.info("Is the Pensieve service running? You can start it with 'memos start'.")
        return None

# --- Data Fetching ---
@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_tasks(limit=100):
    """Fetches the latest processed screenshots from the Pensieve database."""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
        
    query = """
    SELECT
        s.id,
        s.active_window,
        s.ocr_text,
        s.image_path,
        s.created_at
    FROM
        screenshots s
    ORDER BY
        s.created_at DESC
    LIMIT?
    """
    try:
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except pd.io.sql.DatabaseError as e:
        st.error(f"Error querying the database: {e}")
        st.info("The database schema might be different or the table doesn't exist yet. Let Pensieve run for a bit.")
        return pd.DataFrame()


# --- Main App Logic ---
tasks_df = fetch_tasks()

if not tasks_df.empty:
    st.header("Latest Activity Stream")
    
    # Create a more engaging "card" layout
    for index, row in tasks_df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([1, 2]) # Split into two columns
            
            with col1:
                st.subheader(f"Task: {row['active_window']}")
                st.caption(f"Captured at: {pd.to_datetime(row['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show a snippet of the OCR text
                with st.expander("Show recognized text"):
                    st.text(row['ocr_text'][:500] + "..." if row['ocr_text'] and len(row['ocr_text']) > 500 else row['ocr_text'])

            with col2:
                # Display the screenshot thumbnail
                full_image_path = os.path.join(SCREENSHOTS_DIR, row['image_path'])
                if os.path.exists(full_image_path):
                    try:
                        image = Image.open(full_image_path)
                        st.image(image, caption="Screenshot", use_column_width=True)
                    except Exception as e:
                        st.warning(f"Could not load image: {e}")
                else:
                    st.warning("Screenshot not found.")

else:
    st.info("Waiting for task data from Pensieve... Work for a few minutes and then refresh this page.")

```

#### **Step 7: Run Your Custom Task Board**

1.  Make sure the `Pensieve` services are still running in the background.
2.  In your terminal, run your Streamlit app:
    ```bash
    streamlit run task_board.py
    ```
3.  Your web browser will open a new tab with your custom dashboard. As `Pensieve` continues to capture screenshots, you can refresh this page to see your latest activities appear.

You now have a fully functional, AI-powered task discovery system with a custom user interface.

-----

### **Phase 3: Advanced Customization (Optional Next Steps)**

Once you are comfortable with the basic setup, you can extend the system's capabilities.

#### **Advanced AI: Task Summarization with a Local LLM**

`Pensieve` can integrate with a local Large Language Model (LLM) through **Ollama** for more sophisticated task summarization, moving beyond simple search to genuine task inference.[3] This is inspired by advanced research concepts like creating a "Stateful Screen Schema" to feed rich, structured context to an LLM for better understanding.[6, 7, 8]

1.  **Install Ollama:** Follow the official instructions to install Ollama for your operating system (macOS, Windows, or Linux).
2.  **Download a Multimodal Model (VLM):** Open your terminal and pull a VLM. The `minicpm-v` model is a good starting point as it's powerful yet relatively small.[3]
    ```bash
    ollama pull minicpm-v
    ```
3.  **Configure `Pensieve`:**
      * Open the `config.yaml` file located in `~/.memos/`.
      * Find the `vlm` section and configure it to use your Ollama model. This tells `Pensieve` to send screenshot data to the local LLM for analysis.
    <!-- end list -->
    ```yaml
    vlm:
      enable: true
      endpoint: "http://localhost:11434/v1/chat/completions"
      model: "minicpm-v"
      # You can customize the prompt to change how the LLM summarizes tasks
      prompt: "This is a screenshot of a user's screen. Please describe the main task the user is performing in a concise, action-oriented sentence."
    ```
4.  **Restart `Pensieve`** to apply the new configuration:
    ```bash
    memos stop
    memos start
    ```

`Pensieve` will now enrich its database with LLM-generated summaries, which you can then query and display in your custom `task_board.py` dashboard.

-----

This step-by-step plan provides the fastest and most direct path to achieving your goal. By building on `Pensieve`, you leverage a powerful, privacy-focused backend and can dedicate your time to creating the perfect user experience for your task board.