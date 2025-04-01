# llm/predictor.py
from llm.utils import predict_next_action, generate_prompt_for_goals, extract_response_details

def run_prediction(user_command, previous_command, first_command, context=None, context_items=None):
    prompt = generate_prompt_for_goals(
        current_command=user_command,
        previous_command=previous_command,
        context=context,
        context_items=context_items
    )
    response = predict_next_action(prompt)
    predicted_command, asp_goal, reason, goals = extract_response_details(response)
    return predicted_command, asp_goal, reason, goals
