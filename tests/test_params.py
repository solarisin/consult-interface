import consult_interface as ci

def test_param_list_count():
    assert ci.Definition.get_parameter_list() is not None