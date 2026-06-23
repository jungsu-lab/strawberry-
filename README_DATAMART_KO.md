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
이 엔진은 관수/양액, 병해 위험도, 수확 시기 추천을 MVP 범위로 다룹니다.

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
