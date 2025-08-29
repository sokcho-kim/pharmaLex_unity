# -*- coding: utf-8 -*-
# run_all.py
import sys
import subprocess
import shutil
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent

def run(cmd: list[str]):
    print("[RUN]", " ".join([str(x) for x in cmd]))
    subprocess.check_call(cmd)

def main():
    cfg_path = HERE / "config.yaml"
    if not cfg_path.exists():
        print(f"[ERR] config.yaml not found: {cfg_path}")
        sys.exit(1)

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_dir = HERE / cfg["paths"]["data_dir"]
    out_dir  = HERE / cfg["paths"]["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    list_xlsx = data_dir / cfg["inputs"]["hira_list_xlsx"]
    atc_csv   = data_dir / cfg["inputs"]["atc_csv"]
    subm_csv  = data_dir / cfg["inputs"]["substance_master_csv"]

    # sanity check
    for p in [list_xlsx, atc_csv, subm_csv]:
        if not Path(p).exists():
            print(f"[ERR] file missing: {p}")
            sys.exit(2)

    # 1) 동치어 사전 생성
    run([
        sys.executable, str(HERE / "build_synonyms.py"),
        "--list_xlsx", str(list_xlsx),
        "--atc_csv",   str(atc_csv),
        "--out_dir",   str(out_dir),
    ])

    # 2) 분류↔주성분/제품 교차표
    run([
        sys.executable, str(HERE / "build_class_maps.py"),
        "--list_xlsx",     str(list_xlsx),
        "--submaster_csv", str(subm_csv),
        "--out_dir",       str(out_dir),
    ])

    print("\n[OK] 모든 산출물이 생성되었습니다.")
    print(f"     출력 폴더: {out_dir.resolve()}")

if __name__ == "__main__":
    main()
