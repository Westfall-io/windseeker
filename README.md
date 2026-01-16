# Windseeker

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Jupyter](https://img.shields.io/badge/jupyter-notebook-orange.svg)
![SysML](https://img.shields.io/badge/SysML-v2-green.svg)
![CLI](https://img.shields.io/badge/CLI-windseeker-brightgreen.svg)
![Status](https://img.shields.io/badge/status-experimental-yellow.svg)
![PyPI](https://img.shields.io/pypi/v/sysml-windseeker.svg)
![Coverage](https://img.shields.io/codecov/c/github/Westfall-io/windseeker)

**Windseeker** is a command-line tool for **SysML v2 dependency analysis, notebook generation, execution, and view extraction**.

It scans `.sysml` files, analyzes package dependencies, generates a dependency-ordered SysML Jupyter notebook, executes that notebook using a SysML kernel, and extracts rendered **views** as images.

> **Naming note**
>
> - **PyPI distribution name:** `sysml-windseeker`
> - **Python import name:** `windseeker`
> - **CLI command:** `windseeker`

---

## AI Assisted Development

This project has used generative AI to assist in the development of the tool.

---

## ✨ Features

### Model Analysis
- Recursively scans `.sysml` files
- Extracts **top-level packages only**
- Detects `import` dependencies
- Builds a directed dependency graph
- Fails fast on:
  - Import cycles
  - Invalid dependency ordering

### Notebook Generation
- Generates a **single-kernel SysML Jupyter notebook**
- One **code cell per top-level package**
- Cells ordered by **dependency order**
- Nested packages remain embedded in their parent cell
- Appends additional cells for each discovered `view`
  - Uses `%view Fully::Qualified::ViewName`

### Notebook Execution
- Executes the generated notebook programmatically
- Supports:
  - `nbclient` (preferred)
  - `jupyter nbconvert --execute` (fallback)
- Detects errors via:
  - Jupyter `error` outputs
  - SysML kernel `stderr` (`ERROR`, `Exception`, `Traceback`)

### View Image Extraction
- Extracts rendered views from executed notebooks
- Supports:
  - SVG (raw XML)
  - PNG (transparent or solid background)
  - Optional JPG
- Automatically rescales oversized SVGs to avoid Cairo rendering errors

---

## 🚀 Quick Start

### 1) Install Windseeker

Install from PyPI:

```bash
pip install sysml-windseeker
```

This installs the `windseeker` CLI command.

For development or local use:

```bash
pip install -e .
```

---

### 2) Ensure a SysML Jupyter Kernel Is Installed

Windseeker **requires a SysML kernel registered with Jupyter**.

Verify:

```bash
jupyter kernelspec list
```

You must see a kernel such as:

```
sysml
```

> Kernel installation is tool-specific and cannot be handled via `requirements.txt` or `pyproject.toml`.

---

### 3) Minimal Example Model

Create `tests/simple.sysml`:

```sysml
package DemoSystem {

  port def DbPort {
    in item query  : String;
    out item result : String;
  }

  part def UI {
    out port db : DbPort;
  }

  part def ElasticDB {
    in port api : ~DbPort;
  }

  part def System {
    part ui : UI;
    part db : ElasticDB;
    connect ui.db to db.api;
  }

  package Views {
    view uiDbConnection {
      expose DemoSystem::System::ui;
      expose DemoSystem::System::db;
    }
  }
}
```

---

### 4) Run Windseeker

```bash
windseeker run
```

---

## 📜 License

MIT
