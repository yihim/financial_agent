import streamlit as st
import requests
from typing import List, Union
from dataclasses import dataclass, asdict
import json
import logging
import sys
import uuid

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Configure the page with a clean, minimalist theme
st.set_page_config(
    page_title="Finance Assistant",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for minimalist styling
st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
        max-width: 800px;
        margin: 0 auto;
    }
    h1 {
        font-size: 2.2rem;
        font-weight: 600;
        margin-bottom: 2rem;
        color: #3B82F6;
    }
    .stButton button {
        background-color: #3B82F6;
        color: white;
        border-radius: 4px;
        padding: 0.5rem 1.5rem;
        border: none;
        box-shadow: none;
    }
    .stButton button:hover {
        background-color: #2563EB;
    }
    .success-box {
        background-color: rgba(16, 185, 129, 0.15);
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #10B981;
        margin-bottom: 1.5rem;
    }
    .stTextInput, .stNumberInput {
        margin-bottom: 1rem;
    }
    .chat-container {
        margin-top: 1.5rem;
    }
    .step-header {
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 1rem;
        color: #60A5FA;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# API endpoints
# docker
VALIDATION_API = "http://db:8070/api/validify/client-bank-account"
GET_CLIENT_SINGLE_BANK_ACCOUNT_API = (
    "http://db:8070/api/client/{client_id}/bank-account"
)
CHAT_API = "http://agents:8080/api/chat"


# Define message classes
@dataclass
class BaseMessage:
    content: str
    additional_kwargs: dict = None

    def __post_init__(self):
        if self.additional_kwargs is None:
            self.additional_kwargs = {}


@dataclass
class HumanMessage(BaseMessage):
    type: str = "human"


@dataclass
class AIMessage(BaseMessage):
    type: str = "ai"


# Function to encode messages
def encode_messages(messages: List[Union[HumanMessage, AIMessage]]) -> str:
    serializable = [asdict(msg) for msg in messages]
    return json.dumps(serializable)


# Initialize session state
if "validated" not in st.session_state:
    st.session_state.validated = False
if "client_id" not in st.session_state:
    st.session_state.client_id = ""
if "bank_id" not in st.session_state:
    st.session_state.bank_id = ""
if "account_id" not in st.session_state:
    st.session_state.account_id = ""
if "step" not in st.session_state:
    st.session_state.step = "client_input"
if "error" not in st.session_state:
    st.session_state.error = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# Define functions
def validate_client_id(client_id: int):
    try:
        response = requests.post(VALIDATION_API, json={"client_id": client_id})
        data = response.json()
        if data["status"] == "success":
            response = requests.get(
                GET_CLIENT_SINGLE_BANK_ACCOUNT_API.format(client_id=client_id)
            )
            data = response.json()
            if data["status"] == "success":
                st.session_state.validated = True
                st.session_state.bank_id = data["bank_id"]
                st.session_state.account_id = data["account_id"]
                st.session_state.step = "chat"
            else:
                st.session_state.step = "bank_account_input"
            st.rerun()
        else:
            st.session_state.error = (
                f"Validation failed: {data.get('message', 'Unknown error')}"
            )
    except Exception as e:
        st.session_state.error = f"Error during validation: {e}"


def validate_full_details(client_id: int, bank_id: int, account_id: int):
    try:
        response = requests.post(
            VALIDATION_API,
            json={"client_id": client_id, "bank_id": bank_id, "account_id": account_id},
        )
        data = response.json()
        if data["status"] == "success":
            st.session_state.validated = True
            st.session_state.step = "chat"
            st.rerun()
        else:
            st.session_state.error = (
                f"Validation failed: {data.get('message', 'Unknown error')}"
            )
    except Exception as e:
        st.session_state.error = f"Error during validation: {e}"


def stream_chat_response(
    user_input: str, thread_id: str, client_id: int, bank_id: int, account_id: int
):
    try:
        # Add user message to chat history
        st.session_state.chat_history.append(HumanMessage(content=user_input))

        # Prepare payload with client context
        payload = {
            "query": user_input,
            "chat_history": encode_messages(st.session_state.chat_history),
            "client_id": client_id,
            "bank_id": bank_id,
            "account_id": account_id,
            "thread_id": thread_id,
        }

        logger.info(payload)

        # Make a streaming request
        with requests.post(
            CHAT_API,
            json=payload,
            stream=True,
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status_code == 200:
                response_parts = []

                # Process the streaming response in chunks
                for chunk in response.iter_content(
                    chunk_size=None, decode_unicode=True
                ):
                    if chunk:
                        response_parts.append(chunk)
                        # Yield the accumulated response for display
                        yield "".join(response_parts)

                # Add AI response to chat history
                final_response = "".join(response_parts)
                st.session_state.chat_history.append(AIMessage(content=final_response))
                return final_response
            else:
                error_message = f"Error: {response.status_code}"
                yield error_message
                st.session_state.chat_history.append(AIMessage(content=error_message))
                return error_message
    except Exception as e:
        error_message = f"Sorry, an unexpected error occurred: {e}"
        yield error_message
        st.session_state.chat_history.append(AIMessage(content=error_message))
        return error_message


# UI Flow with minimal, clean design
st.title("Finance Assistant")

# Progress indicator
if st.session_state.step == "client_input":
    progress = 1
elif st.session_state.step == "bank_account_input":
    progress = 2
else:
    progress = 3

if st.session_state.step != "chat":
    st.progress(progress / 3)

# Step 1: Client ID Input
if st.session_state.step == "client_input":
    st.markdown(
        '<p class="step-header">Step 1: Account Verification</p>',
        unsafe_allow_html=True,
    )

    with st.container():
        client_id = st.number_input(
            "Enter your Client ID", min_value=1, step=1, key="client_id_input"
        )
        continue_btn = st.button("Continue", use_container_width=True)

        if continue_btn:
            st.session_state.client_id = client_id
            with st.spinner("Verifying..."):
                validate_client_id(client_id)

# Step 2: Bank ID and Account ID Input
elif st.session_state.step == "bank_account_input":
    st.markdown(
        '<p class="step-header">Step 2: Additional Information</p>',
        unsafe_allow_html=True,
    )

    st.info("Please provide your banking details")

    # Display the client ID (read-only)
    st.text_input("Client ID", value=str(st.session_state.client_id), disabled=True)

    # Bank and account inputs
    col1, col2 = st.columns(2)
    with col1:
        bank_id = st.number_input("Bank ID", min_value=1, step=1)
    with col2:
        account_id = st.number_input("Account ID", min_value=1, step=1)

    continue_btn = st.button("Continue", use_container_width=True)
    if continue_btn:
        with st.spinner("Verifying details..."):
            st.session_state.bank_id = bank_id
            st.session_state.account_id = account_id
            validate_full_details(st.session_state.client_id, bank_id, account_id)

# Step 3: Chat Interface
elif st.session_state.step == "chat":
    # Display account info in a subtle way
    client_info = f"Client ID: {st.session_state.client_id} • Bank ID: {st.session_state.bank_id} • Account ID: {st.session_state.account_id}"
    st.markdown(
        f"<div style='color: #6B7280; font-size: 0.8rem; margin-bottom: 1rem;'>{client_info}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='success-box'>✓ Account verified successfully</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.thread_id:
        st.session_state.thread_id = uuid.uuid4().hex[:8]

    # Display chat history with clean styling
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(
            message["role"], avatar="👤" if message["role"] == "user" else "💼"
        ):
            st.write(message["content"])
    st.markdown("</div>", unsafe_allow_html=True)

    # Add initial welcome message if chat is empty
    if not st.session_state.messages:
        welcome_msg = "How can I help you with your finances today?"
        with st.chat_message("assistant", avatar="💼"):
            st.write(welcome_msg)
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        # Also add to dataclass-based chat history
        st.session_state.chat_history.append(AIMessage(content=welcome_msg))

    # Chat input
    user_input = st.chat_input("Ask about your finances...")
    if user_input:
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.write(user_input)

        # Add user message to messages history (for display)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Create a placeholder for the assistant's response
        with st.chat_message("assistant", avatar="💼"):
            message_placeholder = st.empty()
            full_response = ""

            # Stream the response
            for response_chunk in stream_chat_response(
                user_input=user_input,
                thread_id=st.session_state.thread_id,
                client_id=st.session_state.client_id,
                bank_id=st.session_state.bank_id,
                account_id=st.session_state.account_id,
            ):
                message_placeholder.write(response_chunk)
                full_response = response_chunk

            # Add the assistant's response to display history
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

# Show error if any, with minimal styling
if st.session_state.error:
    st.error(st.session_state.error)
    st.session_state.error = ""
