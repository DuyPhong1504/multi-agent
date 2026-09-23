from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st
from langchain_core.messages import HumanMessage


SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph.workflow import run_requirements


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Convert Pydantic models and LangChain messages for Streamlit output."""
    return json.loads(
        json.dumps(
            state,
            default=lambda value: (
                value.model_dump()
                if hasattr(value, "model_dump")
                else str(value)
            ),
        )
    )


def _split_values(value: str) -> list[str]:
    """Convert a comma-separated field into clean string values."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_structured_request(
    destination: str,
    start_date: date | None,
    end_date: date | None,
    duration_days: int,
    travelers: int,
    budget: float | None,
    currency: str,
    interests: str,
    food_preferences: str,
    transport_preference: str,
    accommodation_preference: str,
    avoid: str,
    must_visit: str,
    shopping_preferences: str,
) -> str:
    """Build a stable, explicit prompt from the structured form values."""
    request = {
        "destination": destination.strip() or None,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "duration_days": duration_days,
        "travelers": travelers,
        "budget": budget,
        "currency": currency,
        "interests": _split_values(interests),
        "food_preferences": _split_values(food_preferences),
        "transport_preference": transport_preference.strip() or None,
        "accommodation_preference": accommodation_preference.strip() or None,
        "avoid": _split_values(avoid),
        "must_visit": _split_values(must_visit),
        "shopping_preferences": _split_values(shopping_preferences),
    }
    return (
        "Tôi muốn lập kế hoạch chuyến đi với các thông tin đã được chuẩn hóa sau.\n"
        "Hãy sử dụng đúng các giá trị này, không tự bịa thêm thông tin còn thiếu.\n"
        f"{json.dumps(request, ensure_ascii=False, indent=2)}"
    )


st.set_page_config(
    page_title="Travel Planner Workflow",
    page_icon="✈️",
    layout="wide",
)

st.title("Travel Planner Workflow")
st.caption("Chạy workflow LangGraph và hiển thị kết quả từ các node.")

with st.sidebar:
    st.header("LLM settings")
    api_key = st.text_input(
        "API key",
        value=os.getenv("REQUIREMENT_API_KEY", ""),
        type="password",
    )
    model = st.text_input(
        "Model",
        value=os.getenv("REQUIREMENT_MODEL", "gpt-5.4"),
    )
    base_url = st.text_input(
        "Base URL",
        value=os.getenv("REQUIREMENT_BASE_URL", "https://api.xah.io/v1"),
    )

st.subheader("Thông tin chuyến đi")
has_dates = st.checkbox("Đã xác định ngày đi và ngày về")
budget_enabled = st.checkbox("Có ngân sách dự kiến")

with st.form("trip_requirements"):
    destination = st.text_input(
        "Điểm đến *",
        placeholder="Ví dụ: Tokyo, Nhật Bản",
    )

    date_columns = st.columns(2)
    with date_columns[0]:
        start_date = st.date_input(
            "Ngày đi",
            value=date.today(),
            disabled=not has_dates,
        )
    with date_columns[1]:
        end_date = st.date_input(
            "Ngày về",
            value=date.today(),
            disabled=not has_dates,
        )

    trip_columns = st.columns(2)
    with trip_columns[0]:
        duration_days = st.number_input(
            "Số ngày (0 nếu chưa biết)", min_value=0, value=0, step=1
        )
    with trip_columns[1]:
        travelers = st.number_input("Số người", min_value=1, value=1, step=1)

    st.subheader("Ngân sách và sở thích")
    budget_columns = st.columns(2)
    with budget_columns[0]:
        budget = st.number_input(
            "Ngân sách",
            min_value=0.0,
            value=0.0,
            step=100.0,
            disabled=not budget_enabled,
        )
    with budget_columns[1]:
        currency = st.selectbox("Đơn vị tiền tệ", ["USD", "VND", "JPY", "EUR"])

    interests = st.text_input(
        "Sở thích",
        placeholder="Ví dụ: văn hóa, thiên nhiên, mua sắm",
    )
    food_preferences = st.text_input(
        "Ẩm thực mong muốn",
        placeholder="Ví dụ: sushi, món chay, street food",
    )
    must_visit = st.text_input(
        "Địa điểm bắt buộc muốn ghé",
        placeholder="Ví dụ: Tokyo Skytree, Shibuya",
    )
    shopping_preferences = st.text_input(
        "Nhu cầu mua sắm",
        placeholder="Ví dụ: đồ điện tử, quà lưu niệm",
    )

    preference_columns = st.columns(2)
    with preference_columns[0]:
        transport_preference = st.text_input(
            "Phương tiện ưu tiên",
            placeholder="Ví dụ: tàu điện, đi bộ",
        )
    with preference_columns[1]:
        accommodation_preference = st.text_input(
            "Nơi ở mong muốn",
            placeholder="Ví dụ: khách sạn gần trung tâm",
        )
    avoid = st.text_input(
        "Điều cần tránh",
        placeholder="Ví dụ: nơi quá đông, món cay",
    )

    submitted = st.form_submit_button("Run workflow", type="primary", width="stretch")

if submitted:
    if not api_key:
        st.error("Vui lòng nhập API key hoặc đặt REQUIREMENT_API_KEY trong file .env.")
    elif not destination.strip():
        st.warning("Vui lòng nhập điểm đến.")
    elif has_dates and end_date < start_date:
        st.warning("Ngày về phải bằng hoặc sau ngày đi.")
    else:
        os.environ["REQUIREMENT_API_KEY"] = api_key
        os.environ["REQUIREMENT_MODEL"] = model
        os.environ["REQUIREMENT_BASE_URL"] = base_url

        structured_request = _build_structured_request(
            destination=destination,
            start_date=start_date if has_dates else None,
            end_date=end_date if has_dates else None,
            duration_days=int(duration_days),
            travelers=int(travelers),
            budget=float(budget) if budget_enabled else None,
            currency=currency,
            interests=interests,
            food_preferences=food_preferences,
            transport_preference=transport_preference,
            accommodation_preference=accommodation_preference,
            avoid=avoid,
            must_visit=must_visit,
            shopping_preferences=shopping_preferences,
        )

        with st.spinner("Đang chạy workflow..."):
            result = run_requirements(
                [HumanMessage(content=structured_request)]
            )

        if result.get("error"):
            st.error(result["error"])
        else:
            st.success("Workflow hoàn tất.")

            requirements = result.get("requirements")
            if requirements is not None:
                st.subheader("Requirements")
                requirements_data = (
                    requirements.to_dict()
                    if hasattr(requirements, "to_dict")
                    else requirements
                )
                st.json(requirements_data)

            activities = result.get("activities") or []
            if activities:
                st.subheader(f"Activities ({len(activities)})")
                for activity in activities:
                    activity_data = (
                        activity.model_dump()
                        if hasattr(activity, "model_dump")
                        else activity
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"**Day {activity_data['day']} · "
                            f"{activity_data['start_time']}–{activity_data['end_time']}** — "
                            f"{activity_data['title']}"
                        )
                        if activity_data.get("description"):
                            st.caption(activity_data["description"])
                        st.caption(
                            f"Place: {activity_data['place_id']} · "
                            f"Cost: {activity_data['cost']} {activity_data['currency']}"
                        )
            elif not result.get("error"):
                st.info("Không có activity nào được đề xuất.")

            transportation = result.get("transportation") or []
            if transportation:
                st.subheader(f"Transportation ({len(transportation)})")
                for leg in transportation:
                    leg_data = (
                        leg.model_dump()
                        if hasattr(leg, "model_dump")
                        else leg
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"**{leg_data['from_place_id']} → "
                            f"{leg_data['to_place_id']}** — {leg_data['mode']}"
                        )
                        st.caption(
                            f"Departure: {leg_data.get('departure_time') or '—'} · "
                            f"Arrival: {leg_data.get('arrival_time') or '—'}"
                        )
                        st.caption(
                            f"Duration: {leg_data['duration_minutes']} min · "
                            f"Distance: {leg_data['distance_km']} km · "
                            f"Cost: {leg_data['cost']} {leg_data['currency']}"
                        )
            elif not result.get("error"):
                st.info("Không có transportation nào được đề xuất.")

            accommodations = result.get("accommodations") or []
            if accommodations:
                st.subheader(f"Accommodation ({len(accommodations)})")
                for accommodation in accommodations:
                    acc_data = (
                        accommodation.model_dump()
                        if hasattr(accommodation, "model_dump")
                        else accommodation
                    )
                    with st.container(border=True):
                        st.markdown(f"**{acc_data['name']}**")
                        if acc_data.get("address"):
                            st.caption(acc_data["address"])
                        st.caption(
                            f"Check-in: {acc_data['check_in']} · "
                            f"Check-out: {acc_data['check_out']}"
                        )
                        st.caption(
                            f"Price/night: {acc_data['price_per_night']} "
                            f"{acc_data['currency']} · "
                            f"Total: {acc_data['total_price']} {acc_data['currency']}"
                        )
                        if acc_data.get("rating") is not None:
                            st.caption(f"Rating: {acc_data['rating']}/5")
            elif not result.get("error"):
                st.info("Không có accommodation nào được đề xuất.")

            with st.expander("Workflow state"):
                st.json(_serialize_state(result))
