import openai
import re
import streamlit as st
from prompt import get_system_prompt
# from snowflake.snowpark import Session

st.title("☃️ Frosty")

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Print system prompt - create expandable container
with st.expander("System Prompt:", expanded=True):
    #retrieves content of the first message in the st.session_state.messages which contains the system prompt
    st.write(st.session_state.messages[0]["content"])

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# display the existing chat messages
for message in st.session_state.messages:
    #if message is from system, skips the current iteration of the loop, system messages are not displayed
    if message["role"] == "system":
        
        continue
    #set role for subsequent text or data display within UI
    with st.chat_message(message["role"]):
        #displays content of message
        st.write(message["content"])
        #if results are found in message, display a DataFrame/render structured data in tabular format within Streamlit
        if "results" in message:
            st.dataframe(message["results"])

#If last message is not from assistant, generate a new response
#instead of displaying entire response, use OpenAI stream to signify
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = ""
        # Create an empty Streamlit container for displaying the response
        resp_container = st.empty()
        #Iterate through response chunks from model in streaming mode
        for delta in openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True,
        ):
            #Append each response chunk
            response += delta.choices[0].delta.get("content", "")
            #Display the cumulative response in resp_container using markdown formatting
            resp_container.markdown(response)

        #Create message dictionary for assistant's response
        message = {"role": "assistant", "content": response}
        # Extract the sql code using regex and execute if available
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        if sql_match:
            # Extract the SQL query from the matched pattern
            sql = sql_match.group(1)
            #establish connection to snowflake DB
            conn = st.experimental_connection("snowpark")
            #send query to snowflake store results in message dictionary
            message["results"] = conn.query(sql)
            #display query results in Streamlit DataFrame

            st.dataframe(message["results"])
            
        #Append assistant message including sql results to session's message history
        st.session_state.messages.append(message)
