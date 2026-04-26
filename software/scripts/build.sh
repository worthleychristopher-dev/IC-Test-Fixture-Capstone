#!/bin/bash

set -e

echo "Building executable..."

pyinstaller --onefile --noconsole --name ICTestFixture src/ic_test_fixture/main.py

echo "Build complete, appending checksum..."

python scripts/append_checksum.py dist/ICTestFixture

echo "Cleaning build artifacts..."

rm -rf build __pycache__ ICTestFixture.spec

echo "Done"
