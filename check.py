#!/usr/bin/env python3
"""Quick check for SK-Agent packages"""

packages = [
    # Scientific computing
    ('numpy', 'numpy'),
    ('scipy', 'scipy'),
    ('pandas', 'pandas'),
    ('matplotlib', 'matplotlib'),
    
    # Single-cell analysis
    ('scanpy', 'scanpy'),
    ('anndata', 'anndata'),
    ('scikit-misc', 'skmisc'),
    
    # Deep learning
    ('torch', 'torch'),
    ('torchvision', 'torchvision'),
    
    # Graph/clustering
    ('python-igraph', 'igraph'),
    ('leidenalg', 'leidenalg'),
    ('scikit-learn', 'sklearn'),
    ('umap-learn', 'umap'),
    
    # Utilities
    ('tqdm', 'tqdm'),
    ('openpyxl', 'openpyxl'),
]

print("Checking packages...\n")

installed = []
missing = []

for pip_name, import_name in packages:
    try:
        __import__(import_name)
        print(f"✅ {pip_name}")
        installed.append(pip_name)
    except ImportError:
        print(f"❌ {pip_name}")
        missing.append(pip_name)

print(f"\n{'='*50}")
print(f"Installed: {len(installed)}/{len(packages)}")
print(f"{'='*50}")

if missing:
    print("\n📦 Install missing packages:\n")
    print(f"pip install --break-system-packages {' '.join(missing)}")
else:
    print("\n🎉 All packages installed!")