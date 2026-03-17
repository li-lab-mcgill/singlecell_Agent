
NOTEBOOK_PROMPT = """
You are an expert deep learning engineer and code reviewer.
Your task is to produce a technical, implementation-focused summary of the provided code.

Goal

Generate a clear, structured analysis describing how the current pipeline works, focusing on actual design choices and implementation details.

What to Analyze

1) Data Pipeline & Preprocessing

Describe the concrete preprocessing workflow:
	•	Data loading strategy and formats
	•	Feature construction / engineering steps
	•	Normalization, scaling, filtering, encoding, or transformations
	•	Handling of modalities, alignment, or batching
	•	Train/validation/test split strategy and reproducibility choices
	•	Libraries used (e.g., Scanpy, pandas, sklearn)

Focus on what the code actually does, not general explanations.


2) Model Design & Architecture

Explain the implemented model design:
	•	Architecture type(s) used
	•	Major components or modules
	•	Key design decisions (e.g., embeddings, encoders, decoders, attention, GNN, VAE, etc.)
	•	Algorithms or frameworks selected
	•	Libraries/frameworks used (PyTorch, TensorFlow, sklearn, etc.)

Include structural choices that affect performance or behavior.

3) Training Strategy & Optimization

Describe the training pipeline in detail:
	•	Loss function(s) used
	•	Optimization method(s)
	•	Hyperparameters explicitly defined
	•	Regularization or constraints
	•	Evaluation metrics
	•	Validation strategy or early stopping
	•	Search strategy (if any)

Focus on explicit implementation decisions.


Output Requirements
	•	Provide a concise but detailed structured summary.
	•	Use clear section headers.
	•	Do not restate code line-by-line.
	•	Do not explain generic ML concepts.
	•	Only describe concrete behaviors and design choices present in the code.

Be concise, accurate, structured, and analytical.
"""

# {
#   "data_preprocessing": {
#     "data_loading": "",
#     "transformations": [],
#     "feature_engineering": [],
#     "splitting_strategy": "",
#     "libraries": []
#   },
#   "model_design": {
#     "architecture_type": "",
#     "components": [],
#     "algorithms_or_frameworks": [],
#     "design_decisions": []
#   },
#   "training_strategy": {
#     "loss_functions": [],
#     "optimizers": [],
#     "hyperparameters": {},
#     "evaluation_metrics": [],
#     "validation_strategy": "",
#     "search_or_tuning": ""
#   },
#   "technical_summary": ""
# }

NOTEBOOK_QUERY = """
Below the current versions of code for the same task on a dataset.

---
Role of the code: **{code_role}**

Code at Step {cur_step}:
<START of Code at Step {cur_step}>
{cur_code}
<END of Code at Step {cur_step}>

---
Output format:
- {code_role} Behavior at Step {cur_step}: ...
"""

NOTEBOOK_PERF_DIFF=(
# "\n- Pipeline performance ({metrics}), corresponding model config and coefficients at Step {pre_step}:\n<PERFORMANCE>\n{pre_perf}</PERFORMANCE>\n<MODEL_CONFIG>\n{pre_model}\n</MODEL_CONFIG>\n<MODEL_COEF>\n{pre_coef}\n</MODEL_COEF>\n"
"- Pipeline performance ({metrics}) and corresponding model config and coefficients at Step {cur_step}:\n<PERFORMANCE>\n{cur_perf}</PERFORMANCE>\n"
)

NOTEBOOK_META_DIFF=(
# "\n- Metadata from data preprocessing at Step {pre_step}:\n<METADATA>\n{pre_meta}\n</METADATA>\n"
"- Metadata from data preprocessing at Step {cur_step}:\n<METADATA>{cur_meta}\n</METADATA>\n"
)
