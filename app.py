import streamlit as st
import requests
from typing import List, Union
from dataclasses import dataclass, asdict
import json

# Configure the page
st.set_page_config(page_title="Financial Assistant", page_icon="💰", layout="centered")

# API endpoints
# local
# VALIDATION_API = "http://localhost:8070/api/validify/client-bank-account"
# GET_CLIENT_SINGLE_BANK_ACCOUNT_API = "http://localhost:8070/api/client/{client_id}/bank-account"
# CHAT_API = "http://localhost:8080/api/chat"

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


# UI Flow
st.title("💰 Financial Assistant")

# Step 1: Client ID Input
if st.session_state.step == "client_input":
    client_id = st.number_input("Enter your Client ID", min_value=1, step=1)
    if st.button("Continue"):
        st.session_state.client_id = client_id
        validate_client_id(client_id)

# Step 2: Bank ID and Account ID Input
elif st.session_state.step == "bank_account_input":
    st.info(
        "We couldn't find a default bank/account. Please provide the details below."
    )

    # 🔒 Display the client ID (read-only)
    st.text_input("Client ID", value=str(st.session_state.client_id), disabled=True)

    # Bank and account inputs
    bank_id = st.number_input("Enter your Bank ID", min_value=1, step=1)
    account_id = st.number_input("Enter your Account ID", min_value=1, step=1)

    if st.button("Continue"):
        st.session_state.bank_id = bank_id
        st.session_state.account_id = account_id
        validate_full_details(st.session_state.client_id, bank_id, account_id)

# Step 3: Chat Interface
elif st.session_state.step == "chat":
    st.success("✅ You're successfully validated! Welcome to the chat.")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Add initial welcome message if chat is empty
    if not st.session_state.messages:
        welcome_msg = "How can I help you with your finances today?"
        with st.chat_message("assistant"):
            st.write(welcome_msg)
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        # Also add to dataclass-based chat history
        st.session_state.chat_history.append(AIMessage(content=welcome_msg))

    # Chat input
    user_input = st.chat_input("Type your question...")
    if user_input:
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)

        # Add user message to messages history (for display)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Create a placeholder for the assistant's response
        with st.chat_message("assistant"):
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

# Show error if any
if st.session_state.error:
    st.error(st.session_state.error)
    st.session_state.error = ""
