# libsbapi
제4회 스마트 농업 인공지능 경진대회용 라이브러리

## 소개
제4회 스마트농업 인공지능 경진대회 API 를 활용하기위한 파이썬라이브러리이다.
pyModbusTCP (https://github.com/sourceperl/pyModbusTCP) 의 코드를 활용하였다.

별도의 API 문서에서 소개되겠지만, 경진대회 API 의 컨텐츠는 KS X 3267, KS X 3286, KS X 3288 스마트온실 통신 표준을 기반으로 구성되었다. 

BerryNext AI는 이 라이브러리 위에 생육단계, 온실환경, 이미지/예찰, 작업이력을 합쳐 농부가 오늘 해야 할 방제, 관수, 수확, 적엽 작업의 우선순위를 추천하는 농작업 의사결정 AI 구조를 추가한다.

## BerryNext 목표

이 저장소의 BerryNext 확장 목표는 딸기 스마트팜에서 농업인이 매일 판단하던 농작업 시점을 데이터로 보조하는 것이다.

- 관수/양액: 일사, VPD, 지습, EC/pH, 배액 신호를 이용해 오늘 관수 필요도와 주의사항을 판단한다.
- 방제/예찰: 고습, 낮은 VPD, 강우, 환기 부족, 예찰 공백을 이용해 병해충 위험과 예찰 우선순위를 판단한다.
- 수확: 생육단계, 착과/성숙 이미지 신호, 가격/출하 정보를 이용해 수확 우선순위를 판단한다.
- 적엽: 엽수, 잎 밀도, 고습, 최근 적엽 이력을 이용해 과도한 적엽을 피하면서 필요한 작업만 추천한다.

관련 문서:

- `BERRYNEXT_AI_PLAN.md`: 농작업 의사결정 AI 전체 구조
- `DATASET_MAPPING_KO.md`: 딸기 전기/펠릿 실데이터 입력 매핑
- `STRAWBERRY_DATA_ROOM_KO.md`: 로컬 딸기 전용 자료 정리본 사용 기준

## 사용법

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

### BerryNext 오늘 할 일 추천

생육단계, 온실환경, 이미지/예찰, 작업이력을 합쳐 방제, 관수, 수확, 적엽 중 오늘 우선 실행할 농작업을 추천한다.

examples/daily_farmwork.py 에 샘플이 있다.
테스트는 현재 위치에서 다음과 같이 한다.

python3 -m examples.daily_farmwork

 
