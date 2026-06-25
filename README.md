# libsbapi
제4회 스마트 농업 인공지능 경진대회용 라이브러리

## 소개
제4회 스마트농업 인공지능 경진대회 API 를 활용하기위한 파이썬라이브러리이다.
pyModbusTCP (https://github.com/sourceperl/pyModbusTCP) 의 코드를 활용하였다.

별도의 API 문서에서 소개되겠지만, 경진대회 API 의 컨텐츠는 KS X 3267, KS X 3286, KS X 3288 스마트온실 통신 표준을 기반으로 구성되었다.

BerryNext is an explainable decision-support system that predicts short-term strawberry greenhouse environmental changes, compares candidate management actions through scenario simulation and literature/manual thresholds, and recommends today's priority actions for irrigation, EC/nutrient adjustment, ventilation, shading, and heat preservation.

## BerryNext 목표

이 저장소의 BerryNext 확장 목표는 딸기 스마트팜의 관리자가 센서 상태와 근거 규칙을 보고 오늘 검토할 온실 관리 작업을 설명 가능하게 정렬하도록 돕는 것이다. BerryNext는 농업인의 작업 선택을 작업이력 라벨로 지도학습하는 모델이 아니며, 온실 구동기를 자율 제어하는 시스템도 아니다.

Level 1 핵심 작업은 다음 5개로 고정한다.

- 관수: 지습, VPD, 일사, 예측 수분 변화로 관수 검토 필요도를 설명한다.
- EC/양액 조정 검토: 급액/배액 EC, pH, 배액률 신호로 양액 농도와 염류 집적 점검 필요도를 설명한다.
- 환기: 습도, VPD, 외기 조건, 결로/과습 위험으로 환기 또는 제습 검토 필요도를 설명한다.
- 차광: 고온, 고일사, 높은 VPD로 차광 또는 열부하 완화 검토 필요도를 설명한다.
- 보온/난방 검토: 저온, 야간 외기온, 생육단계 민감도로 보온 또는 난방 점검 필요도를 설명한다.

Level 2 보조 알림은 의사결정의 참고 신호로만 제공한다.

- 병해 위험 예찰 알림: 실제 병해 예측이나 방제 처방이 아니라 고습, 낮은 VPD, 강우, 엽면젖음 등 환경 기반 예찰 우선순위다.
- 수확 가능성 알림: 검증된 수확 시기 예측이 아니라 착색, 과실 수, 고온/강우 품질 위험을 보는 모니터링 알림이다.
- 적엽 검토 알림: 검증된 적엽 추천이 아니라 과습, 수관 밀도, 최근 작업 간격을 고려한 보수적 검토 알림이다.

작업이력이 입력에 포함되더라도 지도학습 라벨로 쓰지 않는다. 최근 관수, 양액 조정, 환기, 차광, 난방, 예찰, 수확, 적엽 기록은 반복 작업을 피하기 위한 안전 간격, cooldown, 설명 근거로만 사용한다.

권장 아키텍처:

```text
Sensor Data
→ Current State Builder
→ Environmental Predictor
→ Scenario Simulator
→ Threshold / Literature Rule Engine
→ Work-Need Scorer
→ Recommendation Generator
```

GAM은 작업을 직접 분류하는 모델이 아니라 단기 환경 변화량을 예측하는 Environmental Predictor 후보 중 하나다. 예측기는 `v0 no-change baseline`, `v1 rolling delta baseline`, `v2 linear regression`, `v3 GAM`, `v4 LSTM or Transformer` 순서로 확장한다. 약한 예측은 문헌/매뉴얼 규칙으로 fallback해야 하며, 시나리오 시뮬레이션 결과를 가짜 지도학습 라벨로 만들어서는 안 된다.

관련 문서:

- `BERRYNEXT_AI_PLAN.md`: BerryNext 의사결정 보조 구조
- `docs/current_state_builder.md`: Current State Builder
- `docs/environmental_prediction.md`: Environmental Predictor
- `docs/scenario_simulation.md`: Scenario Simulator
- `docs/rule_engine.md`: Threshold / Literature Rule Engine
- `docs/work_need_scorer.md`: Work-Need Scorer
- `docs/recommendation_generator.md`: Recommendation Generator
- `DATASET_MAPPING_KO.md`: 딸기 전기/펠릿 실데이터 입력 매핑
- `STRAWBERRY_DATA_ROOM_KO.md`: 로컬 딸기 전용 자료 정리본 사용 기준

## BerryNext Quickstart

외부 API 키나 온실 하드웨어 없이 최종 의사결정 보조 파이프라인을 실행한다.

```bash
python3 -m examples.berrynext_today_recommendation
```

시나리오 후보 비교만 따로 확인한다.

```bash
python3 -m examples.greenhouse_scenario_compare
```

Streamlit 대시보드는 선택 기능이다.

```bash
pip install streamlit
streamlit run dashboard/greenhouse_dashboard.py
```

현재 환경에 Streamlit이 없으면 `python3 dashboard/greenhouse_dashboard.py`가 설치 안내를 출력하고 종료한다.

## BerryNext 현재 제한

- GAM은 아직 학습/검증되어 통합된 모델이 아니다. 현재 오프라인 데모는 v0 no-change baseline과 규칙 기반 fallback을 사용한다.
- 문헌/매뉴얼 임계값은 로컬 캘리브레이션 전까지 provisional rule이다.
- 시간 단위 센서 이력은 baseline predictor에 연결할 수 있지만, 충분한 실제 운영 이력 기반 검증은 아직 남아 있다.
- 단위, 센서 품질, 결측치 검증은 현재 상태 builder에서 노출하지만 농가별 표준화는 추가 검토가 필요하다.
- 병해, 수확, 적엽은 Level 2 보조 알림이다. 이미지/예찰 데이터와 검증 테스트 없이는 실제 병해 예측, 검증된 수확 예측, 검증된 적엽 처방으로 표현하지 않는다.

## BerryNext 로드맵

- v0.1: sample context 기반 current state, baseline prediction, rule/scenario 기반 score, offline recommendation demo.
- v0.2: 시간 단위 센서 이력 연결, rolling delta baseline 개선, 데이터 품질 리포트 강화.
- v0.3: 문헌/매뉴얼 rule citation 정리와 농가별 threshold calibration.
- v0.5: GAM-ready feature table, confidence gate, baseline 대비 검증 지표.
- v1.0: 검증된 단기 환경 예측기를 recommendation pipeline에 연결하되, 출력은 계속 human-reviewed decision support로 유지.

## 사용법

Python 3.11 이상에서 실행한다. BerryNext 작업 추천 모듈이 표준 라이브러리 `StrEnum`을 사용한다.

### 초기화

팀별로 할당된 키를 사용하여 모듈을 초기화한다. Authorization key 는 팀별로 할당되는 비밀키이다.

client = SBAPIClient("Authorization key")

### 데이터 읽기

데이터를 읽어오기 위해서는 read_holding_registers 함수를 사용한다.

reg = client.read_holding_registers(start_address, number_of_registers, unit_id, retry)

정상적인 읽기가 되었다면, reg 는 읽어온 레지스터의 배열이다.
start_address : 읽기 시작할 주소
number_of_registers : 읽을 레지스터 개수
unit_id : 슬레이브 아이디라고도 하며, 노드의 아이디
retry : 3 이 디폴트 값이며, 읽기를 실패할 경우 재시도 회수

### 데이터 쓰기

데이터를 쓰기 위해서는 write_multiple_registers 함수를 사용한다.

ret = client.write_multiple_registers(start_address, list_of_values, unit_id, retry)

정상적인 쓰기가 되었다면, ret는 True 를 리턴한다.
start_address : 쓰기 시작할 주소
list_of_values : 레지스터에 기록할 값들의 배열(리스트)
unit_id : 슬레이브 아이디라고도 하며, 노드의 아이디
retry : 3 이 디폴트 값이며, 읽기를 실패할 경우 재시도 회수

## 예시

### 센서값 읽어오기
센서값을 읽을 수 있다.
샘플에서는 2번 슬레이브(유닛아이디 2)에 있는 일사, 풍속, 풍향과 3번 슬레이브(유닛아이디 3)에 있는 온도, 습도 데이터를 읽는다.

examples/read_sensor.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.read_sensor

### 제어권 확인 및 바꾸기
인공지능을 활용하여 제어를 수행할때는 노드의 제어권을 변경해야한다.
인공지능 제어를 하지 않을때에는 제어권을 로컬로 변경해두면 기존의 설정으로 작동한다.

examples/control_priv.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.control_priv

### 스위치와 개폐기
스위치와 개폐기는 모두 4번 슬레이브에 연결되어 있다.
대회에서는 레벨 1 스위치와 레벨 1 개폐기만 지원한다.

#### 스위치 작동시키기
스위치는 ON, OFF, TIMED_ON (일정시간 작동) 명령이 가능하다.
샘플에서는 4번 슬레이브(유닛아이디 4)에 있는 유동팬 1 (읽기는 204, 쓰기는 504)을 ON/OFF 한다.

examples/switch.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.switch

### 개폐기 작동시키기
개폐기는 OFF, OPEN, CLOSE, TIMED_OPEN (일정시간 열기), TIMED_CLOSE (일정시간 닫기) 명령이 가능하다.
샘플에서는 4번 슬레이브(유닛아이디 4)에 있는 천창1 (읽기는 236, 쓰기는 536)을 열었다 닫았다 한다.

examples/retractable.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.retractable

### 양액기 작동시키기
양액기는 5번 슬레이브에 연결되어 있다.
5번 슬레이브는 양액기 이외에도 EC, pH, 일사, 유량 센서를 가지고 있다.
양액기에 사용가능한 명령은 4가지 인데, 이 중 1회 관수 명령은 대회에서 활용하기에는 적합하지 않아서 사용을 추천하지 않는다.
그외 정지, 원수 관수(맹물 관수), 양액 관수(지정된 EC, pH) 명령을 활용할 수 있다.
양액기는 펌프, 밸브등 관수를 위해 작동시켜야할 서브 구동기들을 많이 가지고 있어, 반응이 전반적으로 느린편이다. 명령을 전달한 후 5초 정도 반응시간이 걸린다고 보면 된다.

examples/nutsupply.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.nutsupply

### BerryNext 오늘 온실 관리 추천

현재 온실 상태, 문헌/매뉴얼 규칙, 선택적 단기 예측을 바탕으로 관수, EC/양액 조정, 환기, 차광, 보온/난방 검토를 우선순위화한다. 병해 예찰, 수확 가능성, 적엽 검토는 Level 2 보조 알림으로만 표시한다.
코드 출력에서도 `tasks`는 Level 1 추천 전용이고, 병해 환경 위험 proxy, 수확 가능성, 적엽 검토는 `auxiliary_alerts` 아래에 분리된다.

메인 오프라인 데모는 외부 API 키 없이 실행된다.

```bash
python3 -m examples.berrynext_today_recommendation
```

출력은 `sample_daily_context.json`을 사용해 current state, 1-3시간 baseline 예측 상태, action scenario comparison, 문헌/매뉴얼 rule check, work-need score, Level 1 ranked recommendations, Level 2 auxiliary alerts를 순서대로 보여준다. 현재 데모 예측은 v0 no-change baseline이며, GAM은 향후 단기 환경 delta 예측기로 계획되어 있다. 모든 추천은 `decision_support`이며 사람 검토가 필요하다.

examples/daily_farmwork.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.daily_farmwork

### 논문 기반 규칙 시뮬레이터

구형 규칙 시뮬레이터는 관수, 방제, 수확, 적엽 작업의 방향성 효과를 확인하는 legacy 예제다. 새 추천 출력은 `docs/action_recommendations.md`의 Level 1/Level 2 구조를 우선한다.
논문 노트의 설향 EC 후보, 적산일사/배지수분/VWC 관수 트리거, 40-50% 배액률 목표, 환경성 병해 위험 proxy, 착색 모니터링 기준, 런너 제거와 과도 적엽 제한을 `evidence_tags`, `warnings`, `metrics`, `confidence`로 함께 남긴다.

examples/greenhouse_simulator.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.greenhouse_simulator

### 온실 시뮬레이션 시나리오 비교

구형 논문 기반 규칙 시뮬레이터를 여러 날에 걸쳐 실행해 무작업, 관수 중심, 방제+적엽, 즉시 수확, 수확 지연 시나리오의 최종 상태를 비교한다. 이 결과는 what-if 설명용이며, 자율 제어 명령이나 지도학습용 정답 라벨이 아니다.

examples/greenhouse_scenario_compare.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

### BerryNext 데모 시나리오

딸기 스마트팜 의사결정 보조 시스템의 현실적인 데모 입력은 `examples/scenarios/`에 있다.
5개 상황(고 VPD+저수분, 고습+저 VPD, 고 EC, 저온, 적엽 주의)을 추천 모듈과 what-if 시뮬레이터로 함께 실행한다. 앞의 4개는 Level 1 관리 작업 예시이고, 적엽 주의는 Level 2 보조 알림 예시다.

python3 scripts/run_demo_scenarios.py

결과는 `artifacts/demo_outputs/summary.json`과 `artifacts/demo_outputs/demo_report.md`에 저장된다.
자세한 설명은 `docs/demo_scenarios.md`를 참고한다.

python3 -m examples.greenhouse_scenario_compare

### 온실 시뮬레이터 대시보드

Streamlit 대시보드는 오프라인 BerryNext 오늘 추천 파이프라인을 먼저 보여준다. current state, 1-3시간 predicted state, action scenario comparison, work-need scores, recommendation reasons, auxiliary alerts가 섹션별로 분리된다. 외부 API 키는 필요하지 않다.

Streamlit은 선택 의존성이다. 설치되어 있지 않으면 대시보드 스크립트가 설치 명령을 안내하고 종료한다.

실행:

```bash
pip install streamlit
streamlit run dashboard/greenhouse_dashboard.py
```

대시보드의 두 번째 탭은 legacy what-if 시뮬레이터다. 결과 표에는 시나리오별 최종 상태와 논문 규칙의 `notes`, `warnings`, `evidence_tags`가 함께 표시된다.

### 샘플 JSON으로 오늘 할 일 추천하기

원본 엑셀과 대용량 CSV는 GitHub에 올리지 않는다. 대신 하루 단위로 정규화된 작은 JSON을 현재 상태 입력으로 변환해 의사결정 보조 엔진에 넣는 흐름을 제공한다.

샘플 입력:

```text
examples/sample_daily_context.json
```

실행:

```bash
python3 -m examples.build_daily_context
```

다른 날짜의 전처리 결과 JSON을 넣을 때:

```bash
python3 -m examples.build_daily_context path/to/daily_context.json
```

이 JSON은 나중에 `딸기_AI_의사결정_통합정리본/01_핵심_운영데이터`의 전기/펠릿 엑셀을 일 단위로 집계한 결과와 같은 계약으로 사용한다.
