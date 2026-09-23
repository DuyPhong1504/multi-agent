from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st
from langchain_core.messages import HumanMessage


# Allow this file to be launched directly with `streamlit run`.
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))

from agent.requirement import requirement_node


st.set_page_config(page_title="Trip Requirement Agent", page_icon="✈️")

st.title("Trip Requirement Agent")
st.caption("Nhập yêu cầu chuyến đi để kiểm tra output JSON của requirement agent.")

with st.sidebar:
	st.header("LLM settings")
	api_key = st.text_input(
		"API key",
		value=os.getenv("REQUIREMENT_API_KEY", ""),
		type="password",
		help="Key chỉ được dùng trong lần chạy hiện tại và không được lưu vào source.",
	)
	model = st.text_input(
		"Model",
		value=os.getenv("REQUIREMENT_MODEL", "gpt-5.4"),
	)
	base_url = st.text_input(
		"Base URL",
		value=os.getenv("REQUIREMENT_BASE_URL", "https://api.xah.io/v1"),
	)

default_request = (
	"Tôi muốn đi Tokyo 5 ngày vào tháng 11, 2 người, ngân sách 1000 USD. "
	"Chúng tôi thích ẩm thực Nhật, đền chùa và mua sắm; không thích nightlife."
)
user_input = st.text_area(
	"Yêu cầu chuyến đi",
	value=default_request,
	height=140,
)

if st.button("Extract requirements", type="primary", use_container_width=True):
	if not api_key:
		st.error("Bạn cần nhập API key trong sidebar hoặc đặt REQUIREMENT_API_KEY trong file .env.")
	elif not user_input.strip():
		st.warning("Hãy nhập yêu cầu chuyến đi.")
	else:
		os.environ["REQUIREMENT_API_KEY"] = api_key
		os.environ["REQUIREMENT_MODEL"] = model
		os.environ["REQUIREMENT_BASE_URL"] = base_url

		with st.spinner("Đang gọi requirement agent..."):
			result = requirement_node(
				{"messages": [HumanMessage(content=user_input.strip())]}
			)

		if result.get("error"):
			st.error(result["error"])
		else:
			requirements = result["requirements"]
			st.success("Đã trích xuất requirements thành công.")
			st.subheader("TripRequirements")
			st.json(requirements.to_dict())
			st.download_button(
				"Download JSON",
				data=json.dumps(requirements.to_dict(), ensure_ascii=False, indent=2),
				file_name="trip_requirements.json",
				mime="application/json",
			)
