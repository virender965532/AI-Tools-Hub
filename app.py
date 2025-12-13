from agents import trace
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlparse
# from debate.src.debate.crew import Debate
from job_apply_pro.job_apply_pro import run_recruitment_pipeline
from superviouser import superviouser_agentic_handoff
# StockPickerCrew is imported lazily in start_stock_picker() to avoid import-time initialization
import os
import yaml
import json
import asyncio
import threading
import importlib.util
import re
from Constants.constants import get_ai_tools

load_dotenv()
app = Flask(__name__)
app.secret_key = "supersecretkey"

# === File Paths ===
BASE_DIR = os.path.dirname(__file__)
DEBATER_AGENTS_FILE = os.path.join(BASE_DIR, "debate/src/debate/config/agents.yaml")
DEBATER_TASKS_FILE = os.path.join(BASE_DIR, "debate/src/debate/config/tasks.yaml")
STOCK_AGENTS_FILE = os.path.join(BASE_DIR, "stock_picker_advance", "src", "stock_picker", "config", "agents.yaml")
STOCK_TASKS_FILE = os.path.join(BASE_DIR, "stock_picker_advance", "src", "stock_picker", "config", "tasks.yaml")
STOCK_OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")


# === ROUTES ===

@app.route("/")
def home():
    current_year = datetime.now().year
    tools = get_ai_tools()
    return render_template("home.html", year=current_year, tools=tools)


@app.route("/ai/tool/agentic-applypro/about")
def jobapply_about():
    current_year = datetime.now().year
    return render_template("jobapplypro_about.html", year=current_year)

@app.route("/ai/tool/agentic-applypro", methods=["GET", "POST"])
def jobapply():
    current_year = datetime.now().year

    # Default values (for GET or failed POST)
    old_values = {
        "hiring_manager_email": "virender8800745356@gmail.com",
        "job_requirement": """Job Summary:


We are looking for a skilled ReactJS Developer to join our team. The ideal candidate will be responsible for developing and implementing user interface components using ReactJS concepts and workflows. You will also be responsible for profiling and improving front-end performance and documenting our front-end codebase.


Key Responsibilities:


Develop new user-facing features using ReactJS.
Build reusable components and front-end libraries for future use.
Optimize components for maximum performance across a vast array of web-capable devices and browsers.
Collaborate with designers, backend developers, and product managers to deliver high-quality solutions.
Write clean, maintainable, and efficient code following best practices.
Troubleshoot and debug application issues.

Required Skills & Qualifications:


Strong proficiency in JavaScript, including DOM manipulation and the JavaScript object model.
Thorough understanding of ReactJS and its core principles.
Experience with popular ReactJS workflows (such as Redux, Context API, or MobX).
Familiarity with RESTful APIs and JSON.
Knowledge of modern front-end build pipelines and tools (Webpack, Babel, etc.).
Experience with HTML5, CSS3, and responsive design principles.
Familiarity with Git and version control systems.
Good understanding of cross-browser compatibility issues.""",
        "reparse": False
    }
    
    if request.method == "POST":
        # Extract inputs from form
        hiring_manager_email = request.form.get("hiring_manager_email", "").strip()
        job_requirement = request.form.get("job_requirement", "").strip()
        reparse = request.form.get("reparse", "off") == "on"
    
        # Store old values back so template can reuse them
        old_values = {
            "hiring_manager_email": hiring_manager_email,
            "job_requirement": job_requirement,
            "reparse": reparse
        }

        # 1. Empty fields
        if not hiring_manager_email or not job_requirement:
            flash("All fields are required. Please fill out the form completely.", "danger")
            return render_template("jobapplypro.html", year=current_year, old=old_values)

        # 2. Email format
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, hiring_manager_email):
            flash("Invalid email format for Hiring Manager Email.", "danger")
            return render_template("jobapplypro.html", year=current_year, old=old_values)

        # 3. JD min length
        if len(job_requirement) < 30:
            flash("Job description is too short. Please paste the full requirement.", "warning")
            return render_template("jobapplypro.html", year=current_year, old=old_values)

        try:
            result = asyncio.run(run_recruitment_pipeline(
                job_requirement,
                hiring_manager_email,
                reparse
            ))

            safe_result = result.to_dict() if hasattr(result, "to_dict") else result
            if isinstance(safe_result, str):
                safe_result = json.loads(safe_result)
            print("Pipeline Result:", safe_result.final_output)
            if safe_result.final_output:

                # Extract email domain
                domain = hiring_manager_email.split("@")[1]     # e.g., gmail.com

                # Timestamp in format: 2025_12_03_01_11_13
                timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

                # Filename
                filename = f"{domain}_{timestamp}.json"

                # Folder to store saved pipeline results
                save_dir = "job_apply_pro/history"
                os.makedirs(save_dir, exist_ok=True)

                # Full file path
                filepath = os.path.join(save_dir, filename)

                # Save JSON file
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(safe_result.final_output, f, ensure_ascii=False, indent=4)

                flash(f"Job application email sent successfully and saved as {filename}", "success")

            else:
                flash(f"Failed to send email: {safe_result.get('error')}", "danger")

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")

        # Continue to next step
        return redirect(url_for("jobapply"))

    # GET Request
    return render_template("jobapplypro.html", year=current_year, old=old_values)



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

# @app.route("/ai/tool/nuro-debater/about")
# def nuro_debater_about():
    """About Page for Neuro Debater"""
    current_year = datetime.now().year
    return render_template("debater/nuro_debater_about.html", year=current_year)


# @app.route("/ai/tool/nuro-debater")
# def nuro_debater():
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


# @app.route("/ai/tool/nuro-debater/start", methods=["POST"])
# def start_nuro_debater():
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


# @app.route("/ai/tool/stock-picker/about")
# def stock_picker_about():
    """About Page for StockCraft AI (Stock Picker)"""
    current_year = datetime.now().year
    return render_template("stock_picker/stock_picker_about.html", year=current_year)


# @app.route("/ai/tool/stock-picker")
# def stock_picker():
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

    # Load output files for Previous Outputs section
    outputs_data = {}
    
    # 1. Industry Mapping (YAML)
    try:
        industry_mapping_file = os.path.join(STOCK_OUTPUTS_DIR, "01_industry_mapping.yaml")
        # Robust YAML loader: try safe_load, then try simple normalization and fallbacks
        def load_yaml_resilient(path):
            import re, ast
            txt = open(path, "r", encoding="utf-8").read()
            try:
                return yaml.safe_load(txt) or {}
            except Exception:
                # Try removing accidental leading indentation on mapping keys
                try:
                    normalized = re.sub(r'^\s+(?=[A-Za-z0-9_\-]+:)', '', txt, flags=re.M)
                    return yaml.safe_load(normalized) or {}
                except Exception:
                    pass
                # Try extracting JSON-like block
                m = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', txt)
                if m:
                    try:
                        return json.loads(m.group(1)) or {}
                    except Exception:
                        pass
                # Last resort: very simple key: value parser (handles lists and strings)
                result = {}
                for line in txt.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' not in line:
                        continue
                    k, v = line.split(':', 1)
                    k = k.strip()
                    v = v.strip()
                    # try to parse v as Python literal (list / string)
                    try:
                        parsed = ast.literal_eval(v)
                    except Exception:
                        # remove surrounding quotes if any
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")): parsed = v[1:-1]
                        else: parsed = v
                    result[k] = parsed
                return result

        outputs_data["industry_mapping"] = load_yaml_resilient(industry_mapping_file) or {}
    except Exception:
        outputs_data["industry_mapping"] = {}

    # 2. Candidates (JSON)
    try:
        candidates_file = os.path.join(STOCK_OUTPUTS_DIR, "02_candidates.json")
        with open(candidates_file, "r", encoding="utf-8") as f:
            candidates_raw = json.load(f)
        if isinstance(candidates_raw, list):
            outputs_data["candidates"] = candidates_raw
        elif isinstance(candidates_raw, dict):
            outputs_data["candidates"] = candidates_raw.get("root", candidates_raw.get("candidates", []))
        else:
            outputs_data["candidates"] = []
    except Exception:
        outputs_data["candidates"] = []

    # 3. Screened Metrics (JSON)
    try:
        screened_metrics_file = os.path.join(STOCK_OUTPUTS_DIR, "03_screened_metrics.json")
        with open(screened_metrics_file, "r", encoding="utf-8") as f:
            try:
                metrics_raw = json.load(f)
            except Exception:
                # fallback: extract JSON block from text
                f.seek(0)
                txt = f.read()
                import re
                m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", txt)
                if m:
                    try:
                        metrics_raw = json.loads(m.group(1))
                    except Exception:
                        metrics_raw = None
                else:
                    metrics_raw = None
        if isinstance(metrics_raw, list):
            outputs_data["screened_metrics"] = metrics_raw
        elif isinstance(metrics_raw, dict):
            outputs_data["screened_metrics"] = metrics_raw.get("root", metrics_raw.get("screened_metrics", []))
        else:
            outputs_data["screened_metrics"] = []
    except Exception:
        outputs_data["screened_metrics"] = []

    # 4. Valuation Rank (JSON)
    try:
        valuation_rank_file = os.path.join(STOCK_OUTPUTS_DIR, "04_valuation_rank.json")
        with open(valuation_rank_file, "r", encoding="utf-8") as f:
            valuation_raw = json.load(f)
        if isinstance(valuation_raw, list):
            outputs_data["valuation_rank"] = valuation_raw
        elif isinstance(valuation_raw, dict):
            outputs_data["valuation_rank"] = valuation_raw.get("root", valuation_raw.get("valuation_rank", []))
        else:
            outputs_data["valuation_rank"] = []
    except Exception:
        outputs_data["valuation_rank"] = []

    # 5. News & Risks (JSON)
    try:
        news_risks_file = os.path.join(STOCK_OUTPUTS_DIR, "05_news_risks.json")
        with open(news_risks_file, "r", encoding="utf-8") as f:
            try:
                news_raw = json.load(f)
            except Exception:
                f.seek(0)
                txt = f.read()
                import re
                m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", txt)
                if m:
                    try:
                        news_raw = json.loads(m.group(1))
                    except Exception:
                        news_raw = None
                else:
                    news_raw = None
        if isinstance(news_raw, list):
            outputs_data["news_risks"] = news_raw
        elif isinstance(news_raw, dict):
            outputs_data["news_risks"] = news_raw.get("root", news_raw.get("news_risks", []))
        else:
            outputs_data["news_risks"] = []
    except Exception:
        outputs_data["news_risks"] = []

    # 6. Shortlist (Markdown - parse as JSON)
    try:
        shortlist_file = os.path.join(STOCK_OUTPUTS_DIR, "06_shortlist.md")
        with open(shortlist_file, "r", encoding="utf-8") as f:
            shortlist_content = f.read()
            # Extract JSON from markdown
            import re
            json_match = re.search(r'\{[\s\S]*\}', shortlist_content)
            if json_match:
                shortlist_json = json.loads(json_match.group())
                outputs_data["shortlist"] = shortlist_json.get("picks", [])
            else:
                outputs_data["shortlist"] = []
    except Exception:
        outputs_data["shortlist"] = []

    return render_template(
        "stock_picker/stock_picker.html",
        year=current_year,
        agents=agents_data,
        tasks=tasks_data,
        outputs=outputs_data,
        result=None,
    )


# @app.route("/ai/tool/stock-picker/start", methods=["POST"])
# def start_stock_picker():
    form = request.form
    industry = form.get("industry", "").strip()
    region = form.get("region", "India").strip() or "India"
    n_picks = int(form.get("n_picks") or 5)
    try:
        min_mcap = int(form.get("min_mcap") or 500000000)
    except Exception:
        min_mcap = 500000000
    valuation_pref = form.get("valuation_pref") or "balanced"

    # Validate required fields
    if not industry:
        flash("Industry is required.", "danger")
        return redirect(url_for("stock_picker"))

    def run_crew_background(industry_local, region_local, n_picks_local, min_mcap_local, valuation_pref_local):
        """Run crew in background thread with lazy loading of StockPickerCrew."""
        try:
            # Ensure environment variables are loaded
            import os as os_module
            if not os_module.getenv("OPENAI_API_KEY"):
                from dotenv import load_dotenv
                load_dotenv()
            
            # Set CHROMA_OPENAI_API_KEY if OPENAI_API_KEY is set
            if os_module.getenv("OPENAI_API_KEY") and not os_module.getenv("CHROMA_OPENAI_API_KEY"):
                os_module.environ["CHROMA_OPENAI_API_KEY"] = os_module.getenv("OPENAI_API_KEY")
            
            # Add stock_picker_advance to sys.path so relative imports work
            import sys
            stock_picker_path = os.path.join(BASE_DIR, "stock_picker_advance")
            if stock_picker_path not in sys.path:
                sys.path.insert(0, stock_picker_path)
            
            # Now we can import normally
            from src.stock_picker.crew import StockPickerCrew

            crew = StockPickerCrew().crew()
            inputs = {
                "industry": industry_local,
                "region": region_local,
                "n_picks": n_picks_local,
                "min_mcap": min_mcap_local,
                "valuation_pref": valuation_pref_local,
            }
            result = crew.kickoff(inputs=inputs)
            print(f"✅ Stock Picker Crew Completed for {industry_local}")
        except Exception as e:
            print(f"❌ Stock Picker Crew Failed for {industry_local}: {e}")
            import traceback
            traceback.print_exc()

    # Start crew in background thread (pass arguments explicitly)
    thread = threading.Thread(
        target=run_crew_background,
        args=(industry, region, n_picks, min_mcap, valuation_pref),
        daemon=True,
    )
    thread.start()

    # Redirect immediately
    flash(f"Stock picker analysis started for {industry}. Results will be available shortly.", "info")
    return redirect(url_for("stock_picker"))


# === Fallback Tool Page ===

# @app.route("/tool/<tool_name>")
# def tool_page(tool_name):
    try:
        return render_template("ai_page.html", tool_name=tool_name)
    except Exception as e:
        return render_template("error.html", error_message=str(e))


# === MAIN ===
if __name__ == "__main__":
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug_mode, port=port)