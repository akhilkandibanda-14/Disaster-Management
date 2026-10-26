#!/usr/bin/env python
"""
CLI runner for SafeMap AI Local Flood Data Curation Pipeline.
Executes all reproducible data importers, validates raw inputs,
writes clean datasets to data/curated/, and generates data/data_manifest.json.
"""

import json
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.data_importers.curation_pipeline import SafeMapCurationPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_data_curation")


def main():
    root_dir = backend_dir.parent
    logger.info(f"Starting SafeMap AI Data Curation Pipeline from {root_dir}...")
    pipeline = SafeMapCurationPipeline(base_dir=root_dir)
    res = pipeline.run()

    print("\n" + "=" * 70)
    print("SAFEMAP AI — LOCAL FLOOD DATA CURATION PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Status: {res['status']}")
    print(f"Duration: {res['execution_duration_seconds']} seconds")
    print(f"Manifest written to: {res['manifest_file']}")
    print("-" * 70)

    for name, r in res["importer_results"].items():
        status = r.get("status")
        imported = r.get("records_imported") or r.get("daily_records_curated") or 0
        raw_sha = r.get("raw_sha256", "")[:12]
        print(f" • {name.ljust(20)}: {status} | Imported: {imported} | Raw SHA256: {raw_sha}...")

    print("=" * 70)
    print("Machine-readable manifest updated at data/data_manifest.json\n")


if __name__ == "__main__":
    main()
