# llm/utils.py
import openai
import re
from config.config import OPENAI_API_KEY, LLM_MODEL
from kg.history_manager import load_user_history
import json
openai.api_key = OPENAI_API_KEY


def predict_next_action(prompt):
    response = openai.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a home assistant robot."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()


def generate_prompt_for_goals(
        current_command,
        previous_command=None,
        context=None,
        context_items=None,
        missing_components=None,
        predicted_history_command=None,
        context_expanded_info=None
):
    import json
    from kg.history_manager import load_user_history

    user_command_history = load_user_history()
    old_history_entries = []
    new_history_entries = []
    new_session_found = False

    for line in user_command_history:

        if "=== New Session ===" in line:
            new_session_found = True
            continue
        if '|' in line:
            entry = f"- {line.split('|', 1)[1].strip()}"
            if new_session_found:
                new_history_entries.append(entry)
            else:
                old_history_entries.append(entry)

    history_str = "\n".join(old_history_entries) if old_history_entries else "N/A"
    new_history_str = "\n".join(new_history_entries) if new_history_entries else "N/A"

    prev_str = f"**Previous Command:** \"{previous_command}\"" if previous_command else ""
    context_str = f"**Context:** {context}" if context else "**Context:** N/A"

    if isinstance(context_items, dict):
        context_items_str = "**Context Items from KG:**\n"
        for key_name, detail_map in context_items.items():
            context_items_str += f"- expansions for '{key_name}' :\n"
            for ent, val in detail_map.items():
                line = f"{val['props_str']} (similarity={val['score']:.2f})"
                context_items_str += f"   {line}\n"
    else:
        context_items_str = "**Context Items:** N/A"

    feedback_str = ""
    if missing_components and len(missing_components) > 0:
        feedback_str = """
            **User Feedback / Additional Instructions:**
            The user has provided the following specific feedback or requirements that must now guide your next predicted command:
        """
        for comp in set(missing_components):
            feedback_str += f"\n- {comp}"
        feedback_str += """
            The above feedback overrides or supplements previous logic. 
            You must incorporate these instructions into your next predicted action and ASP goal. 
            If the user requests something different from the previous logic (e.g., providing food instead of lighting), 
            you must comply and produce a new command aligned with this feedback.

            YOU MUST FOLLOW THIS FEEDBACK IMMEDIATELY.
        """

    if predicted_history_command:
        predicted_history_str = f"**Predicted History Command:** {predicted_history_command}"
    else:
        predicted_history_str = "**Predicted History Command:** None"

    if context_expanded_info:
        expanded_info_str = (
                "**Expanded Context from KG:**\n"
                + json.dumps(context_expanded_info, indent=2)
        )
    else:
        expanded_info_str = "**Expanded Context from KG:** None"

    prompt = f"""
            You are an assistant that predicts the next best action for the user based on their current command, previous command, user history, and the current context.

            **User's High-Level Command History:**
            (Old History)
            {history_str}

            **New History Entries (High Priority):**
            {new_history_str}

            **Additional Instruction for History Suggestion:**
            We have a recommended next command from the user's history:
            {predicted_history_str}

            1) If the environment states do not conflict with that suggested command, you should adopt it as the final "Predicted Command."
            2) If the environment already meets that suggestion or otherwise conflicts with it (e.g., the lamp is already on, or the item no longer exists), you must propose a new high-level command instead. 
               - In that case, you must explain explicitly **which environment state** prevents adopting the suggestion from history.
               - Then provide a new valid "Predicted Command" that logically follows from the current state.
            3) If user give a feedback to what to do, you need to always follow user's feedback and generate results for it regardless of the history suggestions.
            {expanded_info_str}
            4) You should also take the {current_command} into consideration. For example, if the current command is "open(fridge)", even though the current fridge state is "CLOSED", you should still account for the impact of the current command. Since executing "open(fridge)" will change the fridge state to "OPEN", the next predicted command should consider this updated state. Therefore, you should not predict opening the fridge again, as it would already be open after the execution of the current command.
            **Instructions:**

            - Your task is to generate a high-level task that logically progresses from the user's current command.
            - If the user requests "prepare a cup of tea," suggest "grab book" or "switchon lamp" based on the history and logical continuation, instead of repeating "grab tea."
            - The predicted task must be different from the current command and should align with the logical flow of tasks in the user's history.
            - The new task must not repeat the current command and should instead align with the logical flow of high-level tasks in the user's history.
            - Use the current context, top relevant items, and the user's history (especially the new entries which have higher priority) to infer the next logical task.
            - Ensure the task aligns with high-level goals, not intermediate or repetitive actions.
            - **Provide your response in the following format:**
                  Predicted Command: [action] [object]
                  Reason: [Provide a brief explanation of why this action is appropriate.]
                  ASP Goal: goal(I) :- holds([predicate](arg1, arg2, ...), I).

            **Important Notes:**

            - Replace `[action]` with the action you recommend.
            - Replace `[object]` with the object of the action, if applicable.
            - Do **not** include parentheses, commas, or additional arguments in the `Predicted Command`.
            - `[action]` and `[object]` should be separated by a single space.
            - If the action involves an agent or additional parameters, assume they are implicit and do not include them in the command.
            - Ensure that the `ASP Goal` follows the correct syntax as shown.
            **AvailableActions:**
                - grab(agent, item, furniture)
                - grab(agent, item, user)
                - putin(agent, item, furniture)
                - put(agent, item, furniture)
                - give(agent, item, user)
                - switchon(agent, switch_furniture_light)
                - switchoff(agent, switch_furniture_light)
                - open(agent, furniture)
                - close(agent, furniture)

            **AvailableItems:**
                - cellphone
                - folder
                - book
                - mug
                - notes
                - magazine
                - milk
                - chicken
                - cutlets
                - alcohol
                - juice
                - apple
                - bananas
                - peach
                - cereal
                - cupcake
                - crackers
                - poundcake
                - plate

            **AvailablePredicates:**
                Here are the possible `holds` predicates, each describing a specific aspect of the environment's state or the agent's interactions with items and furniture. **Use only these predicates to represent the final goal state. Do not use any predicates not listed below.**

                - **User Possession:**
                   has- The user possesses the item.

                - **Open/Locked States:**
                   open- A piece of furniture or device is in an open/on state.
                   closed- A piece of furniture or device is in a closed/off state.
                - **Heated Items:**
                   heated - The item is heated.

                - **Item Placement:**
                  put_inside- An item is inside a piece of furniture.
                  on- An item is on top of a piece of furniture.

                - **Switched States:**
                  turn_on- A switchable furniture is turned on.
                  switched_off- A switchable furniture is turned off.
            **Environment and Input Details:**

            <CurrentCommand>{current_command}</CurrentCommand>
            (Old History)
            {history_str}
            (New High Priority History)
            {new_history_str}
            {prev_str}
            {context_str}
            {context_items_str}
            {feedback_str}

            {predicted_history_str}
            {expanded_info_str}

            <Instructions>
                <Step>1. Analyze the user's current command, previous command, and context. The next predicted task should be a new high-level action that follows logically from the previous actions, context, and items. It has to be one goal instead of multiple goals.</Step>
                <Step>2. Based on the context and environment, propose a relevant next task in the format of action + object. **Only use actions from the `AvailableActions` list.** For example, use "grab book" or "switchon lamp". Also remember ONLY ONE PREDICTION TASK</Step>
                <Step>3. Translate the high-level action into an ASP goal structure. The ASP goal structure should accurately capture the intended final state for each task, based on the relationships and conditions that must be true once the task is completed. To avoid common mistakes, follow these detailed guidelines:
                           - **Example Explanation**: For a task like "give the user a book," the goal should be that the "book" is in the possession of the user, not the agent. Represent this by using `holds(has(user, book), I)`, which means "the user has the book at step I." Avoid incorrectly stating that the book is with the agent, as the goal is for the user to have it, not the agent.
                           - **Avoid Incorrect References to agent When the Goal Involves the User**: If the task involves transferring an item to the user, ensure that the item's location references the user (e.g., `holds(has(user, book), I)`) and not the agent. Only use `holds(has(agent, item), I)` if the task explicitly requires the agent to possess the item.
                           - **ASP Goal Structure Interpretation**: In ASP, goals should describe the desired end state rather than intermediate actions. For example:
                              - "Give book to user" should be translated as `goal(I) :- holds(has(user, book), I).`, ensuring that the user possesses the book and their location is known.
                              - "Turn on the table lamp" should be represented as `goal(I) :- holds(turn_on(lamp), I).`, indicating that the table lamp is in the 'on' state at the completion of the task.
                           - **General Approach for Other Goals**: For similar tasks, think about where items or states should end up, focusing on the end result:
                              - If fetching an item to give to the user, use `goal(I) :- holds(has(user, item), I).`, as the agent should end up with the user possessing the item.
                           - **ASP Syntax Validation**: Ensure that each ASP goal structure follows the correct syntax. Every goal statement should start with `goal(I) :-` and be followed by one `holds(...)` predicate. Close each predicate in `holds(...)` with parentheses, and close the entire structure with a period (`.`) at the end to avoid syntax errors.
                           - **Avoid using compound words.**
                </Step>
                       - **Avoid using compound words.**
            </Instructions>

            <Example>
                <Scenario>If the user requests "bring me the book," instead of repeating "give book," analyze the context and suggest a related task, like "grab book" or "switchon lamp" if appropriate.</Scenario>
            </Example>

            <OutputFormat>
                Predicted Command: <Your predicted action and item here, format as :[action] [object]>
                Reason: <Explain why this command was chosen based on context and logical progression>
                ASP goals: goal(I) :- holds(<Your goal components here>, I).
                Goals: <Next high-level ASP-compatible goal components, e.g., has(user, book)>
            </OutputFormat>
        """
    return prompt


def extract_response_details(response):
    predicted_command = ""
    reason = ""
    asp_goal = ""
    goals = []

    lines = response.strip().split('\n')

    for line in lines:
        line_str = line.strip().lower()
        if line_str.startswith('predicted command:'):
            predicted_command = line.split(':', 1)[1].strip()
        elif line_str.startswith('reason:'):
            reason = line.split(':', 1)[1].strip()
        elif line_str.startswith('asp goal') or line_str.startswith('asp goals'):
            asp_goal_match = re.search(
                r'ASP Goal[s]?:\s*goal\(I\)\s*:-\s*holds\((.+?),\s*I\)\.',
                line,
                re.IGNORECASE
            )
            if asp_goal_match:
                asp_goal = asp_goal_match.group(0).strip()
                holds_part = asp_goal_match.group(1).strip()
                hold_match = re.match(r'(\w+)\(([^)]+)\)', holds_part)
                if hold_match:
                    predicate = hold_match.group(1).strip()
                    obj = hold_match.group(2).strip()
                    goals.append(f"{predicate}({obj})")
        elif line_str.startswith('goals:'):
            goals_content = line.split(':', 1)[1].strip()
            goals_split = re.findall(r'\w+\([^)]*\)', goals_content)
            goals.extend(goals_split)

    goals = list(set(goals))
    return predicted_command, asp_goal, reason, goals
