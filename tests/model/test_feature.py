from halfpipe.model.feature import FeatureSchema


def test_null_estimation_task_based_feature() -> None:
    feature = FeatureSchema().load(dict(type="task_based", name="taskBased"))
    assert feature.estimation == "multiple_trial"
