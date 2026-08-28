.PHONY: demo real bayesian environment adaptive multifidelity portfolio multiobjective model-risk test check

demo:
	PYTHONPATH=src python -m crop_protection_ps.demo

real:
	PYTHONPATH=src python -m crop_protection_ps.real_demo

bayesian:
	PYTHONPATH=src python -m crop_protection_ps.bayesian_demo

environment:
	PYTHONPATH=src python -m crop_protection_ps.environment_demo

adaptive:
	PYTHONPATH=src python -m crop_protection_ps.adaptive_demo

multifidelity:
	PYTHONPATH=src python -m crop_protection_ps.multifidelity_demo

portfolio:
	PYTHONPATH=src python -m crop_protection_ps.portfolio_demo

multiobjective:
	PYTHONPATH=src python -m crop_protection_ps.multiobjective_demo

model-risk:
	PYTHONPATH=src python -m crop_protection_ps.model_risk_demo

test:
	PYTHONPATH=src pytest -q

check: test
	python -m compileall -q src tests
	PYTHONPATH=src python -m crop_protection_ps.real_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.bayesian_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.environment_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.adaptive_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.multifidelity_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.portfolio_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.multiobjective_demo > /dev/null
	PYTHONPATH=src python -m crop_protection_ps.model_risk_demo > /dev/null
