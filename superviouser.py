# tools/superviouser.py
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import asyncio

load_dotenv(override=True)

@function_tool
def send_brevo_email(to_email: str, subject: str, html_content: str):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY')
    
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": "Recipient"}],
        sender={"email": os.environ.get('EMAIL_SENDER', "virender.aideveloper@gmail.com"), "name": "Virender AI Developer"},
        subject=subject,
        html_content=html_content
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        return {"status": "success", "response": api_response}
    except ApiException as e:
        return {"status": "error", "error": str(e)}
    
def create_agent(name, instructions, tools=None, handoff_description="", handoff_tools=None):
    # avoid mutable default arguments
    if tools is None:
        tools = []
    if handoff_tools is None:
        handoff_tools = []

    base_kwargs = {
        "name": name,
        "instructions": instructions,
        "model": os.environ.get('OPENAI_SUPERVISED_AGENT_MODEL', 'gpt-4o-mini'),
    }

    if not tools:
        return Agent(**base_kwargs)
    elif handoff_tools and handoff_tools != []:
        return Agent(
            **base_kwargs,
            tools=tools,
            handoffs=handoff_tools
        )
    else:
        return Agent(
            **base_kwargs,
            tools=tools,
            handoff_description=handoff_description
        )

def convert_agent_to_tool(agent, tool_name, tool_description):
    return agent.as_tool(
      tool_name=tool_name,
      tool_description=tool_description
    )
    

async def superviouser_agentic_handoff(to_email, instructions1, instructions2, instructions3, manager_instructions):
    if os.environ.get('OPENAI_API_KEY') is None:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    if os.environ.get('BREVO_API_KEY') is None:
        raise ValueError("BREVO_API_KEY environment variable is not set.")
    if not all([to_email, instructions1, instructions2, instructions3, manager_instructions]) or any(field.strip() == "" for field in [to_email, instructions1, instructions2, instructions3, manager_instructions]):
        raise ValueError("All fields must be filled.")
    
    subject_instructions = "You can write a subject for a cold sales email. \
    You are given a message and you need to write a subject for an email that is likely to get a response."
    html_instructions = "You can convert a text email body to an HTML email body. \
    You are given a text email body which might have some markdown \
    and you need to convert it to an HTML email body with simple, clear, compelling layout and design."
    instructions ="You are an email formatter and sender. You receive the body of an email to be sent. \
    You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
    Finally, you use the send_brevo_email tool to send the email with the subject and HTML body."
    sales_agent1 = create_agent("Professional Sales Agent", instructions1)
    sales_agent2 = create_agent("Engaging Sales Agent", instructions2)
    sales_agent3 = create_agent("Busy Sales Agent", instructions3)
    subject_writer_agent = create_agent("Email subject writer", subject_instructions)
    html_converter_agent = create_agent("HTML email body converter", html_instructions)

    tool1 = convert_agent_to_tool(sales_agent1, "professional_sales_agent", "Write a cold sales email.")
    tool2 = convert_agent_to_tool(sales_agent2, "engaging_sales_agent", "Write a cold sales email.")
    tool3 = convert_agent_to_tool(sales_agent3, "busy_sales_agent", "Write a cold sales email.")
    subject_writer = convert_agent_to_tool(subject_writer_agent, "subject_writer", "Write a subject for a cold sales email.")
    html_converter = convert_agent_to_tool(html_converter_agent, "html_converter", "Convert a text email body to an HTML email body.")

    tools = [subject_writer, html_converter, send_brevo_email]
    
    emailer_agent = create_agent("Email Manager", instructions, tools, "Convert an email to HTML and send it")
    
    sales_tools = [tool1, tool2, tool3]
    handoff_tools = [emailer_agent]

    sales_manager = create_agent("Sales Manager", manager_instructions, sales_tools, "", handoff_tools)
    message = f"""Send out a cold sales email addressed to Dear CEO from Virender.
                The recipient email is: {to_email}.
                After generating and formatting the best email, call the send_brevo_email tool with these parameters:
                - to_email: {to_email}
                - subject: the generated subject line
                - html_content: the HTML version of the selected best email
                """

    with trace("Superviouser Agentic Handoff"):
        result = await Runner.run(sales_manager, message)
    return {"status": "success", "result": result}