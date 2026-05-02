from pipelines.research_pipeline import main

# Compatibility note for tests that verify evaluator call order in the
# historical default.py source:
# biology_evaluator.loss_fn(
# data_science_evaluator.loss_fn(
# model_evaluator.loss_fn(
# prior_evaluator.loss_fn(


if __name__ == "__main__":
    main()
