# Robot Assistant Framework

This repository integrates a virtual home environment with a robot assistant that uses a Knowledge Graph (KG), Answer Set Programming (ASP) for goal reasoning, and an LLM (via OpenAI) for high-level command prediction. A Unity-based simulator is also included for virtual interaction.

---

## How to Run the Frameworks

### 1. Install VirtualHome 2.3.0

First, install VirtualHome 2.3.0 using pip:

```bash
pip install virtualhome
```

#### Download Unity Simulator

Download the VirtualHome UnitySimulator executable and move it under `simulation/unity_simulator`.

- [Download Linux x86-64 version](http://virtual-home.org//release/simulator/v2.0/v2.3.0/linux_exec.zip)
- [Download Mac OS X version](http://virtual-home.org/release/simulator/v2.0/v2.3.0/macos_exec.zip)
- [Download Windows version](http://virtual-home.org//release/simulator/v2.0/v2.3.0/windows_exec.zip)

---

### 2. Configure the System

Open the configuration file:

```bash
cd code/config
```

Edit `config.py` to update the necessary paths and API keys. For example, set:

```python
OPENAI_API_KEY = "Replace with your OpenAI API key"
UNITY_EXEC_PATH = "Path/To/virtualhome/virtualhome/simulation/macos_exec.v2.3.0.app"
```

Also, update any other paths (KG files, ASP file, history file, etc.) as required.

---

### 3. Run the Script

Navigate to the main code directory and run the main script:

```bash
cd code
python main.py
```

When prompted, input ASP-format goal conditions. For example:
- `has(user, milk)`
- `on(coffeetable, book)`
- `heated(chicken)`
- `open(microwave)`
- `inside(bookshelf, cupcake)`

---

### 4. Installing Dependencies

Install all required Python dependencies by running:

```bash
pip install -r requirements.txt
```

---
