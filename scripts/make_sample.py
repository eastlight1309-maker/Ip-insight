"""데모/테스트용 가상 DWPI 특허 엑셀 생성.

실행:  python scripts/make_sample.py
결과:  sample/sample_dwpi_patents.xlsx
"""

from __future__ import annotations

import os

import pandas as pd

ASSIGNEES = ["Samsung Electronics", "LG Chem", "TSMC", "Toyota", "BASF", "Sony", "Bosch"]
INVENTORS = ["Kim J", "Lee S", "Park H", "Chen W", "Sato T", "Müller K", "Garcia M"]
IPC = ["H01L21/02", "H01M10/052", "G06F3/041", "C08G73/10", "B60L58/12", "H04N19/00"]
DWPI_CLASS = ["L03", "X15", "T01", "A85", "W04"]
COUNTRIES = ["US", "KR", "JP", "CN", "EP", "DE"]

NOVELTIES = [
    "고에너지밀도 리튬 이차전지 음극 소재로서 실리콘-탄소 복합체를 사용.",
    "반도체 소자 미세 패터닝을 위한 EUV 포토레지스트 조성물.",
    "차량 배터리 열관리를 위한 냉각 유로 구조 및 제어 방법.",
    "온디바이스 추론을 위한 저전력 신경망 가속기 아키텍처.",
    "폴더블 디스플레이용 유연 투명 전극 및 봉지 구조.",
    "촉매 담지량을 높인 수소 연료전지 막전극접합체(MEA).",
]


def build(n: int = 120) -> pd.DataFrame:
    rows = []
    for i in range(n):
        year = 2013 + (i * 7) % 12
        rows.append(
            {
                "Publication Number": f"US{9000000 + i}B2",
                "Title": f"Patent example {i+1}",
                "DWPI Title": f"DWPI standardized title {i+1}",
                "DWPI Abstract": NOVELTIES[i % len(NOVELTIES)],
                "Assignee": ASSIGNEES[i % len(ASSIGNEES)],
                "Inventor": f"{INVENTORS[i % len(INVENTORS)]}; {INVENTORS[(i+3) % len(INVENTORS)]}",
                "Priority Date": f"{year}-0{(i % 9) + 1}-15",
                "Publication Date": f"{year + 1}-0{(i % 9) + 1}-20",
                "IPC": f"{IPC[i % len(IPC)]}; {IPC[(i+2) % len(IPC)]}",
                "CPC": IPC[(i + 1) % len(IPC)],
                "DWPI Class": f"{DWPI_CLASS[i % len(DWPI_CLASS)]}; {DWPI_CLASS[(i+1) % len(DWPI_CLASS)]}",
                "Country": COUNTRIES[i % len(COUNTRIES)],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(here, "sample")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "sample_dwpi_patents.xlsx")
    build().to_excel(path, index=False)
    print(f"생성 완료: {path}")


if __name__ == "__main__":
    main()
