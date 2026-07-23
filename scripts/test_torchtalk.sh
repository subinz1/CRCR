#!/bin/bash
# Test TorchTalk inside a PyTorch build container with compile_commands.json
#
# Usage:
#   bash test_torchtalk.sh <image_tag>
#   bash test_torchtalk.sh rhel9-pytorch-nightly:be929eef178d24cdbbb4e92461636824421097f1

set -euo pipefail

IMAGE_TAG="${1:?Usage: bash test_torchtalk.sh <image_tag>}"

echo "================================================"
echo "TorchTalk Integration Test"
echo "Image: ${IMAGE_TAG}"
echo "================================================"

podman run --rm "${IMAGE_TAG}" bash -c '
set -euo pipefail
source /miniconda/etc/profile.d/conda.sh && conda activate cuda_torch_build

echo ""
echo "=== Step 1: Check compile_commands.json ==="
CCJ=""
for p in /pytorch/build/compile_commands.json /pytorch/compile_commands.json; do
    if [ -f "$p" ]; then
        CCJ="$p"
        SIZE=$(du -sh "$p" | cut -f1)
        ENTRIES=$(grep -c "\"file\":" "$p" || echo "unknown")
        echo "  Found: $p"
        echo "  Size: ${SIZE}"
        echo "  Entries: ${ENTRIES}"
        break
    fi
done
if [ -z "$CCJ" ]; then
    echo "  NOT FOUND — TorchTalk C++ analysis will be skipped"
fi

echo ""
echo "=== Step 2: Check TorchTalk is installed ==="
python -c "import torchtalk; print(f\"  torchtalk {torchtalk.__version__}\")" 2>&1 || echo "  FAILED: TorchTalk not importable"

echo ""
echo "=== Step 3: TorchTalk init_from_source (5min timeout) ==="
timeout 300 python -c "
import time
from torchtalk.indexer import _init_from_source, _state

start = time.time()
_init_from_source(\"/pytorch\")
elapsed = time.time() - start

print(f\"  Init time: {elapsed:.1f}s\")
print(f\"  cpp_extractor: {\"available\" if _state.cpp_extractor else \"None\"}\")
print(f\"  test_classes: {len(_state.test_classes) if _state.test_classes else 0}\")
print(f\"  test_files: {len(_state.test_files) if _state.test_files else 0}\")
print(f\"  by_cpp_name: {len(_state.by_cpp_name) if _state.by_cpp_name else 0}\")
" 2>&1
INIT_RC=$?
if [ $INIT_RC -eq 124 ]; then
    echo "  TIMEOUT: init_from_source exceeded 5 minutes"
elif [ $INIT_RC -ne 0 ]; then
    echo "  FAILED with exit code ${INIT_RC}"
fi

echo ""
echo "=== Step 4: Test affected_tests with C++ file (2min timeout) ==="
timeout 120 python -c "
import time, sys
from torchtalk.indexer import _init_from_source, _state
from torchtalk.analysis.affected import affected_tests, symbols_in_file

_init_from_source(\"/pytorch\")

if _state.cpp_extractor is None:
    print(\"  Skipped: cpp_extractor not available\")
    sys.exit(0)

test_file = \"aten/src/ATen/native/Linear.cpp\"
start = time.time()
result = symbols_in_file(test_file, _state.cpp_extractor)
funcs = [f[\"function\"] for f in result.get(\"functions\", [])]
print(f\"  symbols_in_file: {len(funcs)} symbols in {time.time()-start:.1f}s\")

if not funcs:
    print(\"  No symbols found, skipping affected_tests\")
    sys.exit(0)

start = time.time()
tests = affected_tests(
    funcs=funcs,
    cpp_extractor=_state.cpp_extractor,
    by_cpp_name=_state.by_cpp_name,
    test_classes=_state.test_classes,
    test_files=_state.test_files,
    opinfo_registry=_state.opinfo_registry,
    opinfo_alias_map=_state.opinfo_alias_map,
    opinfo_test_files=_state.opinfo_test_files,
    test_attr_index=_state.test_attr_index,
    python_profiling=_state.python_profiling or None,
    decomp_alias_map=_state.decomp_alias_map or None,
    backward_to_forward=_state.backward_to_forward or None,
    native_functions=_state.native_functions or None,
    native_implementations=_state.native_implementations or None,
    depth=3,
)
print(f\"  affected_tests: {len(tests)} tests in {time.time()-start:.1f}s\")
for t in tests[:5]:
    print(f\"    {t}\")
" 2>&1
STEP4_RC=$?
if [ $STEP4_RC -eq 124 ]; then
    echo "  TIMEOUT: affected_tests exceeded 2 minutes"
elif [ $STEP4_RC -ne 0 ]; then
    echo "  FAILED with exit code ${STEP4_RC}"
fi

echo ""
echo "================================================"
echo "Test complete"
echo "================================================"
'
