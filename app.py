from agents import trace
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from datetime import datetime
from debate.src.debate.crew import Debate
from superviouser import superviouser_agentic_handoff
# from stock_picker.crew import StockPickerCrew
import os
import yaml
import asyncio

load_dotenv()
app = Flask(__name__)
app.secret_key = "supersecretkey"

# === File Paths ===
BASE_DIR = os.path.dirname(__file__)
DEBATER_AGENTS_FILE = os.path.join(BASE_DIR, "debate/src/debate/config/agents.yaml")
DEBATER_TASKS_FILE = os.path.join(BASE_DIR, "debate/src/debate/config/tasks.yaml")
STOCK_AGENTS_FILE = os.path.join(BASE_DIR, "stock-picker-advance", "src", "stock_picker", "config", "agents.yaml")
STOCK_TASKS_FILE = os.path.join(BASE_DIR, "stock-picker-advance", "src", "stock_picker", "config", "tasks.yaml")


# === ROUTES ===

@app.route("/")
def home():
    """Home Page - Shows Available AI Tools"""
    current_year = datetime.now().year
    tools = [
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot1.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI: Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot13.png"
        },
        {
            "url": "/ai/tool/stock-picker/about",
            "title": "StockCraft AI: CrewAI Industry Stock Picker",
            "description": "StockCraft AI uses a CrewAI multi-agent pipeline to discover, screen and rank public companies by industry with auditable outputs and configurable weighting (value/growth/balanced).",
            "image": "images/robot6.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot2.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot4.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot5.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot6.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot7.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot8.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot9.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot10.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot11.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot12.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot13.png"
        },
        {
            "url": "/ai/tool/nuro-debater/about",
            "title": "Neuro Debate AI - Autonomous Multi-Agent Debate System",
            "description": """Neuro Debate AI simulates structured debates between intelligent AI entities using CrewAI orchestration.""",
            "image": "images/robot14.png"
        },
        {
            "url": "/ai/tool/superviouser/about",
            "title": "Superviouser: An Autonomous Multi-Agent Email Intelligence System",
            "description": """Superviouser is an advanced AI-driven agent orchestration framework designed to autonomously generate, evaluate, format, and deliver cold sales emails using multi-agent collaboration.""",
            "image": "images/robot5.png"
        },
    ]
    return render_template("home.html", year=current_year, tools=tools)


# === Superviouser Pages ===

@app.route("/ai/tool/superviouser/about")
def superviouser_about():
    current_year = datetime.now().year
    return render_template("superviouser_about.html", year=current_year)


@app.route("/ai/tool/superviouser", methods=["GET", "POST"])
def superviouser():
    """Handles Superviouser Email AI Tool"""
    if request.method == "POST":
        recipient_email = request.form.get("email")
        instructions1 = request.form.get("instructions1", "")
        instructions2 = request.form.get("instructions2", "")
        instructions3 = request.form.get("instructions3", "")
        manager_instructions = request.form.get("manager_instructions", "")

        if not all([recipient_email, instructions1, instructions2, instructions3, manager_instructions]):
            flash("All fields are required.", "danger")
            return redirect(url_for("superviouser"))

        try:
            result = asyncio.run(superviouser_agentic_handoff(
                recipient_email,
                instructions1,
                instructions2,
                instructions3,
                manager_instructions
            ))

            if result.get("status") == "success":
                flash(f"Email sent successfully to {recipient_email}!", "success")
            else:
                flash(f"Failed to send email: {result.get('error')}", "danger")

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")

        return redirect(url_for("superviouser"))

    return render_template("superviouser.html")


# === Neuro Debater Pages ===

@app.route("/ai/tool/nuro-debater/about")
def nuro_debater_about():
    """About Page for Neuro Debater"""
    current_year = datetime.now().year
    return render_template("debater/nuro_debater_about.html", year=current_year)


@app.route("/ai/tool/nuro-debater")
def nuro_debater():
    """Loads Editable YAML UI for Neuro Debater"""
    current_year = datetime.now().year
    try:
        with open(DEBATER_AGENTS_FILE, "r", encoding="utf-8") as f:
            agents_yaml = f.read()
        with open(DEBATER_TASKS_FILE, "r", encoding="utf-8") as f:
            tasks_yaml = f.read()
    except Exception as e:
        agents_yaml = f"# Failed to load agents.yaml: {e}"
        tasks_yaml = f"# Failed to load tasks.yaml: {e}"

    return render_template(
        "debater/nuro_debater.html",
        year=current_year,
        agents_yaml=agents_yaml,
        tasks_yaml=tasks_yaml
    )


@app.route("/ai/tool/nuro-debater/start", methods=["POST"])
def start_nuro_debater():
    import yaml

    form = request.form
    motion = form.get("motion", "")

    # ✅ 1. Define agents with consistent names
    agents_yaml_data = {
        "debater": {
            "role": form.get("debater_role") or "Debater",
            "goal": form.get("debater_goal") or "Argue for or against a motion logically",
            "backstory": form.get("debater_backstory") or "An experienced AI debater trained on argumentation.",
            "llm": form.get("debater_llm") or "gpt-4o-mini"
        },
        "judge": {
            "role": form.get("judge_role") or "Judge",
            "goal": form.get("judge_goal") or "Evaluate arguments objectively and decide the winner.",
            "backstory": form.get("judge_backstory") or "A fair and analytical debate judge.",
            "llm": form.get("judge_llm") or "gpt-4o-mini"
        }
    }

    # ✅ 2. Ensure the `agent` field in tasks refers to these keys
    tasks_yaml_data = {
        "propose": {
            "description": form.get("propose_desc") or "Argue in favor of the motion.",
            "expected_output": form.get("propose_output") or "A strong argument supporting the motion.",
            "agent": "debater",  # 🔥 matches above key
            "output_file": form.get("propose_file") or "propose.txt"
        },
        "oppose": {
            "description": form.get("oppose_desc") or "Argue against the motion.",
            "expected_output": form.get("oppose_output") or "A strong rebuttal opposing the motion.",
            "agent": "debater",  # 🔥 same agent name
            "output_file": form.get("oppose_file") or "oppose.txt"
        },
        "decide": {
            "description": form.get("decide_desc") or "Decide which argument is stronger and why.",
            "expected_output": form.get("decide_output") or "A decision and reasoning summary.",
            "agent": "judge",  # 🔥 matches above key
            "output_file": form.get("decide_file") or "decision.txt"
        }
    }

    # ✅ Convert to YAML strings
    agents_yaml_str = yaml.dump(agents_yaml_data, sort_keys=False, allow_unicode=True)
    tasks_yaml_str = yaml.dump(tasks_yaml_data, sort_keys=False, allow_unicode=True)

    # ✅ Load into CrewAI Debater
    
    debate_crew = Debate()
    # debate_crew.agents_config = DEBATER_AGENTS_FILE
    # debate_crew.tasks_config = DEBATER_TASKS_FILE
    crew_instance = debate_crew.crew()
    result = crew_instance.kickoff(inputs={"motion": motion})
    # 🧩 Collect outputs by task name
    conversation = {
        "propose": None,
        "oppose": None,
        "decide": None
    }

    for task in crew_instance.tasks:
        if hasattr(task, "output") and task.output:
            if "propose" in task.name.lower():
                conversation["propose"] = task.output
            elif "oppose" in task.name.lower():
                conversation["oppose"] = task.output
            elif "decide" in task.name.lower():
                conversation["decide"] = task.output

    # ✅ Print to console for debugging
    print("\n========= Debate Conversation =========")
    for k, v in conversation.items():
        print(f"\n--- {k.upper()} ---\n{v}\n")
    print("=======================================\n")



    return render_template(
        "debater/nuro_debater_result.html",
        motion=motion,
        conversation=conversation,
        result=str(result),
        year=datetime.now().year
    )


@app.route("/ai/tool/stock-picker/about")
def stock_picker_about():
    """About Page for StockCraft AI (Stock Picker)"""
    current_year = datetime.now().year
    return render_template("stock_picker/stock_picker_about.html", year=current_year)


@app.route("/ai/tool/stock-picker")
def stock_picker():
    """Loads editable YAML UI for Stock Picker"""
    current_year = datetime.now().year
    try:
        with open(STOCK_AGENTS_FILE, "r", encoding="utf-8") as f:
            agents_yaml = f.read()
    except Exception as e:
        agents_yaml = f"# Failed to load agents.yaml: {e}"

    try:
        with open(STOCK_TASKS_FILE, "r", encoding="utf-8") as f:
            tasks_yaml = f.read()
    except Exception as e:
        tasks_yaml = f"# Failed to load tasks.yaml: {e}"

    # parse agents yaml to provide structured defaults for the form
    try:
        agents_data = yaml.safe_load(agents_yaml) or {}
        tasks_data = yaml.safe_load(tasks_yaml) or {}
    except Exception:
        agents_data = {}
        tasks_data = {}

    return render_template(
        "stock_picker/stock_picker.html",
        year=current_year,
        agents=agents_data,
        tasks=tasks_data,
        result=None,
    )


# @app.route("/ai/tool/stock-picker/start", methods=["POST"])
# def start_stock_picker():
#     form = request.form
#     industry = form.get("industry", "").strip()
#     region = form.get("region", "global").strip() or "global"
#     n_picks = int(form.get("n_picks") or 5)
#     try:
#         min_mcap = int(form.get("min_mcap") or 500000000)
#     except Exception:
#         min_mcap = 500000000
#     valuation_pref = form.get("valuation_pref") or "balanced"

#     if not industry:
#         flash("Industry is required.", "danger")
#         return redirect(url_for("stock_picker"))

#     try:
#         crew = StockPickerCrew().crew()
#         inputs = {
#             "industry": industry,
#             "region": region,
#             "n_picks": n_picks,
#             "min_mcap": min_mcap,
#             "valuation_pref": valuation_pref,
#         }

#         result = crew.kickoff(inputs=inputs)
#         # render template with result
#         return render_template("stock_picker/stock_picker.html", year=datetime.now().year, agents_yaml=None, tasks_yaml=None, result=str(result))

#     except Exception as e:
#         flash(f"Failed to run StockPicker crew: {e}", "danger")
#         return redirect(url_for("stock_picker"))


# === Fallback Tool Page ===

@app.route("/tool/<tool_name>")
def tool_page(tool_name):
    try:
        return render_template("ai_page.html", tool_name=tool_name)
    except Exception as e:
        return render_template("error.html", error_message=str(e))


# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)
