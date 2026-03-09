#!/bin/bash
set -e
cd /workspace
python3 -c "import zipfile; zipfile.ZipFile('BA_01.zip').extractall('.')"
ls /workspace/BA_01/
pip install sentencepiece datasets matplotlib --quiet
echo "=== SETUP COMPLETE ==="
python3 -c "import torch; print('torch', torch.__version__, 'cuda:', torch.cuda.is_available())"
