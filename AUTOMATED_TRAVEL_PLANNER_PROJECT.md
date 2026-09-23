# Automated Travel Planner — Project Roadmap

## 1. Mục tiêu project

Xây dựng một hệ thống **AI Automated Travel Planner** có khả năng:

1. Nhận yêu cầu du lịch bằng ngôn ngữ tự nhiên.
2. Phân tích yêu cầu thành dữ liệu có cấu trúc.
3. Tìm kiếm destination, địa điểm, hoạt động, nhà hàng, phương tiện và chỗ ở.
4. Lập itinerary theo từng ngày.
5. Tính toán route và thời gian di chuyển.
6. Kiểm tra ngân sách và điều chỉnh kế hoạch.
7. Gợi ý souvenir / shopping.
8. Cho phép người dùng review và yêu cầu AI lập kế hoạch lại.
9. Export toàn bộ kế hoạch thành:
   - Excel `.xlsx`
   - Interactive map `.html`
   - JSON `.json`
10. Sử dụng các công nghệ:
   - LangGraph
   - MCP
   - A2A
   - CrewAI
   - OpenStreetMap
   - OSRM
   - Leaflet
   - OpenPyXL
   - Pydantic
   - Checkpoint / Memory
   - Human-in-the-loop

> **Nguyên tắc quan trọng:** LLM không trực tiếp tạo Excel hoặc tự đoán dữ liệu bản đồ.  
> Tất cả agent cùng thao tác trên một `TripState` có schema rõ ràng. Các exporter sẽ chuyển `TripState` thành Excel, Map và JSON.

---

# 2. Ví dụ user request

User có thể nhập:

```text
Tôi muốn đi Nhật 7 ngày vào tháng 11.

Ngân sách khoảng 2,000 USD.
Tôi thích:
- anime
- đồ ăn địa phương
- thiên nhiên
- văn hóa Nhật

Không muốn lịch trình quá dày.
Ưu tiên đi tàu.
Tôi muốn mua quà cho gia đình.
```

System cần biến request này thành một kế hoạch có cấu trúc.

Output cuối cùng:

```text
output/
├── itinerary.xlsx
├── map.html
└── trip.json
```

---

# 3. Kiến trúc tổng thể

```text
                         User
                           │
                           ▼
                Requirements Agent
                           │
                           ▼
                 Destination Research
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      Activity         Transport       Accommodation
       Agent              Agent              Agent
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    Route Optimizer
                           │
                           ▼
                     Budget Agent
                           │
                           ▼
                   Shopping Agent
                           │
                           ▼
                   Reviewer Agent
                           │
                    ┌──────┴──────┐
                    │             │
                   FAIL          PASS
                    │             │
                    ▼             ▼
                Re-plan         Export
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
               Excel             Map              JSON
```

---

# 4. Nguyên tắc kiến trúc

## 4.1 Single Source of Truth

Tất cả agent phải thao tác trên:

```python
TripState
```

Không để mỗi agent tự tạo một format dữ liệu riêng.

```text
                    TripState
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      Excel           Map            JSON
```

## 4.2 Phân biệt nguồn dữ liệu

### LLM-generated

LLM có thể tạo:

- user intent
- preferences
- candidate destinations
- candidate activities
- descriptions
- reasoning / suggestions

### Tool-generated

Tool/API phải cung cấp:

- latitude / longitude
- opening hours
- route
- distance
- travel duration
- weather
- external prices nếu có API
- place details

### Deterministically calculated

Code phải tính:

- total cost
- budget remaining
- duration
- schedule conflicts
- route duration
- daily utilization
- tổng số ngày
- thời gian rảnh

Không để LLM tự tính những dữ liệu quan trọng nếu có thể tính bằng code.

---

# 5. Data Models

Đây là phần cần hoàn thành trước khi xây dựng agent.

## 5.1 TripRequirements

Mô tả yêu cầu ban đầu của user.

Các field dự kiến:

```python
class TripRequirements:
    destination: str | None
    start_date: str | None
    end_date: str | None
    duration_days: int
    travelers: int

    budget: float | None
    currency: str

    interests: list[str]
    food_preferences: list[str]
    transport_preference: str | None

    accommodation_preference: str | None

    avoid: list[str]
    must_visit: list[str]
    shopping_preferences: list[str]
```

---

# 6. Place

Địa điểm chuẩn hóa.

```python
class Place:
    id: str
    name: str
    category: str

    address: str

    latitude: float
    longitude: float

    price: float | None
    currency: str | None

    opening_time: str | None
    closing_time: str | None

    url: str | None
```

Ví dụ:

```json
{
  "id": "place_tokyo_001",
  "name": "Senso-ji",
  "category": "temple",
  "address": "Asakusa, Tokyo",
  "latitude": 35.7148,
  "longitude": 139.7967
}
```

---

# 7. Activity

```python
class Activity:
    id: str

    place_id: str

    day: int

    start_time: str
    end_time: str

    title: str
    description: str

    cost: float
    currency: str
```

---

# 8. Transportation

```python
class Transportation:
    id: str

    from_place_id: str
    to_place_id: str

    mode: str

    departure_time: str | None
    arrival_time: str | None

    duration_minutes: int
    distance_km: float

    cost: float
    currency: str
```

---

# 9. Route

Route được tạo từ routing engine, không phải LLM.

```python
class Route:
    from_place_id: str
    to_place_id: str

    mode: str

    duration_minutes: int
    distance_km: float

    geometry: dict
```

`geometry` có thể là GeoJSON.

---

# 10. Accommodation

```python
class Accommodation:
    id: str

    name: str
    address: str

    latitude: float
    longitude: float

    check_in: str
    check_out: str

    price_per_night: float
    total_price: float
    currency: str

    rating: float | None
    url: str | None
```

---

# 11. Souvenir

```python
class Souvenir:
    id: str

    name: str
    category: str

    recipient: str

    price: float
    currency: str

    place_id: str
    day: int

    priority: str
```

Ví dụ:

```json
{
  "id": "souvenir_001",
  "name": "Matcha",
  "category": "food",
  "recipient": "family",
  "price": 20,
  "currency": "USD",
  "place_id": "kyoto_001",
  "day": 4,
  "priority": "high"
}
```

---

# 12. BudgetItem

```python
class BudgetItem:
    category: str

    description: str

    amount: float
    currency: str

    day: int | None
```

Các category:

```text
Accommodation
Transportation
Food
Activities
Shopping
Miscellaneous
```

---

# 13. DayPlan

```python
class DayPlan:
    day: int

    date: str

    activities: list[Activity]
    transportation: list[Transportation]

    estimated_cost: float
```

---

# 14. TripState

Đây là object quan trọng nhất của hệ thống.

```python
class TripState:
    requirements: TripRequirements

    destinations: list[Place]

    places: list[Place]

    activities: list[Activity]

    transportation: list[Transportation]

    accommodations: list[Accommodation]

    routes: list[Route]

    souvenirs: list[Souvenir]

    budget_items: list[BudgetItem]

    daily_plans: list[DayPlan]

    total_cost: float
    remaining_budget: float

    review_errors: list[str]

    status: str
```

---

# 15. Project Phases

## Phase 0 — Project Setup

### Mục tiêu

Tạo project Python cơ bản.

### Tasks

- [x] Tạo repository
- [x] Tạo virtual environment
- [x] Tạo `pyproject.toml`
- [x] Cấu hình `.env`
- [ ] Cấu hình logging
- [ ] Cấu hình pytest
- [x] Tạo folder structure

### Expected output

```text
automated-travel-planner/
├── src/
├── tests/
├── data/
├── output/
├── .env
├── pyproject.toml
└── README.md
```

---

# Phase 1 — Data Schema

### Mục tiêu

Hoàn thành toàn bộ Pydantic models.

### Tasks

- [x] `TripRequirements`
- [x] `Place`
- [x] `Activity`
- [x] `Transportation`
- [x] `Accommodation`
- [x] `Route`
- [x] `Souvenir`
- [x] `BudgetItem`
- [x] `DayPlan`
- [x] `TripState`

### Tests

Kiểm tra:

- required fields
- default values
- enum values
- invalid data
- serialization
- JSON output

### Expected result

Có thể chạy:

```python
trip_state.model_dump()
```

và nhận được JSON hợp lệ.

---

# Phase 2 — Basic Trip Planner

### Mục tiêu

Từ natural language tạo `TripRequirements`.

Flow:

```text
User Request
     │
     ▼
Requirements Agent
     │
     ▼
TripRequirements
```

Ví dụ:

```text
"I want to visit Japan for 7 days,
budget $2000, love anime and food."
```

thành:

```json
{
  "destination": "Japan",
  "duration_days": 7,
  "budget": 2000,
  "currency": "USD",
  "interests": [
    "anime",
    "food"
  ]
}
```

### Tasks

- [x] Tạo Requirements Agent
- [x] Structured output bằng Pydantic
- [x] Validate output

---

# Phase 3 — LangGraph

### Mục tiêu

Chuyển workflow sang LangGraph.

Graph đầu tiên:

```text
START
  │
  ▼
requirements
  │
  ▼
destination
  │
  ▼
activities
  │
  ▼
END
```

### Tasks

- [x] Tạo `StateGraph`
- [x] Tạo nodes
- [x]Tạo edges
- [x] Compile graph
- [x] Test graph
- [x] Stream graph execution

---

# Phase 4 — Destination Agent

### Mục tiêu

Tìm destination / city / area phù hợp.

Input:

```text
TripRequirements
```

Output:

```text
list[Place]
```

### Tasks

- [x] Tạo Destination Agent
- [x] Search places
- [x] Normalize result thành `Place`
- [x] Deduplicate places
- [x] Lưu vào `TripState`

---

# Phase 5 — MCP Places Server

### Mục tiêu

Đưa khả năng search dữ liệu ra MCP.

Server:

```text
places-mcp
```

Tools:

```text
search_places
get_place_details
search_restaurants
```

Ví dụ:

```text
Agent
  │
  ▼
MCP Client
  │
  ▼
places-mcp
  │
  ▼
Places API / OpenStreetMap
```

### Tasks

- [ ] Tạo MCP server
- [ ] Implement `search_places`
- [ ] Implement `get_place_details`
- [ ] Implement restaurant search
- [ ] Test MCP tools
- [ ] Kết nối LangGraph agent với MCP

---

# Phase 6 — Activity Agent

### Mục tiêu

Tạo danh sách activities.

Flow:

```text
Destination
      │
      ▼
Activity Agent
      │
      ▼
Candidate Activities
      │
      ▼
TripState.activities
```

### Tasks

- [x] Search attractions
- [x] Search restaurants
- [x] Search cultural activities
- [x] Search nature activities
- [x] Match activities với interests
- [x] Remove duplicates

---

# Phase 7 — Routing

### Mục tiêu

Tính route thật giữa các địa điểm.

Stack:

```text
OpenStreetMap
      │
      ▼
    OSRM
      │
      ▼
   GeoJSON
      │
      ▼
    Route
```

### Tasks

- [ ] Tạo `routing-mcp`
- [ ] Implement `calculate_route`
- [ ] Implement `calculate_distance_matrix`
- [ ] Parse OSRM response
- [ ] Convert geometry thành GeoJSON
- [ ] Lưu `Route` vào TripState

### Important

Không để LLM tự nói:

```text
Senso-ji → Shibuya mất 20 phút
```

Mà phải:

```text
LLM candidate
     ↓
OSRM
     ↓
duration / distance
```

---

# Phase 8 — Route Optimization

### Mục tiêu

Sắp xếp activities hợp lý theo vị trí và thời gian.

Input:

```text
Activities
+
Routes
+
Opening Hours
```

Output:

```text
Daily Plans
```

Pipeline:

```text
Candidate Places
       │
       ▼
OSRM Distance Matrix
       │
       ▼
Optimization Algorithm
       │
       ▼
Daily Plan
```

### Tasks

- [ ] Tạo distance matrix
- [ ] Group places theo khu vực
- [ ] Kiểm tra opening hours
- [ ] Tính travel time
- [ ] Detect schedule conflicts
- [ ] Optimize order
- [ ] Generate `DayPlan`

---

# Phase 9 — Transportation Agent

### Mục tiêu

Tạo kế hoạch transportation.

Có thể xử lý:

```text
Flight
Train
Metro
Bus
Taxi
Walking
```

### Tasks

- [x] Transportation model
- [x] Search transport options
- [x] Estimate cost
- [x] Estimate duration
- [ ] Integrate với daily plan
- [ ] Detect impossible connections

---

# Phase 10 — Accommodation Agent

### Mục tiêu

Tìm accommodation.

### Tasks

- [x] Search hotels
- [x] Filter theo budget
- [x] Filter theo location
- [x] Filter theo preferences
- [x] Add accommodation vào TripState

---

# Phase 11 — Budget Agent

### Mục tiêu

Tính tổng ngân sách.

```text
Accommodation
+
Transportation
+
Food
+
Activities
+
Shopping
+
Misc
      │
      ▼
   TOTAL
```

### Tasks

- [ ] Calculate category totals
- [ ] Calculate total
- [ ] Calculate remaining budget
- [ ] Detect budget overflow
- [ ] Suggest reductions

### Important

Tổng tiền phải được tính bằng code.

Ví dụ:

```python
total = sum(item.amount for item in budget_items)
```

Không để LLM tính tổng.

---

# Phase 12 — Shopping / Souvenir Agent

### Mục tiêu

Tạo danh sách quà / souvenir.

Input:

```text
TripRequirements
+
DailyPlan
+
Places
```

Output:

```text
Souvenirs
```

### Ví dụ

```text
Day 2 — Akihabara

- Anime figure
- Manga
- Character goods
```

```text
Day 4 — Kyoto

- Matcha
- Japanese sweets
- Traditional crafts
```

### Tasks

- [ ] Tạo Shopping Agent
- [ ] Search shopping areas
- [ ] Search souvenir
- [ ] Estimate prices
- [ ] Link souvenir → Place
- [ ] Link souvenir → DayPlan
- [ ] Add Shopping vào Budget

---

# Phase 13 — Reviewer Agent

### Mục tiêu

Reviewer kiểm tra toàn bộ itinerary.

Các rule cần kiểm tra:

```text
Budget
Time
Distance
Opening hours
Transportation
Duplicate places
Overloaded days
Missing meals
Missing free time
```

Output:

```python
review_errors: list[str]
```

Ví dụ:

```text
[
  "Day 3 has 9 activities and may be overloaded.",
  "Activity X starts before the previous route finishes.",
  "Budget exceeds limit by $180."
]
```

---

# Phase 14 — Re-planning Loop

LangGraph phải hỗ trợ loop.

```text
Reviewer
   │
   ├── PASS ────────► Export
   │
   └── FAIL
          │
          ▼
      Re-planner
          │
          ▼
       Reviewer
```

### Tasks

- [ ] Conditional edge
- [ ] Retry limit
- [ ] Re-planning strategy
- [ ] Prevent infinite loop
- [ ] Preserve previous state

Ví dụ:

```text
max_iterations = 3
```

---

# Phase 15 — Human-in-the-loop

### Mục tiêu

Cho user duyệt itinerary trước khi export.

```text
AI Proposed Trip

[Approve]
[Modify]
```

Nếu user nói:

```text
Giảm budget xuống $1500.
Bỏ Osaka.
Thêm một ngày ở Kyoto.
```

Graph tiếp tục chạy từ checkpoint.

### Tasks

- [ ] LangGraph interrupt
- [ ] Save checkpoint
- [ ] Resume graph
- [ ] Parse user modifications
- [ ] Re-run necessary agents

---

# Phase 16 — Memory

Memory và checkpoint là hai thứ khác nhau.

## Memory

Lưu thông tin lâu dài:

```json
{
  "preferences": {
    "transport": "train",
    "food": "local",
    "avoid": [
      "early flights"
    ]
  }
}
```

## Checkpoint

Lưu trạng thái workflow hiện tại:

```text
TripState
current_node
iteration
pending_action
```

### Tasks

- [ ] Tạo Memory MCP
- [ ] `memory_get`
- [ ] `memory_set`
- [ ] Connect user preferences
- [ ] Tách Memory khỏi checkpoint

---

# Phase 17 — Excel Exporter

### Mục tiêu

Generate:

```text
itinerary.xlsx
```

Library:

```text
openpyxl
```

Workbook:

```text
Overview
Daily Plan
Places
Transportation
Budget
Souvenirs
Map Data
```

---

## Sheet: Overview

Thông tin:

```text
Destination
Start Date
End Date
Travelers
Budget
Estimated Total
Remaining Budget
```

Có thể thêm:

```text
Open Interactive Map
```

là hyperlink tới `map.html`.

---

## Sheet: Daily Plan

Columns:

```text
Day
Start
End
Location
Type
Activity
Transport
Travel Time
Price
Currency
Booking
Notes
```

Một activity = một row.

---

## Sheet: Places

```text
ID
Name
Category
Address
Latitude
Longitude
Price
Opening
URL
```

---

## Sheet: Transportation

```text
From
To
Mode
Departure
Arrival
Duration
Distance
Cost
```

---

## Sheet: Budget

```text
Category
Amount
```

Ví dụ:

```text
Accommodation   $600
Transportation  $300
Food            $400
Activities      $250
Shopping        $150
Miscellaneous   $100
--------------------
TOTAL           $1800
BUDGET          $2000
REMAINING       $200
```

---

## Sheet: Souvenirs

```text
Item
Category
Where to Buy
Estimated Price
Recommended For
Day
Priority
```

---

## Sheet: Map Data

```text
ID
Day
Sequence
Name
Lat
Lng
Type
```

Không nên nhét toàn bộ GeoJSON lớn vào Excel.

GeoJSON nên được lưu riêng:

```text
output/
├── itinerary.xlsx
├── map.html
├── routes.geojson
└── trip.json
```

---

# Phase 18 — Interactive Map

### Mục tiêu

Generate:

```text
map.html
```

Stack:

```text
OpenStreetMap
     │
     ▼
   OSRM
     │
     ▼
   GeoJSON
     │
     ▼
   Leaflet
     │
     ▼
 map.html
```

### Map features

- [ ] Marker cho từng location
- [ ] Popup
- [ ] Route polyline
- [ ] Day filter
- [ ] Activity information
- [ ] Cost
- [ ] Start / End time
- [ ] Different layer cho từng ngày
- [ ] Legend

Popup:

```text
Day 2

10:00 - 12:00
Senso-ji

Category: Temple
Price: Free
```

---

# Phase 19 — JSON Export

Generate:

```text
trip.json
```

Ví dụ:

```json
{
  "trip": {},
  "places": [],
  "activities": [],
  "routes": [],
  "transportation": [],
  "accommodation": [],
  "souvenirs": [],
  "budget": {}
}
```

JSON là format thuận tiện để:

- debug
- API
- frontend
- import/export
- test

---

# Phase 20 — A2A

Sau khi local architecture chạy ổn mới thêm A2A.

Mục tiêu:

```text
Main LangGraph
       │
       ├── A2A → Hotel Agent
       │
       ├── A2A → Transport Agent
       │
       └── A2A → Research Agent
```

### Tasks

- [ ] Tạo independent agent service
- [ ] Agent card
- [ ] A2A endpoint
- [ ] A2A client
- [ ] Request / response schema
- [ ] Timeout
- [ ] Error handling

---

# Phase 21 — CrewAI

Dùng CrewAI cho một nhóm chuyên gia nghiên cứu destination.

Ví dụ:

```text
Destination Research Team
│
├── Food Analyst
├── Culture Analyst
└── Nature Analyst
```

CrewAI team tạo candidate recommendations.

Sau đó:

```text
CrewAI
   │
   ▼
Research Result
   │
   ▼
A2A
   │
   ▼
LangGraph
```

Mục tiêu của phase này là thể hiện rõ:

```text
LangGraph = orchestration
CrewAI   = internal agent/team
A2A      = agent-to-agent communication
MCP      = agent-to-tool communication
```

---

# Phase 22 — Observability

Thêm tracing / observability.

Theo dõi:

```text
User request
    ↓
Agent execution
    ↓
Tool calls
    ↓
LLM calls
    ↓
Final output
```

Có thể dùng Langfuse.

### Metrics

- latency
- token usage
- tool errors
- agent errors
- retry count
- final budget accuracy
- itinerary validation failures

---

# Phase 23 — Evaluation

Không chỉ test code, cần test chất lượng agent.

## Functional tests

```text
Input
  ↓
Expected structured output
```

## Itinerary tests

Kiểm tra:

```text
No impossible schedule
No negative cost
No duplicate activities
No invalid coordinates
Budget respected
Opening hours respected
```

## Agent evaluation

Ví dụ:

```text
Destination relevance
Activity relevance
Budget accuracy
Route feasibility
Preference matching
```

---

# Phase 24 — Production Architecture

Final architecture:

```text
                         ┌───────────────┐
                         │     User      │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │   LangGraph   │
                         │ Orchestrator  │
                         └───────┬───────┘
                                 │
             ┌───────────────────┼──────────────────┐
             │                   │                  │
             ▼                   ▼                  ▼
        Local Agents        A2A Agents         CrewAI Team
             │                   │                  │
             └───────────────────┼──────────────────┘
                                 │
                                 ▼
                           MCP Servers
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
   Places API                 OSRM                  Weather API
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                            TripState
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
            Excel              Map                JSON
```

---

# 25. MCP Servers

Recommended capability-based design:

```text
mcp/
├── places_server.py
├── routing_server.py
├── weather_server.py
├── shopping_server.py
└── memory_server.py
```

## places-mcp

Tools:

```text
search_places
get_place_details
search_restaurants
```

## routing-mcp

Tools:

```text
calculate_route
calculate_distance_matrix
```

## weather-mcp

Tools:

```text
get_weather
get_forecast
```

## shopping-mcp

Tools:

```text
search_souvenirs
find_shopping_area
get_product_info
```

## memory-mcp

Tools:

```text
memory_get
memory_set
```

---

# 26. Folder Structure

```text
automated-travel-planner/
│
├── src/
│   ├── agents/
│   │   ├── requirements_agent.py
│   │   ├── destination_agent.py
│   │   ├── activity_agent.py
│   │   ├── transport_agent.py
│   │   ├── accommodation_agent.py
│   │   ├── budget_agent.py
│   │   ├── shopping_agent.py
│   │   └── reviewer_agent.py
│   │
│   ├── graph/
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── routing.py
│   │   └── workflow.py
│   │
│   ├── models/
│   │   ├── trip.py
│   │   ├── place.py
│   │   ├── activity.py
│   │   ├── transportation.py
│   │   ├── accommodation.py
│   │   ├── route.py
│   │   ├── souvenir.py
│   │   └── budget.py
│   │
│   ├── mcp/
│   │   ├── places_server.py
│   │   ├── routing_server.py
│   │   ├── weather_server.py
│   │   ├── shopping_server.py
│   │   └── memory_server.py
│   │
│   ├── a2a/
│   │   ├── hotel_agent.py
│   │   ├── transport_agent.py
│   │   └── client.py
│   │
│   ├── crew/
│   │   └── destination_research.py
│   │
│   ├── persistence/
│   │   └── checkpoint.py
│   │
│   ├── export/
│   │   ├── excel.py
│   │   ├── map.py
│   │   └── json.py
│   │
│   └── observability/
│       └── langfuse.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evaluation/
│
├── data/
│   └── checkpoints.db
│
├── output/
│   ├── itinerary.xlsx
│   ├── map.html
│   ├── routes.geojson
│   └── trip.json
│
├── .env
├── pyproject.toml
└── README.md
```

---

# 27. Development Order

Không nên xây toàn bộ multi-agent ngay từ đầu.

Thứ tự đề xuất:

```text
01. Project setup
       ↓
02. Pydantic models
       ↓
03. TripRequirements
       ↓
04. Basic LangGraph
       ↓
05. Destination Agent
       ↓
06. Activity Agent
       ↓
07. MCP Places
       ↓
08. OSRM Routing
       ↓
09. Route Optimization
       ↓
10. Transportation Agent
       ↓
11. Accommodation Agent
       ↓
12. Budget Agent
       ↓
13. Shopping Agent
       ↓
14. Reviewer
       ↓
15. Re-planning loop
       ↓
16. Human-in-the-loop
       ↓
17. Excel exporter
       ↓
18. Map exporter
       ↓
19. JSON exporter
       ↓
20. Memory
       ↓
21. Checkpoint
       ↓
22. A2A
       ↓
23. CrewAI
       ↓
24. Observability
       ↓
25. Evaluation
```

---

# 28. Milestone Strategy

## Milestone 1 — Single Agent

Input:

```text
I want a 5-day trip to Japan.
```

Output:

```text
TripRequirements
```

---

## Milestone 2 — Basic Multi-Agent

```text
Requirements
     ↓
Destination
     ↓
Activities
```

Output:

```text
Candidate itinerary
```

---

## Milestone 3 — Real Data

```text
Agents
  ↓
MCP
  ↓
Real places
  ↓
OSRM
  ↓
Real routes
```

---

## Milestone 4 — Full Planner

Có:

```text
Destination
Activity
Transportation
Accommodation
Budget
Shopping
Reviewer
```

---

## Milestone 5 — Export

Output:

```text
itinerary.xlsx
map.html
trip.json
```

---

## Milestone 6 — Advanced Agent Architecture

Thêm:

```text
Memory
Checkpoint
Human-in-the-loop
A2A
CrewAI
Observability
Evaluation
```

---

# 29. Definition of Done

Project được xem là hoàn thành MVP khi:

- [x] User nhập natural language request.
- [x] System tạo `TripRequirements`.
- [x] LangGraph điều phối nhiều agent.
- [x] Places được lấy từ tool/API.
- [x] Coordinates không do LLM tự bịa.
- [ ] Route được tính bằng OSRM.
- [ ] Itinerary có thời gian và địa điểm.
- [ ] Budget được tính bằng code.
- [ ] Shopping/Souvenir được tích hợp.
- [ ] Reviewer phát hiện lỗi.
- [ ] Có re-planning loop.
- [ ] Có human approval.
- [ ] Export được Excel.
- [ ] Export được interactive map.
- [ ] Export được JSON.

Advanced version:

- [ ] MCP servers
- [ ] Memory
- [ ] Checkpoint
- [ ] A2A
- [ ] CrewAI
- [ ] Observability
- [ ] Evaluation

---

# 30. Quy tắc quan trọng khi implement

## Rule 1

Không xây agent trước khi có schema.

## Rule 2

Không để LLM làm việc mà code có thể làm deterministic.

Ví dụ:

```text
❌ LLM tính tổng tiền
❌ LLM tính khoảng cách
❌ LLM tự tính thời gian di chuyển
❌ LLM tự sinh latitude/longitude
```

Thay bằng:

```text
✅ Python tính tổng tiền
✅ OSRM tính route
✅ OSRM tính duration
✅ Places API trả coordinates
```

## Rule 3

Không thêm A2A/CrewAI quá sớm.

Hãy làm local LangGraph version chạy ổn trước.

## Rule 4

Mỗi phase phải có test.

## Rule 5

Mỗi agent phải có input/output schema rõ ràng.

## Rule 6

TripState là nguồn dữ liệu duy nhất.

## Rule 7

Exporter không được tự quyết định itinerary.

Exporter chỉ render dữ liệu từ `TripState`.

---

# 31. Final Mental Model

Hãy nhớ 4 lớp:

```text
                 ┌─────────────────────┐
                 │      LangGraph      │
                 │   Orchestration     │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │       Agents        │
                 │  Reasoning / Plan   │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │    MCP / A2A        │
                 │ Tools / Agent APIs   │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │     TripState       │
                 │ Single Source Truth │
                 └──────────┬──────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
          Excel            Map            JSON
```

### Ý nghĩa

**LangGraph**

> Ai chạy trước, ai chạy sau, khi nào loop, khi nào dừng?

**Agent**

> AI cần suy luận / quyết định điều gì?

**MCP**

> Agent cần sử dụng tool/data nào?

**A2A**

> Agent này cần giao tiếp với agent khác như thế nào?

**CrewAI**

> Một nhóm agent phối hợp để giải quyết một subtask như thế nào?

**TripState**

> Toàn bộ hệ thống đang biết gì và kế hoạch hiện tại là gì?

**Exporter**

> Biến kế hoạch đã hoàn thành thành output cho user.

---

# 32. Bước tiếp theo

Không code tất cả cùng lúc.

Bắt đầu từ:

```text
Phase 0
  ↓
Phase 1
  ↓
Phase 2
```

Tức là:

1. Setup project.
2. Thiết kế Pydantic models.
3. Tạo `TripRequirements`.
4. Viết agent đầu tiên.
5. Sau đó mới đưa vào LangGraph.

Khi mỗi phase hoàn thành, đánh dấu checkbox trong file này và chuyển sang phase tiếp theo.
