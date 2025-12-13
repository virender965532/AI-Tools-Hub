import asyncio
import os
import webbrowser
from dotenv import load_dotenv
from pypdf import PdfReader
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from agents import Agent, Runner, trace, function_tool
import urllib
import win32com.client as win32
import json

load_dotenv(override=True)
OPENAI_AGENT_MODEL = os.environ.get('OPENAI_AGENT_MODEL', 'gpt-4o-mini')

def open_email_default(to_email: str, subject: str, html_content: str):
    try:
        subject_encoded = urllib.parse.quote(subject)
        body_encoded = urllib.parse.quote(html_content)

        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&tf=1&to={to_email}&su={subject_encoded}&body={body_encoded}"

        webbrowser.open(gmail_url)
        return {"status": "success", "message": "Email client opened successfully."}
    except Exception as e:
        print("Error:", e)
        return {"status": "failure", "error": str(e)}


def create_agent(name, instructions, tools=None, handoff_description="", handoff_tools=None):
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


PROMPTS = {
    "JobRequirementAnalyzer": (
        "Understand the job requirement provided in the input text.\n"
        "Return a detailed breakdown of: key responsibilities, required skills (hard and soft),"
        " seniority level, mandatory vs nice-to-have qualifications, and suggested interview topics."
    ),

    "CandidateProfileAnalyzer": (
        "Given access to candidate files (Profile.pdf, Summary.txt, VirenderFullstackResume.pdf) located in a provided folder path,"
        " analyze and summarize the candidate's skills, experience, achievements, and gaps. Output a structured profile with skill tags, years of experience per area, notable projects, and suggested strengths to highlight."
    ),

    "HiringManagerEmailDraftsman": (
        "Using the finalized job description, and extracted resume profile, draft a highly professional, concise, and persuasive email to the hiring manager expressing interest in the role. The email must open courteously, highlight the strongest skills, achievements, and experience that directly match the job description, and clearly show why the candidate is an excellent fit for the position. Incorporate important keywords from both the resume profile and job description to improve relevance and impact. Ensure the tone is polite, confident, and value-driven. Close with a polite call to action, include contact details, and mention attached documents such as the resume and fitment report. Output only the email body."
    ),

    "EmailSubjectLineCreator": (
        "Generate a professional, concise, and attention-grabbing subject line for a job application email, using the candidate’s top strengths and the job title as context. The subject line should be clear, specific, and appealing to a hiring manager, reflecting the role, years of experience if applicable, and top relevant skills or technologies extracted from the resume profile and job description. Format it in a clean, industry-standard way similar to: “Experienced Frontend Engineer — 6 yrs, React & TypeScript”."
    ),

    "EmailReviewerEvaluator": (
        """Review the one generated subject line and the two generated email bodies together for quality, clarity, professionalism, tone, grammar, persuasiveness, and alignment with both the job description and the candidate profile. First, select the best email body from the two drafts based on clarity, structure, personalization, alignment with job requirements, keyword usage, achievements, tone, conciseness, and persuasive impact. Then evaluate this chosen email together with the subject line to ensure the subject is sharp, role-specific, and attention-grabbing, and the email body is well-structured, personalized, keyword-rich, achievement-focused, and clearly demonstrates the candidate’s fit. If any issue is found—such as weak phrasing, missing keywords, poor tone, insufficient personalization, or unclear messaging—you must request a regeneration. Only one regeneration cycle is allowed. If regeneration is required, you must call EmailSubjectLineCreator once and HiringManagerEmailDraftsman twice simultaneously, then select the best regenerated email body and evaluate it again with the regenerated subject line. If the regenerated versions still fall short, return the best possible result and explain its limitations. Your final output must be exactly one JSON object, using the following structure when fully satisfied: { "is_satisfied": true, "reason": "<explanation>", "final_subject": "<best subject line>", "final_email_body": "<best email body>" }. Do not include any text outside the JSON, and do not use Markdown."""
    ),
}

managerInstructionsPrompt = """
You are the Job Apply Pro Pipeline Manager.
You will receive ONE input object containing exactly these four fields:
1. job_requirement_text  
2. hiring_manager_email  
3. candidate_profile_data (LinkedIn profile data, summary text data, resume data)

You MUST NOT proceed unless all fields are present and non-empty.

============================================================
PHASE-BASED WORKFLOW (MANDATORY, NO REORDERING)
============================================================

PHASE 1 — RUN IN PARALLEL (no dependence order)
You must call the following three tools in parallel and capture their outputs:

1) job_requirement_analyzer  
2) candidate_profile_analyzer  
3) subject_creator

Rules:
• Each of these tools may be retried up to 3 times if output is incomplete.  
• If any still fail after 3 retries, STOP the full pipeline.  

After all three are complete, merge results into a structured internal report for later stages.
DO NOT write emails in this phase.

============================================================

PHASE 2 — RUN SEQUENTIALLY (strict order)
Step A — email_draftsman  
Use all insights from Phase 1 to draft a highly personalized job application email.  
REQUIRED CONSTRAINTS:  
• The email body must be written in plain English only — NO HTML and NO HTML tags (no <p>, <br>, <strong>, etc.)  
• It must clearly highlight the candidate’s matching skills and achievements, without fabricating information.

Step B — email_reviewer  
Review and refine the email created in Step A.  
Improve clarity, correctness, tone, grammar, and professionalism only.  
The reviewer MUST NOT add new fitment content — only polish language and flow.

Retry rule:  
• email_reviewer may be called up to 3 times.  
• Select the best refined version.

============================================================

PHASE 3 — EMAIL DELIVERY
Finally, call open_email_default using:
• hiring_manager_email  
• the subject created in Phase 1  
• the final reviewed email content produced in Phase 2 (still plain English)

============================================================
FINAL OUTPUT FORMAT
============================================================
You must return a structured JSON object containing:
{
  "tool_call_logs": [ordered log of each tool call, inputs, and outputs],
  "final_subject": "<generated subject>",
  "final_email": "<reviewed plain-text email body>",
  "status": "<result of open_email_default>"
}

NO commentary outside the JSON.
Do NOT wrap the email body in HTML or Markdown.
Do NOT add suggestions or notes outside JSON.
"""



def build_recruitment_agents():
    # Create core agents
    job_req_agent = create_agent("Job Requirement Analyzer", PROMPTS["JobRequirementAnalyzer"])
    candidate_agent = create_agent("Candidate Profile Analyzer", PROMPTS["CandidateProfileAnalyzer"])
    draftsman_agent = create_agent("Hiring Manager Email Draftsman", PROMPTS["HiringManagerEmailDraftsman"])
    subject_agent = create_agent("Email Subject Line Creator", PROMPTS["EmailSubjectLineCreator"])
    reviewer_agent = create_agent("Email Reviewer Evaluator", PROMPTS["EmailReviewerEvaluator"])

    # Convert to tools
    tools = {
        "job_requirement_analyzer": convert_agent_to_tool(job_req_agent, "job_requirement_analyzer", "Analyze job requirement text"),
        "candidate_profile_analyzer": convert_agent_to_tool(candidate_agent, "candidate_profile_analyzer", "Analyze candidate files in folder"),
        "email_draftsman": convert_agent_to_tool(draftsman_agent, "email_draftsman", "Draft an email to the hiring manager"),
        "subject_creator": convert_agent_to_tool(subject_agent, "subject_creator", "Create an email subject line"),
        "email_reviewer": convert_agent_to_tool(reviewer_agent, "email_reviewer", "Review and improve an email"),
        "open_email_default": open_email_default,
    }

    return tools


def create_recruitment_pipeline():
    tools = build_recruitment_agents()

    manager_instructions = (managerInstructionsPrompt)

    # Build manager agent with the full toolset and handoffs
    recruitment_manager = create_agent(
        "Recruitment Manager",
        manager_instructions,
        tools=list(tools.values()),
        handoff_description="Orchestrate the recruitment pipeline and send the final email",
        handoff_tools=[],
    )

    # also return named tools mapping for programmatic use
    return {
        "manager_agent": recruitment_manager,
        "tools_map": tools,
    }

async def run_recruitment_pipeline_OLD(job_requirement_text: str, hiring_manager_email: str):
    if os.environ.get('OPENAI_API_KEY') is None:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    pipeline = create_recruitment_pipeline()
    manager = pipeline['manager_agent']
    domain = extractDomain(hiring_manager_email)
    candidateData = {
        "linkedin profile data": extractProfileText(),
        "summary text data": extractSummaryText(),
        "resume data": extractResumeData()
    }
    message = (
        f"job_requirement_text:\n{job_requirement_text}\n\n"
        f"hiring_manager_email:\n{hiring_manager_email}\n\n"
        f"candidate_profile_data:\n{candidateData}\n"
    )

    with trace(f"{domain} Tracking for Job Apply Pro AI"):
        result = await Runner.run(manager, message)
    return result

async def run_recruitment_pipeline(job_requirement_text: str, hiring_manager_email: str, reparse: bool = False):
    try:
        domain = extractDomain(hiring_manager_email)
        resumeData = extractResumeData()
        JobAnalyserAgent = Agent(name="Job Requirement Analyzer", instructions=PROMPTS["JobRequirementAnalyzer"], model=OPENAI_AGENT_MODEL)
        CandidateProfileAgent = Agent(name="Candidate Profile Analyzer", instructions=PROMPTS["CandidateProfileAnalyzer"], model=OPENAI_AGENT_MODEL)
        with trace(f"{domain} Profile & JD Tracking for Agentic Apply Pro AI"):
            try:
                if reparse:
                    result = await asyncio.gather(
                        Runner.run(JobAnalyserAgent, job_requirement_text),
                        Runner.run(CandidateProfileAgent, resumeData)
                    )
                else:
                    if os.path.exists("job_apply_pro/output/CandidateProfileAnalysis/CandidateProfileAnalysis.txt"):
                        result = await asyncio.gather(
                            Runner.run(JobAnalyserAgent, job_requirement_text)
                        )
                    else:
                        result = await asyncio.gather(
                            Runner.run(JobAnalyserAgent, job_requirement_text),
                            Runner.run(CandidateProfileAgent, resumeData)
                        )
   
            except Exception as e:
                print(f"Retrying due to error: {e}")
            JDData = result[0].final_output
            if reparse:
                ProfileData = result[1].final_output
            else:
                if os.path.exists("job_apply_pro/output/CandidateProfileAnalysis/CandidateProfileAnalysis.txt"):
                    ProfileData = extractProfileData(f"job_apply_pro/output/CandidateProfileAnalysis/CandidateProfileAnalysis.txt")
                else:
                    ProfileData = result[1].final_output
        output = [JDData, ProfileData]
        saveData(output[0], f"job_apply_pro/output/JobRequirementAnalysis/JobRequirementAnalysis.txt")
        saveData(output[1], f"job_apply_pro/output/CandidateProfileAnalysis/CandidateProfileAnalysis.txt") 
        SubjectCreatorAgent = Agent(name="Email Subject Line Creator", instructions=f"{PROMPTS['EmailSubjectLineCreator']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}", model=OPENAI_AGENT_MODEL)
        HiringManagerEmailDraftsAgent = Agent(name="Hiring Manager Email Draftsman", instructions=f"{PROMPTS['HiringManagerEmailDraftsman']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}", model=OPENAI_AGENT_MODEL)
        SubjectCreatorAgentTool = SubjectCreatorAgent.as_tool(
            tool_name="subject_creator",
            tool_description=f"{PROMPTS['EmailSubjectLineCreator']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}"
        )
        HiringManagerEmailDraftsAgentTool = HiringManagerEmailDraftsAgent.as_tool(
            tool_name="email_draftsman",
            tool_description=f"{PROMPTS['HiringManagerEmailDraftsman']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}"
        )
        EmailReviewerEvaluatorAgent = Agent(name="Email Reviewer Evaluator", instructions=f"{PROMPTS['EmailReviewerEvaluator']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}", model=OPENAI_AGENT_MODEL, tools=[HiringManagerEmailDraftsAgentTool, SubjectCreatorAgentTool])
        with trace(f"{domain} Email Drafting & Reviewing for Agentic Apply Pro AI"):
            response = await Runner.run(EmailReviewerEvaluatorAgent, f"{PROMPTS['EmailReviewerEvaluator']} Job Requirement Analysis:\n{JDData}\n\nCandidate Profile Analysis:\n{ProfileData}")
        print("Phase 2 Output:", response.final_output)
        final_output = response.final_output
        if isinstance(final_output, str):
            try:
                final_output = json.loads(final_output)
            except Exception as e:
                print("Error parsing final_output JSON:", e)
                print("Raw output:", final_output)
                raise
        if final_output["is_satisfied"] is True:
            final_output = {
                "subject": final_output["final_subject"],
                "body": final_output["final_email_body"]
                }
            saveDataJson(final_output, f"job_apply_pro/output/EmailDraftsResponse/EmailDraftsResponse.json")
            open_email_default(hiring_manager_email, final_output["subject"], final_output["body"])

    except Exception as e:
        print(f"Error in run_recruitment_pipeline: {e}")
        output = None
    return output

def extractDomain(email: str) -> str:
    """Extract domain from email address."""
    try:
        return email.split('@')[1]
    except IndexError:
        return ""

def extractProfileText() -> str:
    reader = PdfReader("job_apply_pro/me/Profile.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extractSummaryText() -> str:
    with open("job_apply_pro/me/Summary.txt", "r", encoding="utf-8") as file:
        return file.read()

def extractResumeData() -> str:
    reader = PdfReader("job_apply_pro/me/VirenderFullstackResume.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def saveData(data: str, path: str) -> bool:
    try:
        abs_path = os.path.abspath(path)
        folder = os.path.dirname(abs_path)
        os.makedirs(folder, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(data)
        # print(f"File created successfully at {abs_path}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    
def saveDataJson(data: dict, path: str) -> bool:
    try:
        abs_path = os.path.abspath(path)
        folder = os.path.dirname(abs_path)
        os.makedirs(folder, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True

    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False


def extractProfileData(path) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

