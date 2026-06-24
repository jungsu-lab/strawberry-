# daily_context.json 스키마

`daily_context.json`은 하루 단위 농장 상태를 `DailyFarmWorkDecisionEngine`에 넣기 위한 입력 파일이다.

## 최상위

| 필드 | 타입 | 설명 |
|---|---|---|
| `farm_id` | string | `electric`, `pellet` 같은 데이터 구분자 |
| `date` | string | `YYYY-MM-DD` |
| `growth_stage` | string | `transplanting`, `vegetative`, `flowering`, `fruiting`, `harvest`, `resting` |
| `snapshot` | object | 온실/환경/생육 스냅샷 |
| `history` | object | 최근 작업 또는 조사 후 경과일 |
| `source_files` | string[] | 이 context를 만든 원본 파일 |

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
| `days_since_scouting` | integer/null | 가장 최근 생육 조사일 이후 경과일 |

## 출력 로그

`outputs/recommendation_logs/daily_recommendations.jsonl`은 한 줄에 하루/농장 하나의 추천 결과를 저장한다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `farm_id` | string | 농장/재배방식 구분 |
| `date` | string | 추천 대상 날짜 |
| `summary` | string | 상위 작업 요약 |
| `tasks` | object[] | 날짜별 추천 작업 목록 |
| `data_sources` | string[] | 추천에 사용한 데이터 범주 |

`tasks`의 주요 필드는 `work_type`, `timing`, `priority`, `score`, `title`, `reason`, `safeguards`, `metrics`다.
