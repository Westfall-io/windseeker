SysML v2 Dependency Analyzer, Notebook Generator, and View Extractor

This project provides a static-analysis and execution pipeline for SysML v2 textual models.
It scans .sysml files, analyzes package dependencies, generates a dependency-ordered SysML Jupyter notebook, executes that notebook, and extracts rendered views as images.

The toolchain is designed to support:

Large, multi-file SysML v2 models

Deterministic dependency ordering

Import cycle detection

Missing-package detection

Automated view rendering and image extraction

✨ Features
Model Analysis

Recursively scans .sysml files

Extracts top-level packages only

Detects import dependencies

Builds a directed dependency graph

Fails fast on:

Import cycles

Imports referencing missing packages

Notebook Generation

Generates a single-kernel SysML Jupyter notebook

One code cell per top-level package

Cells ordered by dependency order

Appends additional cells for each discovered view

Uses %view Fully::Qualified::ViewName

Notebook Execution

Executes the generated notebook programmatically

Supports:

nbclient (preferred)

jupyter nbconvert --execute (fallback)

Detects errors via:

Jupyter error outputs

SysML kernel stderr (ERROR, Exception, Traceback)

View Image Extraction

Extracts rendered views from executed notebooks

Supports:

SVG (raw XML)

PNG (transparent or solid background)

Optional JPG

Automatically rescales oversized SVGs to avoid Cairo rendering errors

📂 Output Artifacts

After a successful run, the tool produces:

File / Folder	Description
packages_in_dependency_order.sysml	Concatenated SysML source in dependency order
packages_in_dependency_order.ipynb	Generated SysML Jupyter notebook
packages_in_dependency_order_executed.ipynb	Executed notebook with outputs
views/	Extracted view images (.svg, .png, optional .jpg)
🛠 Requirements
Python Packages

Create a requirements.txt similar to:

networkx
matplotlib
nbformat
nbclient
jupyter
cairosvg
pillow


Install with:

pip install -r requirements.txt

SysML Jupyter Kernel (Required)

This project requires a SysML kernel registered with Jupyter.

requirements.txt alone is not sufficient — kernels must be registered separately.

Typical install pattern (tool-specific):

pip install <sysml-kernel-package>
python -m <sysml_kernel_module> install


Verify:

jupyter kernelspec list


You should see something like:

sysml

▶️ Usage

Run the pipeline:

python main.py


By default, it:

Scans ./tests for .sysml files

Builds the dependency graph

Generates notebook + .sysml

Executes the notebook

Extracts all views as images

🔍 Supported SysML v2 Constructs

package (top-level only; nested packages remain inside parent cell)

import

view { ... }

Nested packages (for view qualification)

%view magic execution

🧠 Design Principles

Top-level packages = notebook cells

Nested packages stay embedded in their parent

Imports are resolved at the top-level package granularity

Views are fully qualified (e.g. System::Views::MyView)

Fail early, fail clearly

⚠️ Common Errors & Fixes
No such kernel named sysml

The SysML kernel is not registered

Run jupyter kernelspec list

Install and register the kernel

Cairo INVALID_SIZE error

SVG view is too large

Automatically handled via scaling logic

Tunable via max_dim_px / max_pixels

Missing package error

An import references a package not found in the scanned files

Either add the package or ignore it explicitly

🧩 Extensibility

This codebase is designed to be extended easily:

CLI flags (e.g. --no-execute, --views-only)

CI integration

JSON dependency reports

Multiple view renderers

Alternative image formats

View grouping or filtering

📜 License

This project is intended as a tooling and analysis aid for SysML v2 models.
No official affiliation with OMG or any SysML v2 tool vendor is implied.