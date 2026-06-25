# SmartFarmKorea 데이터마트 클라이언트

기존 `SBAPIClient`는 2024 스마트농업 AI 경진대회용 제어 API에 맞춰져 있습니다.
스마트팜코리아 OPEN-API는 구조가 달라서 `SmartFarmKoreaClient`를 새로 추가했습니다.

## 설치

```powershell
py -m pip install -r requirements.txt
```

## 서비스키

스마트팜코리아 OPEN-API 신청 후 발급받은 서비스키를 환경변수로 넣어두고 사용합니다.

```powershell
$env:SMARTFARMKOREA_SERVICE_KEY="발급받은_서비스키"
```

## 기본 사용

```python
import os

from libsbapi import SmartFarmKoreaClient

client = SmartFarmKoreaClient(os.environ["SMARTFARMKOREA_SERVICE_KEY"])

rows = client.get_item_facility_info_data_list()
strawberry_rows = [row for row in rows if row.get("itemCode") == "080400"]

print(len(strawberry_rows))
print(strawberry_rows[0])
```

## 주요 메서드

- `get_identity_data_list()`
- `get_cropping_season_data_list(user_id)`
- `get_env_data_list(facility_id, meas_date, fld_code, sect_code, fatr_code, item_code)`
- `get_strawberry_cultivate_data_list(user_id, cropping_serl_no, start_date, end_date)`
- `get_item_facility_info_data_list()`
- `get_item_facility_date_info_data_list(facility_id)`
- `get_item_env_info_data_list(facility_id, crpsn_sn, item_code, fix_plntng_de, crpsn_end_de)`
- `get_item_control_info_data_list(facility_id, crpsn_sn, item_code, fix_plntng_de, crpsn_end_de)`
- `get_item_examin_info_data_list(facility_id, crpsn_sn, fix_plntng_de, crpsn_end_de)`

## 2026 기준 데이터 범위

스마트팜코리아 OPEN-API의 `스마트팜 빅데이터 제공서비스`는 시설원예 환경/제어/생육/경영 실시간 수집데이터이며, 공식 페이지 기준 데이터 수집년도는 2015년부터 2026년까지입니다.

반면 `품목별 데이터셋 제공서비스`는 농가 품목기준 조회용 데이터마트 개방데이터이고, 공식 페이지 기준 데이터 수집년도는 2015년부터 2024년까지이며 작기 종료 후 연 단위로 적재됩니다. 시설원예 데이터셋 화면은 딸기, 토마토, 방울토마토, 오이, 파프리카의 환경정보, 제어정보, 생육정보, 경영정보를 안내합니다.

- 스마트팜 빅데이터 제공서비스: https://www.smartfarmkorea.net/openApi/openApiList.do?menuId=M1104030101
- 품목별 데이터셋 제공서비스: https://www.smartfarmkorea.net/openApi/openApiList.do?menuId=M1104030104
- 시설원예 데이터셋: https://www.smartfarmkorea.net/datamart/fclty/list.do

문서에 있는 다른 API도 `request(service, operation, *params)`로 바로 호출할 수 있습니다.

```python
rows = client.request(
    client.ITEM_SERVICE,
    "getEnvInfoDataList",
    "PF_0010069_01",
    2262,
    "080400",
    "2019-09-10",
    "2020-06-10",
)
```

## BerryNext AI와 연결

스마트팜코리아 API에서 가져온 데이터는 `BerryNextDecisionEngine`의 입력으로 정리할 수 있습니다.
이 엔진은 관수, EC/양액 조정 검토, 환기, 차광, 보온/난방 검토를 Level 1 추천 범위로 다룹니다.
병해 위험 예찰, 수확 가능성, 적엽 검토는 검증된 핵심 예측이 아니라 Level 2 보조 알림으로만 다룹니다.

```python
from libsbapi import BerryNextDecisionEngine, GreenhouseSnapshot, ImageGrowthSignals, WeatherForecast

snapshot = GreenhouseSnapshot(
    inside_temperature_c=26.0,
    inside_humidity_pct=88.0,
    solar_radiation_w_m2=520.0,
    root_zone_moisture_pct=34.0,
    ec=1.4,
    ph=6.1,
    vent_open_pct=10.0,
    weather=WeatherForecast(rain_probability=70.0, expected_rain_mm=6.0),
    image=ImageGrowthSignals(ripe_fruit_ratio=0.82, average_fruit_size_mm=31.0),
)

engine = BerryNextDecisionEngine()
for recommendation in engine.recommend(snapshot):
    print(recommendation.action, recommendation.priority, recommendation.reason)
```

## 오늘 할 일 추천

농작업 의사결정 AI는 `DailyFarmWorkDecisionEngine`을 사용합니다.
생육단계, 온실환경, 이미지/예찰, 작업이력을 `FarmWorkContext`로 합칠 수 있지만, 작업이력은 지도학습 라벨이 아니라 안전 간격, cooldown, 설명 근거로만 사용합니다.
새 방향에서는 관수, EC/양액 조정, 환기, 차광, 보온/난방 검토를 Level 1 추천으로 고정하고, 병해 예찰, 수확 가능성, 적엽 검토는 Level 2 보조 알림으로 분리합니다.

실제 `딸기 전기`, `딸기 펠릿` 엑셀 데이터셋의 컬럼 매핑과 전처리 방향은 `DATASET_MAPPING_KO.md`에 정리되어 있습니다.

```python
from libsbapi import (
    CropGrowthStage,
    DailyFarmWorkDecisionEngine,
    FarmWorkContext,
    FarmWorkHistory,
    GreenhouseSnapshot,
    ImageGrowthSignals,
    WeatherForecast,
)

context = FarmWorkContext(
    growth_stage=CropGrowthStage.HARVEST,
    snapshot=GreenhouseSnapshot(
        inside_temperature_c=27.5,
        inside_humidity_pct=91.0,
        solar_radiation_w_m2=540.0,
        root_zone_moisture_pct=31.0,
        vent_open_pct=8.0,
        weather=WeatherForecast(rain_probability=75.0, expected_rain_mm=7.0),
        image=ImageGrowthSignals(
            ripe_fruit_ratio=0.86,
            average_fruit_size_mm=31.0,
            fruit_count=52,
            leaf_density=0.88,
            disease_spot_ratio=0.04,
        ),
    ),
    history=FarmWorkHistory(
        days_since_irrigation=2,
        days_since_scouting=5,
        days_since_disease_control=11,
        days_since_harvest=3,
        days_since_leaf_pruning=12,
    ),
)

plan = DailyFarmWorkDecisionEngine().plan_today(context)
print(plan.summary)
for task in plan.tasks:
    print(task.title, task.timing, task.priority, task.reason)
```

예제는 다음 명령으로 실행할 수 있습니다.

```powershell
py -m examples.daily_farmwork
```
