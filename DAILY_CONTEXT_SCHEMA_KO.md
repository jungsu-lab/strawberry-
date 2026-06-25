# daily_context.json 스키마

`daily_context.json`은 하루 단위 농장 상태를 추천 파이프라인에 넣기 위한 legacy 호환 입력 파일이다. 현재 일부 예제는 `DailyFarmWorkDecisionEngine`을 사용하지만, 최종 BerryNext 방향은 같은 정보를 `CurrentStateBuilder`로 `decision_contract.CurrentGreenhouseState`에 정규화한 뒤 Level 1 온실 관리 작업과 Level 2 보조 알림을 분리하는 것이다.

## 최상위

| 필드 | 타입 | 설명 |
|---|---|---|
| `farm_id` | string | `electric`, `pellet` 같은 데이터 구분자 |
| `date` | string | `YYYY-MM-DD` |
| `growth_stage` | string | `transplanting`, `vegetative`, `flowering`, `fruiting`, `harvest`, `resting` |
| `snapshot` | object | 온실/환경/생육 스냅샷 |
| `history` | object | 최근 작업 또는 조사 후 경과일. 지도학습 label이 아니라 안전 간격, cooldown, 설명용 정보 |
| `source_files` | string[] | 이 context를 만든 원본 파일 |

## Current State Builder 출력

`CurrentStateBuilder`는 legacy JSON의 `snapshot`을 다음 정규화 필드로 맞춘다.

| 정규화 필드 | legacy 입력 예 |
|---|---|
| `air_temp` | `inside_temperature_c` |
| `humidity` | `inside_humidity_pct` |
| `vpd` | `vpd`, `vpd_kpa`; 없으면 온도와 습도로 계산하고 fallback 표시 |
| `co2` | `co2_ppm` |
| `solar_radiation` | `solar_radiation_w_m2` |
| `root_zone_moisture` | `root_zone_moisture_pct` |
| `feed_ec`, `drain_ec`, `root_ec` | `feed_ec`, `drain_ec`, `ec`, `root_zone_ec` |
| `feed_ph`, `drain_ph` | `feed_ph`, `drain_ph`, `ph` |
| `drainage_ratio` | `drainage_ratio_pct` |
| `outside_temp`, `outside_humidity` | `snapshot.weather` 또는 snapshot 직접 필드 |
| `growth_stage`, `time_of_day`, `timestamp` | 최상위 또는 snapshot 필드 |

누락값은 임의로 채우지 않고 `None`으로 유지한다. 대신 `missing_fields`, `quality_warnings`, `assumed_units`, `source_labels`, `fallback_fields`, `suspicious_fields`, `stale_timestamp`, `sensor_quality`에 품질 정보를 남긴다. 0 값은 삭제하지 않으며, 센서 오류 가능성이 있는 0 값은 suspicious warning으로 표시한다.

## snapshot

| 필드 | 타입 | 설명 |
|---|---|---|
| `inside_temperature_c` | number/null | 내부 평균 온도 |
| `inside_humidity_pct` | number/null | 내부 평균 습도 |
| `co2_ppm` | number/null | 내부 평균 CO2 |
| `solar_radiation_w_m2` | number/null | 내부 일사량 평균, 없으면 외부 일사량 평균 |
| `root_zone_moisture_pct` | number/null | 토양/배지 수분 |
| `ec` | number/null | 배액 EC 또는 토양 EC |
| `ph` | number/null | 배액 pH 또는 토양 pH |
| `vent_open_pct` | number/null | 천창/측창 개도율 평균 |
| `weather` | object | 날씨/강우 proxy |
| `image` | object | 이미지 또는 생육 조사 기반 대체 신호 |

## snapshot.weather

| 필드 | 타입 | 설명 |
|---|---|---|
| `rain_probability` | number/null | 강우감지 시간 비율을 0-100으로 환산한 proxy |

## snapshot.image

| 필드 | 타입 | 설명 |
|---|---|---|
| `fruit_count` | integer/null | 화방착과수 합계 |
| `leaf_density` | number/null | 엽수 기반 잎 밀도 proxy, 0-1 |

## history

| 필드 | 타입 | 설명 |
|---|---|---|
| `days_since_scouting` | integer/null | 가장 최근 생육 조사일 이후 경과일. 예찰 보조 알림의 안전 간격/설명에만 사용 |

## 출력 로그

`outputs/recommendation_logs/daily_recommendations.jsonl`은 한 줄에 하루/농장 하나의 추천 결과를 저장한다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `farm_id` | string | 농장/재배방식 구분 |
| `date` | string | 추천 대상 날짜 |
| `summary` | string | 상위 작업 요약 |
| `tasks` | object[] | 날짜별 추천 작업 목록 |
| `data_sources` | string[] | 추천에 사용한 데이터 범주 |

`tasks`의 주요 필드는 `work_type`, `timing`, `priority`, `score`, `title`, `reason`, `safeguards`, `metrics`다. 이 legacy 로그의 `work_type`은 과거 호환 명칭을 포함할 수 있으므로, 새 문서와 발표에서는 Level 1 핵심 작업인 관수, EC/양액 조정 검토, 환기, 차광, 보온/난방 검토와 Level 2 보조 알림인 병해 예찰, 수확 가능성, 적엽 검토로 해석한다.
