# SysML v2 Dependency Analyzer, Notebook Generator, and View Extractor

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Jupyter](https://img.shields.io/badge/jupyter-notebook-orange.svg)
![SysML](https://img.shields.io/badge/SysML-v2-green.svg)
![Status](https://img.shields.io/badge/status-experimental-yellow.svg)

This project provides a **static-analysis and execution pipeline for SysML v2 textual models**.  
It scans `.sysml` files, analyzes package dependencies, generates a dependency-ordered SysML Jupyter notebook, executes that notebook, and extracts rendered **views** as images.

The toolchain is designed to support:
- Large, multi-file SysML v2 models
- Deterministic dependency ordering
- Import cycle detection
- Missing-package detection
- Automated view rendering and image extraction

---

## AI Assisted Development

This project has used generative AI to assist in the development of the tool.

## ✨ Features

### Model Analysis
- Recursively scans `.sysml` files
- Extracts **top-level packages only**
- Detects `import` dependencies
- Builds a directed dependency graph
- Fails fast on:
  - Import cycles
  - Imports referencing missing packages

### Notebook Generation
- Generates a **single-kernel SysML Jupyter notebook**
- One **code cell per top-level package**
- Cells ordered by **dependency order**
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

### 1) Minimal Example Model

Create a file `tests/simple.sysml`:

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

### 2) Install Dependencies

```bash
pip install -r requirements.txt
```

### 3) Ensure SysML Kernel Is Installed

```bash
jupyter kernelspec list
```

You must see a `sysml` kernel. If not, install and register your SysML kernel per your tool’s instructions.

### 4) Run the Pipeline

```bash
python cli.py run
```

> `main.py` contains the core pipeline logic and is treated as a library module.  
> `cli.py` is the supported entry point for end users.

### 5) Inspect Outputs

- `packages_in_dependency_order.sysml`
- `packages_in_dependency_order.ipynb`
- `packages_in_dependency_order_executed.ipynb`
- `views/*.svg`, `views/*.png`

---

## 🧰 CLI Usage

This project exposes a Typer-based command-line interface via `cli.py`.

To see all available commands and options:

```bash
python cli.py --help
```

### Run the full pipeline

```bash
python cli.py run
```

This performs:

1. SysML file scanning  
2. Dependency graph construction  
3. Cycle and missing-import validation  
4. Notebook generation  
5. Notebook execution  
6. View image extraction  

---

### Common CLI Examples

#### Disable graph image generation
```bash
python cli.py run --no-graph
```

#### Specify a custom graph output
```bash
python cli.py run --graph --graph-png my_graph.png
```

#### Skip notebook execution (generate only)
```bash
python cli.py run --no-execute
```

#### Extract views with an opaque PNG background
```bash
python cli.py run --png-opaque --png-bg "#ffffff"
```

#### Change input folder
```bash
python cli.py run --folder ./models
```

---

### Print dependency order only

```bash
python cli.py order
```

This prints the topological package order without generating any output artifacts.

---

## 📂 Output Artifacts

| File / Folder | Description |
|---------------|-------------|
| `packages_in_dependency_order.sysml` | Concatenated SysML source in dependency order |
| `packages_in_dependency_order.ipynb` | Generated SysML Jupyter notebook |
| `packages_in_dependency_order_executed.ipynb` | Executed notebook with outputs |
| `views/` | Extracted view images (`.svg`, `.png`, optional `.jpg`) |

---

## 🛠 Requirements

### Python Packages

```txt
networkx
matplotlib
nbformat
nbclient
jupyter
cairosvg
pillow
```

### SysML Jupyter Kernel (Required)

This project **requires a SysML kernel registered with Jupyter**.

> `requirements.txt` alone is **not sufficient** — kernels must be registered separately.

Typical install pattern (tool-specific):

```bash
pip install <sysml-kernel-package>
python -m <sysml_kernel_module> install
```

The CLI validates kernel availability at execution time; kernel installation
cannot be handled via `requirements.txt`.

---

## 🧠 Design Principles

- **Top-level packages = notebook cells**
- Nested packages stay embedded in their parent
- Imports are resolved at the top-level package granularity
- Views are fully qualified (e.g. `System::Views::MyView`)
- Fail early, fail clearly

---

## 🧠 CLI Design Notes

- The CLI is implemented using **Typer** (Click-based) to provide:
  - Strong typing
  - Clear `--help` output
  - Explicit boolean flags (`--flag / --no-flag`)
- Boolean toggles are always separated from path arguments  
  (e.g. `--graph` vs `--graph-png`)
- All validation failures (cycles, missing packages, execution errors)
  result in a non-zero exit code, making the tool CI-friendly

---

## ⚠️ Common Errors & Fixes

### `No such kernel named sysml`
- The SysML kernel is not registered
- Run `jupyter kernelspec list`
- Install and register the kernel

### Cairo `INVALID_SIZE` error
- SVG view is too large
- Automatically handled via scaling logic
- Tunable via `max_dim_px` / `max_pixels`

### Missing package error
- An `import` references a package not found in the scanned files
- Either add the package or ignore it explicitly

---

## 🧩 Extensibility

This codebase is designed to be extended easily:

- CLI flags (e.g. `--no-execute`, `--views-only`)
- CI integration
- JSON dependency reports
- Multiple view renderers
- Alternative image formats
- View grouping or filtering

---

## 📜 License

This project is intended as a **tooling and analysis aid** for SysML v2 models.  
No official affiliation with OMG or any SysML v2 tool vendor is implied.