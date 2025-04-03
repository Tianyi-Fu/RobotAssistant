# Robot Assistant Framework
![Copy of Human command (6)](https://github.com/user-attachments/assets/af0456eb-c911-4ac6-b288-31d1c0896f1e)

![framework_1-ezgif com-optipng](https://github.com/user-attachments/assets/6a270efd-f093-439d-b4d4-9b601abb50d8)


---
## Environment Requirements

- **Python:** 3.8 or higher (tested with Python 3.8.20)
- **Java:** 11 or higher
  
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

Edit `config.py` to update the UnitySimulator executable paths and API keys. For example, set:

```python
OPENAI_API_KEY = "Replace with your OpenAI API key"
UNITY_EXEC_PATH = "Path/To/virtualhome/virtualhome/simulation/v2.3.0.app"
```
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
